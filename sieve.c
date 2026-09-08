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
 */
#define MODULUS       210
#define BLOCK_BYTES   6

/* Maps residue r [0..MODULUS-1] -> dense bit slot [0..47], or -1 for residues
 * sharing a factor with 210 (multiples of 2, 3, 5 or 7). */
static int8_t dense_idx[MODULUS];

/** Builds the residue -> dense bit-slot map. **/
void init_wheel(void) {
    memset(dense_idx, -1, sizeof(dense_idx));

    int count = 0;
    for (int i = 1; i < MODULUS; ++i) {
        /* Keep every residue coprime to 210 -- including residue 1, since
         * 211, 421, 631, ... are genuine candidates. The *value* 1 itself is
         * excluded later, when residues are turned back into numbers. */
        if (i % 2 != 0 && i % 3 != 0 && i % 5 != 0 && i % 7 != 0) {
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
            "                   without the cost of formatting every result.\n\n"
            "Technical Details:\n"
            "  - Modulo M = 210. Excludes all direct multiples of primes (2,3,5,7).\n"
            "  - Memory footprint: Exactly 6 bytes per modulus block (~phi(210)/8 compressed).",
            prog);
}

/** Parses command line arguments safely. **/
void parse_args(int argc, char *argv[], unsigned long *limit, int *count_only) {
    for (int i = 1; i < argc; ++i) {
        if ((strcmp(argv[i], "--help") == 0) || (strcmp(argv[i], "-h") == 0)) {
            show_help(argv[0]);
            exit(0);
        } else if ((strcmp(argv[i], "--count") == 0) || (strcmp(argv[i], "-c") == 0)) {
            *count_only = 1;
        } else if (!isdigit((unsigned char)argv[i][0])) { 
            continue; // Gracefully ignore invalid flags
        } else {
            *limit = atol(argv[i]);
        }
    }
}

/** High-performance Modulo-210 Sieve implementation. **/
void sieve(unsigned long limit, int count_only) {
    if (limit < 8) return; 

    /* 
     * MEMORY ALLOCATION:
     * Each block covers exactly MODULUS numbers, densely packed into exactly BLOCK_BYTES.
     */
    unsigned long num_blocks = (limit / MODULUS) + 1;
    size_t mem_size = num_blocks * sizeof(uint8_t) * BLOCK_BYTES;

    // Zeroed memory: Bit=0 means Prime candidate. Bit=1 means Composite (marked).
    uint8_t *sieve_mem = calloc(mem_size, sizeof(uint8_t));
    if (sieve_mem == NULL) {
        fprintf(stderr, "out of memory: could not allocate %zu bytes\n", mem_size);
        exit(1);
    }

    /* Integer-exact floor(sqrt(limit)): the FP result can land one off,
     * especially when built with -ffast-math. Off-by-one here would leave
     * p*p unmarked for the largest sieving prime (e.g. 121 with limit=121). */
    unsigned long limit_sqrt = (unsigned long)sqrt((double)limit);
    while (limit_sqrt > 0 && limit_sqrt * limit_sqrt > limit) --limit_sqrt;
    while ((limit_sqrt + 1) * (limit_sqrt + 1) <= limit) ++limit_sqrt;
    
    /* SIEVE PHASE: We only need to sieve candidates up to sqrt(limit). */
    unsigned long end_block = (limit_sqrt / MODULUS) + 2; // +2 for safety
    if (end_block > num_blocks) end_block = num_blocks;

    for (unsigned long b = 0; b < end_block; ++b) {
        // Iterate through all residues in the current block: [0..MODULUS-1]
        for (int r = 0; r < MODULUS; ++r) {
            int idx = dense_idx[r];
            
            // If residue is -1, it's a multiple of 2,3,5,7 OR the number '1'. Skip it.
            if (idx == -1) continue; 

            unsigned long candidate = ((b * MODULUS) + r);

            // Optimization: Stop checking candidates > sqrt(limit).
            // Candidates ascend with r, so a break is safe here.
            if (candidate > limit_sqrt) break;

            // The value 1 sits in slot 0 of block 0; it is not a prime.
            if (candidate < 2) continue;

            /* Check byte/bit for 'candidate' to see if it's already marked composite */
            unsigned long offset = (idx >> 3) + ((b)*BLOCK_BYTES); 
            
            uint8_t mask_check = (uint8_t)(1 << (idx & 7));
            
            if ((sieve_mem[offset] & mask_check) == 0) { 
                // "candidate" is PRIME! Mark multiples starting at p*p.

                /* CRITICAL FIX: Check for overflow in square calculation */
                unsigned long long start_sq_ll = (unsigned long long)candidate * candidate;
                
                if (start_sq_ll <= limit) {
                    /* p is odd, so p*p is odd; stepping by 2p skips the even
                     * multiples, which can never occupy a wheel slot anyway. */
                    unsigned long step = 2UL * candidate;
                    for (unsigned long k = (unsigned long)start_sq_ll; k <= limit; k += step) {
                        int idx_k = dense_idx[k % MODULUS];

                        /* FIX: Only update valid dense packing slots! */
                        if (idx_k != -1) { 
                            unsigned long offset_k = ((k / MODULUS) * BLOCK_BYTES) + (idx_k >> 3);
                            
                            /* CRITICAL FIX: Mask MUST be derived from the slot index of 'k', NOT 'candidate'. */
                            uint8_t mask_k = (uint8_t)(1 << (idx_k & 7));
                            sieve_mem[offset_k] |= mask_k; 
                        }
                    }
                }
            }
        }
    }

    /* OUTPUT PHASE: Reconstruct primes from the dense bitset */
    unsigned long found = 0;
    if (!count_only) printf("Primes up to %lu:\n", limit);

    // Report base primes explicitly removed by our wheel (2, 3, 5, 7) if they are <= limit.
    const int base_primes[] = {2, 3, 5, 7};
    for (int i = 0; i < 4; ++i) {
        if ((unsigned long)base_primes[i] <= limit) {
            ++found;
            if (!count_only) printf("%d ", base_primes[i]);
        }
    }

    // Iterate through every modulus block up to the limit.
    for (unsigned long b = 0; b < num_blocks; ++b) { 
        unsigned long start_val = (b * MODULUS);
        
        // If the start of this block fully exceeds limit, stop the outer loop entirely.
        if (start_val > limit) break;

        for (int r = 0; r < MODULUS; ++r) {
            int idx = dense_idx[r];
            
            // Skip invalid residues (multiples of our base primes)
            if (idx == -1) continue;

            unsigned long val = start_val + r;
            if (val > limit) break; 

            /* FIX: Ensure '1' is never considered prime even if it slipped logic */
            if (val < 2) continue;

            // Bit Unset (0) => Prime!
            unsigned long offset = ((b)*BLOCK_BYTES) + (idx >> 3); 
            
            uint8_t mask = (uint8_t)(1 << (idx & 7));
            
            if ((sieve_mem[offset] & mask) == 0) {
                ++found;
                if (!count_only) printf("%lu ", val);
            }
        }
    }
    
    if (count_only) {
        printf("Primes up to %lu: %lu\n", limit, found);
    } else {
        // Safety flush to ensure line breaks
        printf("\n");
    }

    free(sieve_mem);
}

int main(int argc, char *argv[]) {
    unsigned long limit = 500; // Default limit
    int count_only = 0;
    
    /* Initialize dense packing map: residues [0..209] -> bit-slot [0..47]. */
    init_wheel();

    parse_args(argc, argv, &limit, &count_only);

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
        sieve(limit, count_only);
    }
    
    return 0;
}
