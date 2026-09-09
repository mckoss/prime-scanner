#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <limits.h>
#include <ctype.h>
#include <time.h>
#include <signal.h>
#include <sys/stat.h>
#include <errno.h>

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

/*
 * WORD SIZE:
 * Wide words merge more bits per store; narrow words build the mark pattern
 * faster, since the pattern is 48*max(1,W/16) entries long. That used to make
 * 32 the best all-round choice, but MARK_DIRECT_BELOW removes most of the
 * build cost and 64 now wins from 1e6 up (ms per pass, sieve only, arm64):
 *
 *            1e4      1e5      3e5      1e6      1e7      1e8
 *   32-bit  0.0018   0.0123   0.0325   0.1012   1.4370   17.700
 *   64-bit  0.0023   0.0132   0.0338   0.0983   1.3446   16.424
 *
 * 64 is the default. Below 1e6 the gap is under 10% of times measured in
 * microseconds. Override with: make WORD_BITS=32
 */
#ifndef SIEVE_WORD_BITS
#define SIEVE_WORD_BITS 64
#endif
#if   SIEVE_WORD_BITS == 8
typedef uint8_t  WORD;
#elif SIEVE_WORD_BITS == 16
typedef uint16_t WORD;
#elif SIEVE_WORD_BITS == 32
typedef uint32_t WORD;
#elif SIEVE_WORD_BITS == 64
typedef uint64_t WORD;
#else
#error "SIEVE_WORD_BITS must be 8, 16, 32 or 64"
#endif

#define BITS_PER_WORD   ((unsigned long)(sizeof(WORD) * 8))

#if SIEVE_WORD_BITS == 64
#define POPCOUNT(w) __builtin_popcountll(w)
#else
#define POPCOUNT(w) __builtin_popcount(w)
#endif

/*
 * MARKING PATTERN LENGTH:
 * Stepping a prime p through consecutive wheel residues advances the slot
 * index by exactly 48*p bits per 48 steps. For the *word* offsets and bit
 * masks to recur, that advance must also be a whole number of words:
 * 48*p*m = 0 (mod W). Since p is odd and 48 contributes 2^4, this needs
 * m = max(1, W/16). So the pattern is 48*m steps, advancing 48*m/W words:
 *
 *   W = 8   ->   48 steps, 6*p words       W = 32  ->   96 steps, 3*p words
 *   W = 16  ->   48 steps, 3*p words       W = 64  ->  192 steps, 3*p words
 */
#if SIEVE_WORD_BITS <= 16
#define PATTERN_MULT    1
#else
#define PATTERN_MULT    (SIEVE_WORD_BITS / 16)
#endif
#define PATTERN_STEPS   (WHEEL_SLOTS * PATTERN_MULT)
#define PATTERN_WORDS   (PATTERN_STEPS / SIEVE_WORD_BITS)

/*
 * A prime near sqrt(limit) has almost nothing left to mark: at limit 1e5,
 * 62% of the sieving primes have fewer multiples in range than the 192-entry
 * 64-bit pattern has entries, so building one costs more than it saves.
 * Below this many marks, skip the pattern and mark directly.
 *
 * Swept at 8/16/32/64 bits: the optimum sits at 4/3 of the pattern length in
 * every case (256 marks for the 192-step 64-bit pattern, 128 for the 96-step
 * 32-bit one). Worth 45% at 1e5 and 10% at 1e6.
 */
#ifndef MARK_DIRECT_BELOW
#define MARK_DIRECT_BELOW (4 * PATTERN_STEPS / 3)
#endif

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

/*
 * DIVISION-FREE PATTERN BUILD.
 * Writing p = P*210 + wheel_res[a] and c = C*210 + wheel_res[b], the product
 * expands to
 *
 *     slot(p*c) = (p*48)*C + P*(48*wheel_res[b]) + T[a][b]
 *
 * with T[a][b] = 48*(ra*rb / 210) + dense_idx[(ra*rb) % 210]. Only the two
 * residues matter, so both tables are built once at startup: the per-prime
 * pattern build then needs no division at all, and P and a are already the
 * sieve loop's own block and slot indices.
 *
 * ra*rb < 210^2, so T fits in 16 bits (max 48*209 + 47 = 10079).
 */
static uint16_t wheel_prod[WHEEL_SLOTS][WHEEL_SLOTS];   /* T[a][b] */
static uint16_t wheel_scaled[WHEEL_SLOTS];              /* 48 * wheel_res[b] */

/* For residue r, the slot of the smallest wheel residue >= r, or WHEEL_SLOTS
 * when there is none and the search must move to the next block. Used to snap
 * a window's lower bound up to a real candidate. */
static uint8_t ceil_idx[MODULUS + 1];

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

    {
        int slot = 0;
        for (int r = 0; r <= MODULUS; ++r) {
            while (slot < WHEEL_SLOTS && wheel_res[slot] < r) ++slot;
            ceil_idx[r] = (uint8_t)slot;
        }
    }

    for (int a = 0; a < WHEEL_SLOTS; ++a) {
        wheel_scaled[a] = (uint16_t)(WHEEL_SLOTS * (unsigned)wheel_res[a]);

        for (int b = 0; b < WHEEL_SLOTS; ++b) {
            /* Both residues are coprime to 210, so the product is too and
             * dense_idx of it is never -1. */
            unsigned prod = (unsigned)wheel_res[a] * (unsigned)wheel_res[b];
            wheel_prod[a][b] = (uint16_t)(WHEEL_SLOTS * (prod / MODULUS)
                                          + (unsigned)dense_idx[prod % MODULUS]);
        }
    }
}

