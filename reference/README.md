# Reference implementation

`mod30.c` is Mike Koss's April 2021 Software Drag Race entry (`mckoss-c830`),
kept here as a benchmark baseline. It is **unmodified** — do not "fix" it.

It sieves a different way, and the contrast is the point:

|                | `mod30.c` (reference)       | `../sieve.c` (this repo)      |
|----------------|-----------------------------|-------------------------------|
| Wheel          | 8 of 30 (skips 2, 3, 5)     | 48 of 210 (skips 2, 3, 5, 7)  |
| Storage        | 1 bit per **odd number**    | 1 bit per **wheel candidate** |
| Memory         | n/16 bytes                  | n/35 bytes                    |
| Addressing     | shift and mask only         | needs `k % 210`, `k / 210`    |
| Mark pattern   | 64 steps, advance p words   | 192 steps, advance 3p words   |
| Counting       | test every candidate bit    | popcount whole words          |

The mod-30 wheel here is used only to *iterate* candidates. Storage stays a
plain odd-number bitmap, so 7 of every 15 stored bits (the multiples of 3 and
5) are never read. That waste is deliberate: it makes the bit index of n
exactly `n/2`, so addressing is a shift, and stepping by 2p advances the bit
index by a *constant* p. A constant stride is what lets the mask pattern
recur after only 64 steps.

The 2.2x memory gap is two effects, not one:

    n/16  ->  n/30   1.875x   from packing the wheel densely at all
    n/30  ->  n/35   1.167x   from mod-210 instead of mod-30 (i.e. 1/7)
    ------------------------
              2.19x

So the larger wheel is only the 1/7; most of the gap is density. Density is
also what makes `popcount` counting possible -- in a sparse odd bitmap the
never-marked composite bits would be counted as primes.

Dense mod-30 would be 8 bits = exactly **1 byte per 30 numbers**, with clean
power-of-two addressing. Dense mod-210 is 48 bits = 6 bytes per 210, which is
what forces the awkward `k / 210 * 6` arithmetic in `../sieve.c` -- the price
of that last 1/7.

## prime-check.h

The original included a `prime-check.h` that was not part of the source I was
given, so this one is **reconstructed** — just the pi(n) table the accuracy
assertion needs. If you still have the original, replace this file.

## Building

    make reference

    ./reference/mod30 --secs 5 --size 1000000
    mckoss-c830;29737;5.0;1;algorithm=wheel,faithful=yes,bits=1
    #           ^^^^^ passes  ^^^ seconds

`make bench` in the parent directory times both implementations together.


## The 2021 analysis, re-run in 2026

Mike's original write-up compared six algorithms on an Intel i7-8700K @ 3.7GHz
(full source: https://github.com/mckoss/Primes/blob/main/PrimeCAlgos/sieve.c).
Rebuilding that same file here, limit 1e6, ms per pass:

|                          | 2021 i7-8700K | this machine (32-bit) | (64-bit) |
|--------------------------|---------------|-----------------------|----------|
| Byte-map - 1 of 2        | 0.814         | 0.378                 | 0.379    |
| Bit-map  - 1 of 2        | 0.595         | 0.958                 | 1.131    |
| Bit-map  - 2 of 6        | 0.473         | 0.615                 | 0.792    |
| Bit-map  - 8 of 30       | 0.405         | 0.413                 | 0.584    |
| 1/2 Bit-map (dense)      | 0.653         | 1.122                 | 1.270    |
| 1/3 Bit-map (dense)      | 0.741         | 0.795                 | 0.818    |

Two of the 2021 conclusions still hold, and one has inverted.

**Still true: 32-bit words beat 64-bit** for every bitmap variant, on an
entirely different architecture five years later. (The byte-map is unaffected,
as it uses no words at all.)

**Still true: dense packing loses** -- 1/2 Bit-map is slower than Bit-map 1 of
2, and 1/3 Bit-map slower than 2 of 6, exactly as in 2021.

**Inverted: the byte-map is now the fastest of the naive algorithms** (0.378ms),
where in 2021 it was the slowest (0.814ms). A 1MB byte buffer sits comfortably
in a modern L2, so the memory that bitmaps save no longer pays for the bit
twiddling. This is the single biggest change in the table.

## Why ../sieve.c is dense anyway

The 2021 dense variants carry this comment in both `countPrimesMod2` and
`countPrimesMod6`:

    // I tried pre-calculating masks - but that just slowed it down.

That is the crux. Dense packing lost because its inner loop paid a division
per mark, and precalculating masks did not help *in that form*. The recurrence
has to be exact: for the mod-210 packing the (word offset, mask) pattern
repeats only after 48*max(1,W/16) steps, advancing a whole number of words.
Get that number right and the division disappears entirely -- which flips the
result. At limit 1e6 on this machine:

    your 2021 "Bit-map - 8 of 30"            0.413 ms
    mod30.c drag-race entry (+ mask pattern) 0.169 ms
    ../sieve.c dense mod-210 + pattern       0.107 ms

Note that the drag-race entry is *faster* with 64-bit words (0.169 vs 0.210),
unlike every algorithm in the table above -- once a mask pattern exists, wider
words merge more bits per store and the 2021 rule of thumb reverses.
