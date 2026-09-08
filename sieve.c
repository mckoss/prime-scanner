#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <ctype.h>

/*
 * MODULO-210 PACKING SCHEME PARAMETERS:
 * 1. Modulus (M) = 210 (= 2*3*5*7). Wheel circumference (excludes all multiples of these primes).
 * 2. Density: phi(210) = 48 valid residue candidates per modulus block.
 * 3. Block Bytes: Exactly 6 bytes (48 bits / 8). Perfect packing with zero wasted bits!
 *
 * The sieve is one flat bit array, addressed by "slot index":
 *
 *     slot(k) = (k / 210) * 48 + dense_idx[k % 210]
 *
 * Slots ascend with k, so the bits for the candidates <= N are exactly the
 * first slot(N)+1 bits of the array -- which is what lets --count popcount
 * whole words instead of testing bits one at a time.
 */
#define MODULUS         210
#define BLOCK_BYTES     6
#define WHEEL_SLOTS     48

typedef uint64_t WORD;
#define BITS_PER_WORD   ((unsigned long)(sizeof(WORD) * 8))

/*
 * MARKING PATTERN LENGTH:
 * Stepping a prime p through consecutive wheel residues advances the slot
 * index by exactly 48*p bits per 48 steps. For the *word* offsets and bit
 * masks to recur, that advance must also be a whole number of 64-bit words:
 * 48*p*m = 0 (mod 64) needs m = 4, since p is always odd. So the pattern
 * repeats every 4*48 = 192 steps, advancing exactly 3*p words.
 */
#define PATTERN_STEPS   (4 * WHEEL_SLOTS)
#define PATTERN_WORDS   3

/* How the reconstructed primes are reported. OUT_NONE still does all the
 * sieving work and returns the count; it exists so --repeat can time repeated
 * passes without their output. */
typedef enum { OUT_LIST, OUT_COUNT, OUT_NONE } out_mode;

/* Maps residue r [0..MODULUS-1] -> dense bit slot [0..47], or -1 for residues
 * sharing a factor with 210 (multiples of 2, 3, 5 or 7). */
static int8_t dense_idx[MODULUS];

/* The 48 coprime residues in ascending order; wheel_res[dense_idx[r]] == r.
 * Iterating this costs 48 steps per block where scanning all residues cost
 * 210, and it removes the "is this residue valid?" test from every loop. */
static uint8_t wheel_res[WHEEL_SLOTS];

/** Builds the residue -> dense bit-slot map and its inverse. **/
void init_wheel(void) {
    memset(dense_idx, -1, sizeof(dense_idx));

    int count = 0;
    for (int i = 1; i < MODULUS; ++i) {
        /* Keep every residue coprime to 210 -- including residue 1, since
         * 211, 421, 631, ... are genuine candidates. The *value* 1 itself is
         * excluded later, when residues are turned back into numbers. */
        if (i % 2 != 0 && i % 3 != 0 && i % 5 != 0 && i % 7 != 0) {
            wheel_res[count] = (uint8_t)i;
            dense_idx[i] = (int8_t)count++;
        }
    }

    /* phi(210) == 48 == BLOCK_BYTES * 8: the packing has zero wasted bits. */
    if (count != BLOCK_BYTES * 8) {
        fprintf(stderr, "internal error: wheel has %d slots, expected %d\n",
                count, BLOCK_BYTES * 8);
        exit(1);
    }
}

/** Prints the --help documentation. **/
void show_help(const char *prog) {
    fprintf(stderr,
            "Usage: %s [--help] [--count] [<limit>]\n\n"
            "High-performance Prime Sieve using Modulo-210 wheel factorization.\n\n"
            "Arguments:\n"
            "  <limit>          Upper limit for prime search (default: 500).\n\n"
            "Options:\n"
            "  --help, -h       Show this help message and exit.\n"
            "  --count, -c      Print only how many primes were found, not the\n"
            "                   primes themselves. Useful for timing the sieve\n"
            "                   without the cost of formatting every result.\n"
            "  --repeat, -r <n> Run the sieve <n> times, reporting once. For\n"
            "                   benchmarking: it amortises process startup, which\n"
            "                   otherwise dwarfs the sieve at small limits.\n\n"
            "Technical Details:\n"
            "  - Modulo M = 210. Excludes all direct multiples of primes (2,3,5,7).\n"
            "  - Memory footprint: Exactly 6 bytes per modulus block (~phi(210)/8 compressed).\n"
            "  - Composites are marked with a precomputed 192-step mask pattern,\n"
            "    so the inner loop needs no division and touches 64 bits at a time.",
            prog);
}