/** Prints the --help documentation. **/
void show_help(const char *prog) {
    fprintf(stderr,
            "Usage: %s [--help] [--count] [--from <lo>] [<limit>]\n"
            "       %s --gaps --out <dir> [--from <lo>] [--checkpoint <s>] [<limit>]\n\n"
            "High-performance Prime Sieve using Modulo-210 wheel factorization.\n\n"
            "Arguments:\n"
            "  <limit>          Upper limit for prime search (default: 500).\n\n"
            "Options:\n"
            "  --help, -h       Show this help message and exit.\n"
            "  --count, -c      Print only how many primes were found, not the\n"
            "                   primes themselves. Useful for timing the sieve\n"
            "                   without the cost of formatting every result.\n"
            "  --from, -f <lo>  Report only primes >= <lo>. Sieves just that\n"
            "                   window, so memory and time scale with the window\n"
            "                   rather than with <limit>.\n"
            "  --repeat, -r <n> Run the sieve <n> times, reporting once. For\n"
            "                   benchmarking: it amortises process startup, which\n"
            "                   otherwise dwarfs the sieve at small limits.\n"
            "  --gaps           Search for record prime gaps, and for record\n"
            "                   'lonely' primes (max distance to the NEARER\n"
            "                   neighbour, OEIS A023186), 'aloof' primes (max\n"
            "                   distance between BOTH neighbours, A096265) and\n"
            "                   'equidistant' primes (max distance among the\n"
            "                   BALANCED primes only, A058867).\n"
            "  --out <dir>      Output directory for --gaps, created if needed.\n"
            "                   Writes gap.txt, lonely.txt, aloof.txt and\n"
            "                   equidistant.txt (one record per line, carrying\n"
            "                   both neighbour primes so each line is\n"
            "                   self-contained proof), plus progress.txt for\n"
            "                   checkpoints. Every line is flushed, so a killed\n"
            "                   run resumes without losing work.\n"
            "  --checkpoint <s> Seconds between progress lines and checkpoints\n"
            "                   (default 15).\n\n"
            "  This sieve is single-threaded. To scan a range across several\n"
            "  cores, use the driver alongside it, which shards the range and\n"
            "  merges the workers' output:\n"
            "      python3 pgaps.py --from <lo> --to <hi> --jobs <n> --out <dir>\n\n"
            "Technical Details:\n"
            "  - Modulo M = 210. Excludes all direct multiples of primes (2,3,5,7).\n"
            "  - Memory footprint: Exactly 6 bytes per modulus block (~phi(210)/8 compressed).\n"
            "  - Composites are marked with a precomputed %d-step mask pattern,\n"
            "    so the inner loop needs no division and touches %d bits at a time.",
            prog, prog, PATTERN_STEPS, SIEVE_WORD_BITS);
}

/** Parses command line arguments safely. **/
void parse_args(int argc, char *argv[], unsigned long *limit, int *count_only,
                unsigned long *repeat, unsigned long *from, int *has_from,
                int *gaps, const char **out_path, double *ck_secs) {
    for (int i = 1; i < argc; ++i) {
        if ((strcmp(argv[i], "--help") == 0) || (strcmp(argv[i], "-h") == 0)) {
            show_help(argv[0]);
            exit(0);
        } else if ((strcmp(argv[i], "--count") == 0) || (strcmp(argv[i], "-c") == 0)) {
            *count_only = 1;
        } else if (strcmp(argv[i], "--gaps") == 0) {
            *gaps = 1;
        } else if (strcmp(argv[i], "--out") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "Error: --out needs a directory.\n");
                exit(1);
            }
            *out_path = argv[++i];
        } else if (strcmp(argv[i], "--checkpoint") == 0) {
            if (i + 1 >= argc || !isdigit((unsigned char)argv[i + 1][0])) {
                fprintf(stderr, "Error: --checkpoint needs a number of seconds.\n");
                exit(1);
            }
            *ck_secs = atof(argv[++i]);
            if (*ck_secs < 1) *ck_secs = 1;
        } else if ((strcmp(argv[i], "--from") == 0) || (strcmp(argv[i], "-f") == 0)) {
            if (i + 1 >= argc || !isdigit((unsigned char)argv[i + 1][0])) {
                fprintf(stderr, "Error: %s needs a lower bound.\n", argv[i]);
                exit(1);
            }
            *from = strtoul(argv[++i], NULL, 10);
            *has_from = 1;
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
            /* strtoul, not atol: atol returns a signed long, so any limit at
             * or above 2^63 saturates at LONG_MAX and silently truncates. */
            *limit = strtoul(argv[i], NULL, 10);
        }
    }
}

/** Slot index of a value known to be coprime to MODULUS. **/
static inline unsigned long slot_of(unsigned long k) {
    return (k / MODULUS) * WHEEL_SLOTS + (unsigned long)dense_idx[k % MODULUS];
}

