# Modulo-210 Wheel Prime Sieve

A prime sieve in C using a 48-of-210 wheel, densely bit-packed, with a
precomputed marking pattern. Supports full sieving (`./sieve <limit>`) and
windowed sieving (`./sieve --from <lo> <hi>`) exactly across the whole 64-bit
range.

```
make            # build ./sieve
make test       # 28 tests
make test-slow  # 32 tests, including 1e6/1e7 range checks and the 2^63 window
make bench      # time it against the reference implementation
```

## Where it stands

At limit 1e6 the sieve runs in **0.10 ms**, about **1.7x** the mod-30
reference and **4.2x** the fastest algorithm in the 2021 analysis this work
started from, using **2.2x less memory** than either.

| limit | primes | sieve | +listing | `reference/mod30` | speedup |
|-------|--------|-------|----------|-------------------|---------|
| 1e5 | 9,592 | 0.0136 ms | 0.67 ms | 0.0171 ms | 1.26x |
| 1e6 | 78,498 | 0.1005 ms | 5.28 ms | 0.1688 ms | 1.68x |
| 1e7 | 664,579 | 1.3509 ms | 45.71 ms | 2.8736 ms | 2.13x |
| 1e8 | 5,761,455 | 16.77 ms | 381.7 ms | 38.46 ms | 2.29x |

## Benchmark environment

Every number in this file and in `reference/README.md` was measured on:

- **Apple M1 Max** (MacBookPro18,2), 10 cores (8 performance + 2 efficiency)
- 64 GB RAM, 64 KB L1d, 4 MB L2
- macOS 26.5.2 (arm64), Apple clang 21.0.0
- `-O3 -march=native -flto -funroll-loops`

The L2 size matters for one of the findings below. The original 2021 analysis
was run on an Intel i7-8700K @ 3.7GHz, and several conclusions differ between
the two machines.

`-ffast-math` is deliberately **not** used. The only floating point in the
program is one `sqrt()` at startup, so it buys nothing -- and an `-ffast-math`
build is what made the original `floor(sqrt)` bug reachable.

---

## History

### 1. The inherited code did not work

`sieve.c` arrived after a weaker model had thrashed on it. It printed `2 3 5 7`
and nothing else, for any limit. The cause was one line:

```c
memset(dense_idx, -1, sizeof(dense_idx));
...
if (i == 1) { ... } else if (dense_idx[i] == -1) continue; dense_idx[i] = count++;
```

The init loop read `dense_idx` as if it were an *input*, but it had just been
memset to `-1`. The guard fired every iteration, `count` stayed 0, and all 210
residues stayed invalid, so every candidate was skipped in both the sieve and
output phases. That single line is also the signature of the thrashing: three
"fixes" stacked on one line, with `i == 1` handled twice.

Three more real bugs sat behind it:

- **Residue 1 was dropped from the wheel**, justified as "1 is not prime". But
  residue 1 also holds 211, 421, 631, ...; excluding it would have silently
  lost every prime congruent to 1 mod 210 *and* left 47 slots in a table whose
  whole premise is 48 bits = 6 bytes. Only the *value* 1 needs excluding.
- **`if (candidate < 2 || candidate > limit_sqrt) break;`** shared a `break`
  between the sqrt cutoff and the value 1. Once residue 1 is restored, that
  aborts block 0's scan at the first candidate and suppresses *all* sieving.
- **`floor(sqrt(limit))` in floating point** can land one low, leaving `p*p`
  unmarked for the largest sieving prime -- 121 reported prime at limit 121.

### 2. The tests could not have caught any of it

Three overlapping test scripts existed. One miscounted its own total
("Passed: 5 / 2"). Another used `local` at file scope and grepped the literal
string `"./sieve_bin 200"` instead of the command's output, so its wheel-gap
test passed without testing anything. All three checked only prime *counts*,
which structurally cannot catch a wheel bug that drops one prime and invents
another -- exactly this code's failure mode.

They were replaced with one harness that compares **exact prime lists** against
a plain Eratosthenes sieve, cross-checked by trial division, deterministic
Miller-Rabin, and published pi(n) values so a shared mistake between two
implementations cannot hide. Every bug above has a named regression test.

Two vacuity guards are deliberate: `assert wheel_primes` and
`assert expected` in the tests that build their own case lists. A test that
silently iterates an empty list is how the old script came to pass while
testing nothing.

### 3. Optimisation, in measured steps

The reference point throughout is `reference/mod30.c`, Mike Koss's April 2021
Software Drag Race entry, kept verbatim in this repo. Its design contrast with
this one is documented in `reference/README.md`.