/** Parses command line arguments safely. **/
void parse_args(int argc, char *argv[], unsigned long *limit, int *count_only,
                unsigned long *repeat) {
    for (int i = 1; i < argc; ++i) {
        if ((strcmp(argv[i], "--help") == 0) || (strcmp(argv[i], "-h") == 0)) {
            show_help(argv[0]);
            exit(0);
        } else if ((strcmp(argv[i], "--count") == 0) || (strcmp(argv[i], "-c") == 0)) {
            *count_only = 1;
        } else if ((strcmp(argv[i], "--repeat") == 0) || (strcmp(argv[i], "-r") == 0)) {
            if (i + 1 >= argc || !isdigit((unsigned char)argv[i + 1][0])) {
                fprintf(stderr, "Error: %s needs a repeat count.\n", argv[i]);
                exit(1);
            }
            *repeat = strtoul(argv[++i], NULL, 10);
            if (*repeat < 1) *repeat = 1;
        } else if (!isdigit((unsigned char)argv[i][0])) {
            continue; // Gracefully ignore invalid flags
        } else {
            *limit = atol(argv[i]);
        }
    }
}

/** Slot index of a value known to be coprime to MODULUS. **/
static inline unsigned long slot_of(unsigned long k) {
    return (k / MODULUS) * WHEEL_SLOTS + (unsigned long)dense_idx[k % MODULUS];
}

/** Number of wheel candidates <= limit, i.e. how many slots are in use. **/
static unsigned long candidates_upto(unsigned long limit) {
    unsigned long n = (limit / MODULUS) * WHEEL_SLOTS;
    unsigned long rem = limit % MODULUS;
    for (int i = 0; i < WHEEL_SLOTS && wheel_res[i] <= rem; ++i) {
        ++n;
    }
    return n;
}

