#ifndef PRIME_CHECK_H
#define PRIME_CHECK_H
typedef struct { int n; int piN; } PRIME_CHECK;
static PRIME_CHECK primeChecks[] = {
    {10, 4}, {100, 25}, {1000, 168}, {10000, 1229}, {100000, 9592},
    {1000000, 78498}, {10000000, 664579}, {100000000, 5761455},
};
#define NUM_CHECKS (int)(sizeof(primeChecks) / sizeof(primeChecks[0]))
#endif