| step | 1e6 | note |
|------|-----|------|
| after correctness fixes | 0.920 ms | |
| + wheel iteration, mask pattern, popcount counting | 0.116 ms | 8.0x |
| + 48x48 startup table (division-free build) | 0.109 ms | |
| + skip the pattern when it cannot amortise | 0.098 ms | |

**The mask pattern.** Stepping a prime through consecutive wheel residues
advances the slot index by exactly `48*p` bits per 48 steps. For the *word*
offsets and masks to recur, that advance must also be a whole number of words:
`48*p*m = 0 (mod W)`. Since `p` is odd and 48 contributes `2^4`, this needs
`m = max(1, W/16)` -- a 192-step pattern advancing exactly `3*p` words at
64 bits. Build it once per prime, then replay: no division, no modulo, no
shifting in the marking loop.

**No wasted steps.** Marking walks multiples `p*c` with `c` over the wheel
rather than stepping by `2p` and discarding the 54.3% of steps that land on no
slot. At 1e6 that is 472,978 iterations down to 216,268.

**Popcount counting.** Slots ascend with value, so the candidates up to a limit
are exactly the first N bits. `--count` popcounts whole words instead of
testing bits: ~3.6K word reads instead of ~229K bit tests at 1e6. This is only
possible *because* the packing is dense -- in a sparse odd-number bitmap the
never-marked composite bits would be counted as primes.