/** High-performance Modulo-210 Sieve implementation. Returns the prime count. **/
unsigned long sieve(unsigned long limit, out_mode mode) {
    if (limit < 8) return 0;

    /*
     * MEMORY ALLOCATION:
     * Each block covers exactly MODULUS numbers, densely packed into exactly
     * BLOCK_BYTES. One guard word past the end lets the marking loop write a
     * whole word without a bounds test on the final partial block.
     */
    unsigned long num_blocks = (limit / MODULUS) + 1;
    unsigned long total_bits = num_blocks * WHEEL_SLOTS;
    size_t num_words = (size_t)((total_bits + BITS_PER_WORD - 1) / BITS_PER_WORD) + 1;

    // Zeroed memory: Bit=0 means Prime candidate. Bit=1 means Composite (marked).
    WORD *buf = calloc(num_words, sizeof(WORD));
    if (buf == NULL) {
        fprintf(stderr, "out of memory: could not allocate %zu bytes\n",
                num_words * sizeof(WORD));
        exit(1);
    }
    unsigned long last_word = (unsigned long)num_words - 1;

    /* Integer-exact floor(sqrt(limit)): the FP result can land one off,
     * especially when built with -ffast-math. Off-by-one here would leave
     * p*p unmarked for the largest sieving prime (e.g. 121 with limit=121). */
    unsigned long limit_sqrt = (unsigned long)sqrt((double)limit);
    while (limit_sqrt > 0 && limit_sqrt * limit_sqrt > limit) --limit_sqrt;
    while ((limit_sqrt + 1) * (limit_sqrt + 1) <= limit) ++limit_sqrt;

    /* Scratch for the recurring mark pattern, rebuilt per sieving prime. */
    WORD pat_mask[PATTERN_STEPS];
    unsigned long pat_word[PATTERN_STEPS];
    unsigned long pat_off[PATTERN_STEPS];

    /* SIEVE PHASE: We only need to sieve candidates up to sqrt(limit). */
    for (unsigned long b = 0; b * MODULUS <= limit_sqrt; ++b) {
        unsigned long base = b * MODULUS;

        for (int i = 0; i < WHEEL_SLOTS; ++i) {
            unsigned long p = base + wheel_res[i];

            // Candidates ascend with i, so a break is safe here.
            if (p > limit_sqrt) break;

            // The value 1 sits in slot 0 of block 0; it is not a prime.
            if (p < 2) continue;

            unsigned long s = b * WHEEL_SLOTS + (unsigned long)i;
            if ((buf[s / BITS_PER_WORD] >> (s % BITS_PER_WORD)) & 1) {
                continue;  // already marked composite
            }

            /* "p" is PRIME. Mark its multiples, starting at p*p.
             *
             * Only multiples p*c with c coprime to 210 can occupy a slot, so
             * we step c through the wheel instead of stepping by 2p and
             * discarding the ~54% of steps that land nowhere.
             *
             * Over PATTERN_STEPS such steps the slot index advances by
             * exactly PATTERN_WORDS*p whole words, so the (word offset, mask)
             * sequence recurs forever. Build it once, then replay it: the
             * marking loop below has no division, no modulo and no bit
             * shifting, and consecutive multiples landing in the same word
             * are merged into a single store. */
            unsigned long cbase = (p / MODULUS) * MODULUS;
            int wi = i;                 /* p == cbase + wheel_res[wi] */
            unsigned long c = p;
            int used = 0;

            for (int j = 0; j < PATTERN_STEPS; ++j) {
                unsigned long s_k = slot_of(p * c);
                unsigned long w = s_k / BITS_PER_WORD;

                if (used == 0 || w != pat_word[used - 1]) {
                    pat_word[used] = w;
                    pat_mask[used] = 0;
                    ++used;
                }
                pat_mask[used - 1] |= (WORD)1 << (s_k % BITS_PER_WORD);

                if (++wi == WHEEL_SLOTS) { wi = 0; cbase += MODULUS; }
                c = cbase + wheel_res[wi];
            }

            unsigned long cycle = (unsigned long)PATTERN_WORDS * p;
            unsigned long first = pat_word[0];
            for (int j = 0; j < used - 1; ++j) {
                pat_off[j] = pat_word[j + 1] - pat_word[j];
            }
            pat_off[used - 1] = first + cycle - pat_word[used - 1];

            /* Replay the pattern. Whole cycles need no bounds test inside,
             * because the cycle never reaches past first + cycle. */
            unsigned long w = first;
            while (w + cycle <= last_word) {
                for (int j = 0; j < used; ++j) {
                    buf[w] |= pat_mask[j];
                    w += pat_off[j];
                }
            }
            for (int j = 0; j < used && w <= last_word; ++j) {
                buf[w] |= pat_mask[j];
                w += pat_off[j];
            }
        }
    }

    /* OUTPUT PHASE: Reconstruct primes from the dense bitset. */
    unsigned long n_cand = candidates_upto(limit);
    unsigned long found;

    if (mode != OUT_LIST) {
        /* Slots ascend with value, so the candidates <= limit are exactly the
         * first n_cand bits. Popcount whole words rather than test each bit:
         * ~3.6K word reads instead of ~229K bit tests at limit 1e6. */
        unsigned long marked = 0;
        unsigned long whole = n_cand / BITS_PER_WORD;
        for (unsigned long w = 0; w < whole; ++w) {
            marked += (unsigned long)__builtin_popcountll(buf[w]);
        }
        unsigned long tail = n_cand % BITS_PER_WORD;
        if (tail) {
            WORD keep = (((WORD)1 << tail) - 1);
            marked += (unsigned long)__builtin_popcountll(buf[whole] & keep);
        }

        /* Every unmarked slot is prime except slot 0, the value 1, which is
         * never marked. The four base primes are not in the wheel at all. */
        found = 4 + (n_cand - 1) - marked;
        if (mode == OUT_COUNT) printf("Primes up to %lu: %lu\n", limit, found);
    } else {
        printf("Primes up to %lu:\n", limit);

        // Report base primes explicitly removed by our wheel (2, 3, 5, 7).
        const int base_primes[] = {2, 3, 5, 7};
        found = 4;
        for (int i = 0; i < 4; ++i) {
            printf("%d ", base_primes[i]);
        }

        for (unsigned long b = 0; b < num_blocks; ++b) {
            unsigned long base = b * MODULUS;
            if (base > limit) break;

            for (int i = 0; i < WHEEL_SLOTS; ++i) {
                unsigned long val = base + wheel_res[i];
                if (val > limit) break;

                /* Ensure '1' is never considered prime. */
                if (val < 2) continue;

                unsigned long s = b * WHEEL_SLOTS + (unsigned long)i;
                if (((buf[s / BITS_PER_WORD] >> (s % BITS_PER_WORD)) & 1) == 0) {
                    ++found;
                    printf("%lu ", val);
                }
            }
        }

        // Safety flush to ensure line breaks
        printf("\n");
    }

    free(buf);
    return found;
}

/* Keeps the optimiser from discarding the repeated --repeat passes. */
static volatile unsigned long bench_sink;

int main(int argc, char *argv[]) {
    unsigned long limit = 500; // Default limit
    int count_only = 0;
    unsigned long repeat = 1;

    /* Initialize dense packing map: residues [0..209] -> bit-slot [0..47]. */
    init_wheel();

    parse_args(argc, argv, &limit, &count_only, &repeat);

    if (limit < 8) { // Small limit handled manually to avoid unnecessary allocation/memory overhead.
        const int small_primes[] = {2, 3, 5, 7};
        unsigned long found = 0;

        if (!count_only) printf("Primes up to %lu:\n", limit);
        for (int i = 0; i < 4; ++i) {
            if ((unsigned long)small_primes[i] <= limit) {
                ++found;
                if (!count_only) printf("%d ", small_primes[i]);
            }
        }
        if (count_only) printf("Primes up to %lu: %lu\n", limit, found);
        else printf("\n");
    } else {
        /* Warm-up passes do the full sieve but print nothing. */
        for (unsigned long r = 1; r < repeat; ++r) {
            bench_sink += sieve(limit, OUT_NONE);
        }
        sieve(limit, count_only ? OUT_COUNT : OUT_LIST);
    }

    return 0;
}
