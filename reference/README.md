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