**Where the startup table fell short.** The 48x48 table removes the division
from the pattern build (`slot(p*c) = (p*48)*C + P*(48*rb) + T[a][b]`, and `P`
and `a` are already the sieve loop's own indices). It was predicted to make
64-bit words win at every size. It did not -- removing the division does not
remove the 192 *iterations*. Measuring showed the real cost: at 1e5, **62% of
sieving primes have fewer multiples in range than the pattern has entries**.
We were building a 192-entry table to set two bits. `MARK_DIRECT_BELOW` marks
directly below `4/3 * PATTERN_STEPS` marks -- a threshold that held at exactly
that ratio across all four word widths.

### 4. Word size

Mike's 2021 analysis found 32-bit words fastest for every bitmap variant, even
in a 64-bit build. **That reproduces on the M1 Max, five years and one
architecture later** -- rebuilding his 2021 `sieve.c` here, 32-bit beats 64-bit
across the board (8-of-30: 0.413 ms vs 0.584 ms at 1e6).

It does *not* hold once a mask pattern exists. Both `reference/mod30.c` and
this sieve are faster with 64-bit words, because wider words merge more bits
per store and the pattern is built once rather than per mark. Current numbers:

| limit | 8-bit | 16-bit | 32-bit | 64-bit |
|-------|-------|--------|--------|--------|
| 1e5 | 0.0131 | **0.0125** | 0.0126 | 0.0138 |
| 1e6 | 0.1214 | 0.1156 | 0.1018 | **0.0994** |
| 1e7 | 1.6588 | 1.5997 | 1.4397 | **1.3440** |
| 1e8 | 20.181 | 19.764 | 17.767 | **16.442** |

`WORD_BITS` defaults to 64; `make WORD_BITS=32` overrides. All four widths are
tested (`make test-widths`), since the packing geometry differs per width.

### 5. Memory

The dense mod-210 packing uses **n/35 bytes** -- 28.6 KB at 1e6, 2.86 MB at
1e8 -- against `mod30.c`'s n/16. That 2.19x is two separate effects, and it is
worth keeping them apart:

```
n/16  ->  n/30    1.875x   from packing the wheel densely at all
n/30  ->  n/35    1.167x   from mod-210 instead of mod-30 (i.e. 1/7)
                  2.19x
```

**The larger wheel is only the 1/7.** Most of the gap is density. And density
is what costs us: dense mod-30 would be 8 bits = exactly 1 byte per 30 numbers,
with clean power-of-two addressing, where dense mod-210 is 48 bits = 6 bytes
per 210 -- which is what forces the awkward `k / 210 * 6` arithmetic. We pay
real addressing complexity for that last 1/7.

Nothing is wasted for alignment. The 48-bit blocks straddle word boundaries,
and that straddling is exactly *why* the 64-bit pattern needs 192 steps: block
*k* starts at bit `48k`, so `48k mod 64` cycles 0, 48, 32, 16 before
realigning. The cost of density shows up as pattern length, not memory --
28,573 to 28,584 bytes at 1e6 across all four widths.

### 6. What changed since 2021

Rebuilding the six-algorithm 2021 analysis on this machine, limit 1e6:

| | 2021 i7-8700K | M1 Max (32-bit) | (64-bit) |
|---|---|---|---|
| Byte-map - 1 of 2 | 0.814 | **0.378** | 0.379 |
| Bit-map - 1 of 2 | 0.595 | 0.958 | 1.131 |
| Bit-map - 2 of 6 | 0.473 | 0.615 | 0.792 |
| Bit-map - 8 of 30 | 0.405 | 0.413 | 0.584 |
| 1/2 Bit-map (dense) | 0.653 | 1.122 | 1.270 |
| 1/3 Bit-map (dense) | 0.741 | 0.795 | 0.818 |

Two 2021 conclusions hold; one has inverted.

- **Still true:** 32-bit beats 64-bit for every one of these variants.
- **Still true:** dense packing loses to sparse, in both pairs.
- **Inverted:** the byte-map is now the *fastest* naive algorithm (0.378 ms)
  where it was the *slowest* in 2021 (0.814 ms). A 1 MB byte buffer sits
  comfortably inside this machine's 4 MB L2, so the memory that bitmaps save no
  longer pays for the bit twiddling. This is the single largest change.

**Why this sieve is dense anyway.** Both 2021 dense variants carry the comment:

```c
// I tried pre-calculating masks - but that just slowed it down.
```

That is the crux. Dense packing lost because its inner loop paid a division per
mark, and precalculating masks did not help *in that form*. The recurrence has
to be exact -- for mod-210 the pattern repeats only after `48*max(1,W/16)`
steps, advancing a whole number of words. Get that number right and the
division disappears, which flips the result:

```
2021 "Bit-map - 8 of 30"                  0.413 ms
mod30.c drag-race entry (+ mask pattern)  0.168 ms
this sieve (dense mod-210 + pattern)      0.098 ms
```

### 7. Windowed sieving

`--from <lo>` reports only primes in `[lo, hi]`, allocating for the window
alone. One `mark_prime()` serves both paths -- a window buffer simply starts at
a non-zero `word_base`, and since bit positions within a word are unchanged,
the mask pattern applies verbatim. Sieving primes come from an ordinary sieve
to `sqrt(hi)`, which dominates the cost:

| window `[x, x+1e5]` | primes | peak RSS | time |
|---|---|---|---|
| x = 1e6 | 7,216 | 1.3 MB | 0.002 s |
| x = 1e12 | 3,614 | 1.4 MB | 0.004 s |
| x = 1e15 | 2,805 | 2.2 MB | 0.032 s |
| x = 1e18 | 2,398 | 28.6 MB | 0.97 s |
| x = 2^63 | ~40 | ~90 MB | 4.0 s |

Two overflow bugs surfaced at the top of the range, both of which returned
*confident wrong answers* rather than failing:

- `parse_args` used `atol()`, which returns a **signed** long. Any bound at or
  above 2^63 saturated at `LONG_MAX` and the window silently came back empty.
- The listing walk advanced by value (`blk * 210 + residue`). One step past the
  last candidate below `ULONG_MAX`, that expression wraps to a small number and
  restarted the walk, emitting ~33 million bogus "primes". It now loops on the
  slot index, which cannot wrap.

Correctness at that magnitude is verified against deterministic Miller-Rabin,
since no sieve reference reaches 2^63.

### 8. An experiment: how sparse do primes get?

The question was whether a run of 100,000 consecutive integers containing only
one prime is findable. Scanning `[1e18, 1e18+1e7]` -- 241,295 primes in 1.2 s:

```
100,000-wide windows:  min 2275   max 2529   mean 2414
predicted mean:        100000/ln(1e18) = 2413
largest gap seen:      414, after 1000000000007133977
```

Even the *sparsest* 100,000-run at 1e18 holds 2,275 primes. Two ways to see how
far away 1 is:

- The **average** reaches one prime per 100,000 when `ln(x) = 100000`, i.e.
  `x ~ 10^43429`.
- The **first** such stretch, on Cramer's heuristic (max gap ~ `(ln x)^2`),
  needs a gap of 100,000, first expected near `e^316 ~ 10^137`.

Against the 64-bit ceiling of `10^19.3`, that is short by about `10^118`. No
sieve of any design reaches it -- the limit is not precision or memory, it is
that such runs do not exist below roughly `10^137`.

---

## Layout

```
sieve.c            the sieve
test_sieve.py      32 tests; --slow adds range checks, --binary tests a variant
bench.py           timing harness, compares against reference/mod30
Makefile           all, test, test-slow, test-widths, bench, reference, clean
reference/         Mike Koss's 2021 mod-30 drag-race entry, kept verbatim
```