/** Exact floor(sqrt(n)). **/
static unsigned long isqrt_floor(unsigned long n) {
    if (n < 2) return n;

    /* The double conversion loses precision above 2^53 and -ffast-math can
     * nudge it either way, so correct in both directions. Comparing via
     * division rather than r*r keeps this exact right up to ULONG_MAX. */
    unsigned long r = (unsigned long)sqrt((double)n);
    if (r > n) r = n;
    while (r > 1 && r > n / r) --r;
    while (r + 1 <= n / (r + 1)) ++r;
    return r;
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

/** Set bits in buf[] over the inclusive bit range [lo_bit, hi_bit]. **/
static unsigned long popcount_range(const WORD *buf,
                                    unsigned long lo_bit, unsigned long hi_bit) {
    unsigned long wlo = lo_bit / BITS_PER_WORD, klo = lo_bit % BITS_PER_WORD;
    unsigned long whi = hi_bit / BITS_PER_WORD, khi = hi_bit % BITS_PER_WORD;

    WORD all = (WORD)~(WORD)0;
    WORD mask_lo = (WORD)(all << klo);                       /* bits >= klo */
    WORD mask_hi = (khi + 1 == BITS_PER_WORD)                /* bits <= khi */
                 ? all : (WORD)(((WORD)1 << (khi + 1)) - 1);

    if (wlo == whi) {
        return (unsigned long)POPCOUNT((WORD)(buf[wlo] & mask_lo & mask_hi));
    }

    unsigned long n = (unsigned long)POPCOUNT((WORD)(buf[wlo] & mask_lo));
    for (unsigned long w = wlo + 1; w < whi; ++w) {
        n += (unsigned long)POPCOUNT(buf[w]);
    }
    return n + (unsigned long)POPCOUNT((WORD)(buf[whi] & mask_hi));
}

/**
 * Mark the multiples of prime p that land in [lo, hi].
 *
 * The buffer need not start at slot 0: word_base is the absolute word index
 * of buf[0], so a candidate at absolute slot s lands in
 * buf[s / BITS_PER_WORD - word_base]. last_word is buf's final valid index.
 * That offset is the whole of what makes a windowed sieve work -- bit
 * positions within a word are unchanged, so the mark pattern is identical.
 */
static void mark_prime(WORD *buf, unsigned long word_base, unsigned long last_word,
                       unsigned long p, unsigned long lo, unsigned long hi) {
    unsigned long cmax = hi / p;
    if (cmax < p) return;                  /* p*p is already past the window */

    /* Smallest c with p*c >= lo, never below p itself: any smaller multiple
     * has a factor under p and was marked when that prime was handled. */
    unsigned long c0 = p;
    if (lo > 0) {
        /* ceil(lo / p), written to avoid overflowing when lo is near
         * ULONG_MAX -- (lo + p - 1) would wrap. */
        unsigned long need = lo / p;
        if (need * p < lo) ++need;
        if (need > c0) c0 = need;
    }

    /* Only c coprime to 210 gives a multiple that occupies a slot. */
    unsigned long blk = c0 / MODULUS;
    int bi = ceil_idx[c0 % MODULUS];
    if (bi == WHEEL_SLOTS) { bi = 0; ++blk; }

    unsigned long c = blk * MODULUS + wheel_res[bi];
    if (c > cmax) return;

    /* The wheel keeps 48 of every 210, so this is about how many marks
     * follow. Too few and building a pattern cannot pay for itself. */
    if (((cmax - c) * WHEEL_SLOTS) / MODULUS + 1 < MARK_DIRECT_BELOW) {
        unsigned long cbase = blk * MODULUS;
        unsigned long v = c;

        while (v <= cmax) {
            unsigned long s = slot_of(p * v);
            buf[s / BITS_PER_WORD - word_base] |= (WORD)1 << (s % BITS_PER_WORD);

            if (++bi == WHEEL_SLOTS) { bi = 0; cbase += MODULUS; }
            v = cbase + wheel_res[bi];
        }
        return;
    }

    /* Division-free build: slot(p*c) = (p*48)*C + P*(48*rb) + T[a][b], with
     * the two step-dependent terms folded into one row up front. */
    unsigned long P = p / MODULUS;
    int a = dense_idx[p % MODULUS];

    unsigned long row_base[WHEEL_SLOTS];
    for (int t = 0; t < WHEEL_SLOTS; ++t) {
        row_base[t] = P * (unsigned long)wheel_scaled[t]
                    + (unsigned long)wheel_prod[a][t];
    }

    WORD pat_mask[PATTERN_STEPS];
    unsigned long pat_word[PATTERN_STEPS];
    unsigned long pat_off[PATTERN_STEPS];

    unsigned long p_step = p * WHEEL_SLOTS;    /* slot advance per block of c */
    unsigned long c_base = p_step * blk;
    int used = 0;

    for (int j = 0; j < PATTERN_STEPS; ++j) {
        unsigned long s = c_base + row_base[bi];
        unsigned long w = s / BITS_PER_WORD - word_base;

        if (used == 0 || w != pat_word[used - 1]) {
            pat_word[used] = w;
            pat_mask[used] = 0;
            ++used;
        }
        pat_mask[used - 1] |= (WORD)1 << (s % BITS_PER_WORD);

        if (++bi == WHEEL_SLOTS) { bi = 0; c_base += p_step; }
    }

    unsigned long cycle = (unsigned long)PATTERN_WORDS * p;
    unsigned long first = pat_word[0];
    for (int j = 0; j < used - 1; ++j) {
        pat_off[j] = pat_word[j + 1] - pat_word[j];
    }
    pat_off[used - 1] = first + cycle - pat_word[used - 1];

    /* Whole cycles need no bounds test inside: a cycle never reaches past
     * first + cycle. */
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

/** Sieve [0, m] into a fresh buffer, discovering its own primes as it goes. **/
static WORD *self_sieve(unsigned long m, size_t *words_out) {
    unsigned long num_blocks = (m / MODULUS) + 1;
    unsigned long total_bits = num_blocks * WHEEL_SLOTS;
    size_t num_words = (size_t)((total_bits + BITS_PER_WORD - 1) / BITS_PER_WORD) + 1;

    WORD *buf = calloc(num_words, sizeof(WORD));
    if (buf == NULL) {
        fprintf(stderr, "out of memory: could not allocate %zu bytes\n",
                num_words * sizeof(WORD));
        exit(1);
    }

    unsigned long root = isqrt_floor(m);
    for (unsigned long b = 0; b * MODULUS <= root; ++b) {
        unsigned long base = b * MODULUS;

        for (int i = 0; i < WHEEL_SLOTS; ++i) {
            unsigned long p = base + wheel_res[i];
            if (p > root) break;            /* candidates ascend with i */
            if (p < 2) continue;            /* the value 1 */

            unsigned long s = b * WHEEL_SLOTS + (unsigned long)i;
            if ((buf[s / BITS_PER_WORD] >> (s % BITS_PER_WORD)) & 1) continue;

            mark_prime(buf, 0, (unsigned long)num_words - 1, p, 0, m);
        }
    }

    *words_out = num_words;
    return buf;
}

/** High-performance Modulo-210 Sieve implementation. Returns the prime count. **/
unsigned long sieve(unsigned long limit, out_mode mode) {
    if (limit < 8) return 0;

    size_t num_words;
    WORD *buf = self_sieve(limit, &num_words);

    unsigned long n_cand = candidates_upto(limit);
    unsigned long found;

    if (mode != OUT_LIST) {
        /* Slots ascend with value, so the candidates <= limit are exactly the
         * first n_cand bits. Every unmarked one is prime except slot 0, the
         * value 1, which is never marked. */
        found = 4 + (n_cand - 1) - popcount_range(buf, 0, n_cand - 1);
        if (mode == OUT_COUNT) printf("Primes up to %lu: %lu\n", limit, found);
    } else {
        printf("Primes up to %lu:\n", limit);

        const int base_primes[] = {2, 3, 5, 7};
        found = 4;
        for (int i = 0; i < 4; ++i) {
            printf("%d ", base_primes[i]);
        }

        for (unsigned long b = 0; b * MODULUS <= limit; ++b) {
            unsigned long base = b * MODULUS;

            for (int i = 0; i < WHEEL_SLOTS; ++i) {
                unsigned long val = base + wheel_res[i];
                if (val > limit) break;
                if (val < 2) continue;      /* 1 is not prime */

                unsigned long s = b * WHEEL_SLOTS + (unsigned long)i;
                if (((buf[s / BITS_PER_WORD] >> (s % BITS_PER_WORD)) & 1) == 0) {
                    ++found;
                    printf("%lu ", val);
                }
            }
        }
        printf("\n");
    }

    free(buf);
    return found;
}

/**
 * Windowed sieve: report only the primes in [lo, hi].
 *
 * Allocates for the window alone, so memory tracks (hi - lo) rather than hi.
 * The sieving primes up to sqrt(hi) come from a small ordinary sieve first --
 * for a window near 1e12 that is a sieve of 1e6, a fraction of a millisecond.
 */
unsigned long sieve_window(unsigned long lo, unsigned long hi, out_mode mode) {
    const unsigned long base_primes[] = {2, 3, 5, 7};
    unsigned long found = 0;

    if (mode == OUT_LIST) printf("Primes from %lu to %lu:\n", lo, hi);

    if (lo <= hi) {
        for (int i = 0; i < 4; ++i) {
            if (base_primes[i] >= lo && base_primes[i] <= hi) {
                ++found;
                if (mode == OUT_LIST) printf("%lu ", base_primes[i]);
            }
        }
    }

    /* First and last wheel candidates inside the window. Value 1 occupies a
     * slot but is not prime, so start no lower than 11 unless lo demands it. */
    unsigned long v_lo = 0, v_hi = 0;
    int have_range = 0;

    if (lo <= hi && hi >= 1) {
        unsigned long start = (lo < 1) ? 1 : lo;
        unsigned long blk = start / MODULUS;
        int bi = ceil_idx[start % MODULUS];
        if (bi == WHEEL_SLOTS) { bi = 0; ++blk; }
        v_lo = blk * MODULUS + wheel_res[bi];

        if (v_lo <= hi) {
            unsigned long ehi = hi / MODULUS;
            int ei = ceil_idx[hi % MODULUS];
            /* ceil_idx lands on the first candidate >= hi; step back one. */
            if (ei == WHEEL_SLOTS || wheel_res[ei] > hi % MODULUS) {
                if (ei == 0) { ei = WHEEL_SLOTS - 1; --ehi; } else { --ei; }
            }
            v_hi = ehi * MODULUS + wheel_res[ei];
            have_range = (v_hi >= v_lo);
        }
    }

    if (!have_range) {
        if (mode == OUT_LIST) printf("\n");
        else if (mode == OUT_COUNT) printf("Primes from %lu to %lu: %lu\n", lo, hi, found);
        return found;
    }

    unsigned long s_lo = slot_of(v_lo), s_hi = slot_of(v_hi);
    unsigned long word_base = s_lo / BITS_PER_WORD;
    size_t num_words = (size_t)(s_hi / BITS_PER_WORD - word_base) + 2;   /* +1 guard */

    WORD *buf = calloc(num_words, sizeof(WORD));
    if (buf == NULL) {
        fprintf(stderr, "out of memory: could not allocate %zu bytes\n",
                num_words * sizeof(WORD));
        exit(1);
    }

    /* Sieving primes: every wheel prime up to sqrt(hi). Multiples of 2, 3, 5
     * and 7 are absent from the wheel, so those four need no marking. */
    unsigned long root = isqrt_floor(hi);
    if (root >= 11) {
        size_t bwords;
        WORD *base = self_sieve(root, &bwords);

        for (unsigned long b = 0; b * MODULUS <= root; ++b) {
            unsigned long start = b * MODULUS;

            for (int i = 0; i < WHEEL_SLOTS; ++i) {
                unsigned long p = start + wheel_res[i];
                if (p > root) break;
                if (p < 2) continue;

                unsigned long s = b * WHEEL_SLOTS + (unsigned long)i;
                if (((base[s / BITS_PER_WORD] >> (s % BITS_PER_WORD)) & 1) == 0) {
                    mark_prime(buf, word_base, (unsigned long)num_words - 1,
                               p, lo, hi);
                }
            }
        }
        free(base);
    }

    unsigned long b_lo = s_lo - word_base * BITS_PER_WORD;
    unsigned long b_hi = s_hi - word_base * BITS_PER_WORD;

    if (mode != OUT_LIST) {
        found += (s_hi - s_lo + 1) - popcount_range(buf, b_lo, b_hi);
        if (v_lo < 2) --found;              /* slot 0 is the value 1 */
        if (mode == OUT_COUNT) printf("Primes from %lu to %lu: %lu\n", lo, hi, found);
    } else {
        unsigned long blk = v_lo / MODULUS;
        int bi = dense_idx[v_lo % MODULUS];
        unsigned long v = v_lo;

        /* Loop on the slot index, not the value: for a window at the very top
         * of the range the next candidate value overflows past ULONG_MAX and
         * wraps to a small number, which would restart the walk. Slots cannot
         * wrap (the largest is about 0.229 * ULONG_MAX), and the wrapped v of
         * the final step is computed but never used. */
        for (unsigned long s = s_lo; s <= s_hi; ++s) {
            unsigned long w = s / BITS_PER_WORD - word_base;

            if (v >= 2 && ((buf[w] >> (s % BITS_PER_WORD)) & 1) == 0) {
                ++found;
                printf("%lu ", v);
            }

            if (++bi == WHEEL_SLOTS) { bi = 0; ++blk; }
            v = blk * MODULUS + wheel_res[bi];
        }
        printf("\n");
    }

    free(buf);
    return found;
}


/* ===================================================================== *
 * RECORD GAP SEARCH
 *
 * Scans upward in cache-sized segments, streaming consecutive primes and
 * recording four kinds of record:
 *
 *   gap          record difference between consecutive primes  (OEIS A005250)
 *   lonely       record distance to the NEARER neighbour       (OEIS A023186)
 *   aloof        record total distance between BOTH neighbours (OEIS A096265)
 *   equidistant  record distance among the BALANCED primes     (OEIS A058867)
 *
 * The first three take their maximum over every prime. The fourth does not:
 * it ranks only the primes whose two gaps are EQUAL, against each other. So
 * it is not a filter of the lonely records and cannot be derived from them --
 * a balanced prime enters it by beating every earlier balanced prime, which
 * it can do at a distance some lopsided prime reached first. (Compare
 * balanced.txt, which pgaps.py filters out of the lonely records and which
 * *is* a subsequence of them.)
 *
 * --out <dir> writes five files into that directory, creating it if needed:
 *
 *   <dir>/gap.txt          results only, one record per line
 *   <dir>/lonely.txt         "
 *   <dir>/aloof.txt          "
 *   <dir>/equidistant.txt    "
 *   <dir>/progress.txt     checkpoints, for resuming
 *
 * Results lines are
 *
 *   <n> <prime> <value> <gap_below> <gap_above> <prev_prime> <next_prime>
 *
 * so the first two columns are an OEIS b-file, and the last two make each
 * line self-contained proof: a reader can confirm all three of prev, prime
 * and next are prime and that nothing lies between them, without recomputing
 * anything. Every line is flushed as it is written, so killing the run loses
 * nothing that was printed.
 *
 * Resuming splits its state between the two kinds of file: the scan position
 * comes from the last checkpoint, but the record thresholds come from the
 * results files. That combination is self-correcting. If the run died after
 * writing a record but before the next checkpoint, the rescan re-reaches that
 * record and finds it does not *exceed* the threshold it already set, so it
 * is not written twice -- and no record can be lost, because records only
 * ever increase.
 *
 * Seeding a search to extend a published sequence is therefore just a matter
 * of writing its known terms into the results file first.
 * ===================================================================== */

#define SEG_WORDS  65536u          /* segment bitmap: 512 KB at 64-bit words */

typedef struct {
    FILE *out;
    unsigned long best;            /* largest value recorded so far */
    unsigned long count;           /* records written */
} record_file;

typedef struct {
    unsigned long p_prev, p_last;  /* trailing two primes of the stream */
    unsigned long primes;
    double seconds;
    int resumed;
    record_file gap, lonely, aloof, equi;
    FILE *progress;
} gap_state;

/* Set by SIGINT/SIGTERM so the scan stops at a segment edge and checkpoints,
 * rather than being cut off mid-segment. */
static volatile sig_atomic_t stop_requested = 0;
static void on_signal(int sig) { (void)sig; stop_requested = 1; }

/** Smallest wheel candidate >= v, with its block and slot. **/
static unsigned long wheel_ceil(unsigned long v, unsigned long *blk, int *bi) {
    unsigned long b = v / MODULUS;
    int i = ceil_idx[v % MODULUS];
    if (i == WHEEL_SLOTS) { i = 0; ++b; }
    *blk = b; *bi = i;
    return b * MODULUS + wheel_res[i];
}

/** Largest wheel candidate <= v, or 0 if there is none. **/
static unsigned long wheel_floor(unsigned long v) {
    if (v < 1) return 0;
    unsigned long b = v / MODULUS;
    int i = ceil_idx[v % MODULUS];
    if (i == WHEEL_SLOTS || wheel_res[i] > v % MODULUS) {
        if (i == 0) { if (b == 0) return 0; i = WHEEL_SLOTS - 1; --b; }
        else --i;
    }
    return b * MODULUS + wheel_res[i];
}

/* Sieving primes, regrown as the scan advances. */
typedef struct { unsigned long *p; size_t n; unsigned long limit; } base_set;

static void base_set_ensure(base_set *bs, unsigned long need) {
    if (bs->p != NULL && bs->limit >= need) return;

    unsigned long m = need + need / 4 + 1024;   /* headroom: regrow rarely */
    size_t words;
    WORD *buf = self_sieve(m, &words);

    for (int pass = 0; pass < 2; ++pass) {
        size_t k = 0;
        for (unsigned long b = 0; b * MODULUS <= m; ++b) {
            for (int i = 0; i < WHEEL_SLOTS; ++i) {
                unsigned long v = b * MODULUS + wheel_res[i];
                if (v > m) break;
                if (v < 11) continue;
                unsigned long s = b * WHEEL_SLOTS + (unsigned long)i;
                if (((buf[s / BITS_PER_WORD] >> (s % BITS_PER_WORD)) & 1) == 0) {
                    if (pass == 1) bs->p[k] = v;
                    ++k;
                }
            }
        }
        if (pass == 0) {
            free(bs->p);
            bs->p = malloc(k * sizeof(unsigned long));
            if (bs->p == NULL) {
                fprintf(stderr, "out of memory: %zu sieving primes\n", k);
                exit(1);
            }
        } else {
            bs->n = k;
        }
    }
    bs->limit = m;
    free(buf);
}

/** mkdir -p: create a directory and any missing parents. **/
static void mkdir_p(const char *path) {
    char buf[1024];
    size_t n = strlen(path);
    if (n == 0 || n >= sizeof buf) {
        fprintf(stderr, "invalid output directory: %s\n", path);
        exit(1);
    }
    memcpy(buf, path, n + 1);
    while (n > 1 && buf[n - 1] == '/') buf[--n] = '\0';

    for (char *p = buf + 1; *p; ++p) {
        if (*p != '/') continue;
        *p = '\0';
        if (mkdir(buf, 0777) != 0 && errno != EEXIST) { perror(buf); exit(1); }
        *p = '/';
    }
    if (mkdir(buf, 0777) != 0 && errno != EEXIST) { perror(buf); exit(1); }
}

/** Open one results file, recovering its threshold and count from what is
 *  already there. */
static void rf_open(record_file *rf, const char *dir, const char *kind) {
    char path[1024];
    snprintf(path, sizeof path, "%s/%s.txt", dir, kind);

    rf->best = 0;
    rf->count = 0;

    FILE *r = fopen(path, "r");
    if (r != NULL) {
        char line[512];
        while (fgets(line, sizeof line, r) != NULL) {
            unsigned long n, p, v;
            if (line[0] == '#') continue;
            if (sscanf(line, "%lu %lu %lu", &n, &p, &v) == 3) {
                if (v > rf->best) rf->best = v;
                ++rf->count;
            }
        }
        fclose(r);
    }

    rf->out = fopen(path, "a");
    if (rf->out == NULL) { perror(path); exit(1); }
    if (rf->count == 0) {
        fprintf(rf->out, "# %s records: <n> <prime> <value> <gap_below> "
                         "<gap_above> <prev_prime> <next_prime>\n", kind);
        fflush(rf->out);
    }
}

static void rf_write(record_file *rf, const char *kind, unsigned long p,
                     unsigned long value, unsigned long below,
                     unsigned long above, unsigned long prev,
                     unsigned long next) {
    rf->best = value;
    ++rf->count;
    fprintf(rf->out, "%lu %lu %lu %lu %lu %lu %lu\n",
            rf->count, p, value, below, above, prev, next);
    fflush(rf->out);

    fprintf(stderr, "  *** %-11s record #%lu: p=%lu  value=%lu  "
                    "(%lu < %lu < %lu)\n",
            kind, rf->count, p, value, prev, p, next);
    fflush(stderr);
}

static void gap_checkpoint(gap_state *st) {
    fprintf(st->progress,
            "CHECKPOINT %lu %lu %lu %.1f  gap=%lu lonely=%lu aloof=%lu "
            "equidistant=%lu\n",
            st->p_prev, st->p_last, st->primes, st->seconds,
            st->gap.best, st->lonely.best, st->aloof.best, st->equi.best);
    fflush(st->progress);
}

/** Feed one prime into the stream, emitting any record it completes. **/
static void gap_feed(gap_state *st, unsigned long q) {
    ++st->primes;

    if (st->p_last != 0) {
        unsigned long gap = q - st->p_last;
        unsigned long down = (st->p_prev != 0) ? st->p_last - st->p_prev : 0;

        if (gap > st->gap.best) {
            /* The record concerns the pair (p_last, q); the lower neighbour
             * is carried along so every line holds a full prime triple. */
            rf_write(&st->gap, "gap", st->p_last, gap, down, gap,
                     st->p_prev, q);
        }

        if (st->p_prev != 0 || st->p_last == 2) {
            /* p_last is the centre; it now has both neighbours. The one
             * exception is 2, which has no lower neighbour -- OEIS A023186
             * and A096265 both take it as a(1) using its single gap to 3. */
            unsigned long below = (st->p_prev != 0) ? st->p_last - st->p_prev : gap;
            unsigned long above = gap;
            unsigned long near = (below < above) ? below : above;
            unsigned long total = (st->p_prev != 0) ? below + above : above;

            if (near > st->lonely.best) {
                rf_write(&st->lonely, "lonely", st->p_last, near, below, above,
                         st->p_prev, q);
            }
            if (total > st->aloof.best) {
                rf_write(&st->aloof, "aloof", st->p_last, total, below, above,
                         st->p_prev, q);
            }
            /* Balanced primes ranked against each other, not against all
             * primes -- so this can fire at a distance the lonely record
             * already reached with a lopsided prime. p = 2 is excluded: with
             * no lower neighbour it is not balanced. */
            if (st->p_prev != 0 && below == above && below > st->equi.best) {
                rf_write(&st->equi, "equidistant", st->p_last, below,
                         below, above, st->p_prev, q);
            }
        }
    }
    st->p_prev = st->p_last;
    st->p_last = q;
}

/* Returns 1 if the whole range was scanned, 0 if a signal cut it short. */
static int gap_search(unsigned long lo, unsigned long hi,
                      const char *dir, double ck_secs) {
    gap_state st;
    memset(&st, 0, sizeof st);

    mkdir_p(dir);

    /* Thresholds come from the results files; position from the checkpoint. */
    rf_open(&st.gap, dir, "gap");
    rf_open(&st.lonely, dir, "lonely");
    rf_open(&st.aloof, dir, "aloof");
    rf_open(&st.equi, dir, "equidistant");

    char path[1024];
    snprintf(path, sizeof path, "%s/progress.txt", dir);
    FILE *pr = fopen(path, "r");
    if (pr != NULL) {
        char line[512];
        while (fgets(line, sizeof line, pr) != NULL) {
            unsigned long a, b, n;
            double s;
            if (sscanf(line, "CHECKPOINT %lu %lu %lu %lf", &a, &b, &n, &s) == 4) {
                st.p_prev = a; st.p_last = b; st.primes = n; st.seconds = s;
                st.resumed = 1;
            }
        }
        fclose(pr);
    }
    st.progress = fopen(path, "a");
    if (st.progress == NULL) { perror(path); exit(1); }

    unsigned long pos = st.resumed ? st.p_last + 1 : lo;
    if (st.resumed) {
        fprintf(stderr, "resuming at %lu  (records: gap %lu, lonely %lu, "
                        "aloof %lu, equidistant %lu; "
                        "thresholds %lu / %lu / %lu / %lu)\n",
                pos, st.gap.count, st.lonely.count, st.aloof.count,
                st.equi.count, st.gap.best, st.lonely.best, st.aloof.best,
                st.equi.best);
    } else {
        fprintf(st.progress, "# CHECKPOINT <p_prev> <p_last> <primes> <seconds>\n");
        fflush(st.progress);
    }

    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);

    /* The wheel omits 2, 3, 5 and 7, so feed them by hand when starting low. */
    const unsigned long small[] = {2, 3, 5, 7};
    for (int i = 0; i < 4; ++i) {
        if (small[i] >= pos && small[i] <= hi) gap_feed(&st, small[i]);
    }

    WORD *buf = malloc(SEG_WORDS * sizeof(WORD));
    if (buf == NULL) { fprintf(stderr, "out of memory: segment buffer\n"); exit(1); }
    base_set bs;
    memset(&bs, 0, sizeof bs);

    unsigned long span = (unsigned long)(SEG_WORDS - 4) * BITS_PER_WORD
                       * MODULUS / WHEEL_SLOTS;
    double t_start = (double)clock() / CLOCKS_PER_SEC;
    double base_seconds = st.seconds;
    double next_ck = ck_secs, t_mark = 0.0;
    unsigned long pos_at_mark = pos;

    unsigned long seg_lo = (pos < 11) ? 11 : pos;
    while (seg_lo <= hi && !stop_requested) {
        unsigned long seg_hi = (hi - seg_lo < span) ? hi : seg_lo + span;

        base_set_ensure(&bs, isqrt_floor(seg_hi));

        unsigned long blk; int bi;
        unsigned long v_lo = wheel_ceil(seg_lo, &blk, &bi);
        unsigned long v_hi = wheel_floor(seg_hi);

        if (v_lo <= seg_hi && v_hi >= v_lo) {
            unsigned long s_lo = slot_of(v_lo), s_hi = slot_of(v_hi);
            unsigned long word_base = s_lo / BITS_PER_WORD;
            size_t nwords = (size_t)(s_hi / BITS_PER_WORD - word_base) + 2;

            memset(buf, 0, nwords * sizeof(WORD));
            for (size_t i = 0; i < bs.n; ++i) {
                mark_prime(buf, word_base, (unsigned long)nwords - 1,
                           bs.p[i], v_lo, v_hi);
            }

            unsigned long v = v_lo;
            for (unsigned long s = s_lo; s <= s_hi; ++s) {
                unsigned long w = s / BITS_PER_WORD - word_base;
                if (((buf[w] >> (s % BITS_PER_WORD)) & 1) == 0) {
                    gap_feed(&st, v);
                }
                if (++bi == WHEEL_SLOTS) { bi = 0; ++blk; }
                v = blk * MODULUS + wheel_res[bi];
            }
        }

        double now = (double)clock() / CLOCKS_PER_SEC - t_start;
        if (now >= next_ck || seg_hi == hi) {
            double rate = (now - t_mark) > 0
                        ? (double)(seg_hi - pos_at_mark) / (now - t_mark) : 0.0;
            st.seconds = base_seconds + now;
            fprintf(stderr,
                    "[%8.0fs] pos %.6e  %.2e nums/s  %lu primes  "
                    "best: gap %lu lonely %lu aloof %lu equidistant %lu\n",
                    st.seconds, (double)seg_hi, rate, st.primes,
                    st.gap.best, st.lonely.best, st.aloof.best, st.equi.best);
            fflush(stderr);
            gap_checkpoint(&st);
            next_ck = now + ck_secs;
            pos_at_mark = seg_hi;
            t_mark = now;
        }

        if (seg_hi == hi) break;
        seg_lo = seg_hi + 1;
    }

    st.seconds = base_seconds + (double)clock() / CLOCKS_PER_SEC - t_start;
    gap_checkpoint(&st);
    if (stop_requested) {
        fprintf(stderr, "stopped by signal; checkpointed at %lu\n", st.p_last);
    }

    free(buf);
    free(bs.p);
    fclose(st.gap.out);
    fclose(st.lonely.out);
    fclose(st.aloof.out);
    fclose(st.equi.out);
    fclose(st.progress);

    return !stop_requested;
}

/* Keeps the optimiser from discarding the repeated --repeat passes. */
static volatile unsigned long bench_sink;

int main(int argc, char *argv[]) {
    unsigned long limit = 500; // Default limit
    int count_only = 0;
    unsigned long repeat = 1;
    unsigned long from = 0;
    int has_from = 0;
    int gaps = 0;
    const char *out_path = NULL;
    double ck_secs = 15.0;

    /* Initialize dense packing map: residues [0..209] -> bit-slot [0..47]. */
    init_wheel();

    parse_args(argc, argv, &limit, &count_only, &repeat, &from, &has_from,
               &gaps, &out_path, &ck_secs);

    if (gaps) {
        if (out_path == NULL) {
            fprintf(stderr, "Error: --gaps needs --out <dir>.\n");
            exit(1);
        }
        /* Without an explicit limit, run to the end of the range. */
        unsigned long end = (limit == 500 && !has_from) ? ULONG_MAX : limit;
        if (limit == 500) end = ULONG_MAX;
        /* Exit 2 when interrupted, so a caller can tell "finished the range"
         * from "stopped early but checkpointed". */
        if (!gap_search(has_from ? from : 0, end, out_path, ck_secs)) return 2;
    } else if (has_from) {
        for (unsigned long r = 1; r < repeat; ++r) {
            bench_sink += sieve_window(from, limit, OUT_NONE);
        }
        sieve_window(from, limit, count_only ? OUT_COUNT : OUT_LIST);
    } else if (limit < 8) { // Small limit handled manually to avoid unnecessary allocation/memory overhead.
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
