# Prime Scanner

An exhaustive scan of the primes from zero, built to improve how the OEIS
documents **record prime gaps** and their relatives: the *lonely*, *aloof* and
*equidistant* primes.

Those sequences are published as lists of terms, but a record sequence says
more than its terms. Term *n* is only a term because nothing below it did
better, and that is known only by looking at everything below it. What an
exhaustive scan contributes is:

- **independent confirmation.** Every published term is re-derived from zero,
  with no seed, and matched position by position.
- **completeness bounds.** "No further terms below *x*" is a claim a targeted
  search cannot make.
- **the bounding primes.** Each record comes with both of its neighbouring
  primes, so anyone can check it without rerunning the scan. OEIS has that
  for gaps (an a-file 10 terms out of date) and aloof (as separate sequences),
  but not for lonely or equidistant.
- **stale-entry repair.** Sequences in one family describe the same records,
  and some members have fallen far behind their siblings.

Where that stands, and what is being submitted, is in
[`oeis/README.md`](oeis/README.md) and
[`oeis/submit/edits.yaml`](oeis/submit/edits.yaml).

## The sequences

| family | OEIS | record of | first terms |
|--------|------|-----------|-------------|
| **gap** | [A002386](https://oeis.org/A002386) (lower prime), [A000101](https://oeis.org/A000101) (upper), [A005250](https://oeis.org/A005250) (size) | `nextprime(p) − p` | 2, 3, 7, 23, 89, 113, 523, … |
| **lonely** | [A023186](https://oeis.org/A023186), [A023187](https://oeis.org/A023187) (distance) | `min(gap below, gap above)` | 2, 5, 23, 53, 211, 1847, … |
| **aloof** | [A096265](https://oeis.org/A096265); also [A031133](https://oeis.org/A031133)/[A031134](https://oeis.org/A031134)/[A031132](https://oeis.org/A031132), indexed one lower | `nextprime(p) − prevprime(p)` | 2, 3, 5, 7, 23, 53, 89, … |
| **equidistant** | [A058867](https://oeis.org/A058867), [A058868](https://oeis.org/A058868) (distance) | the common gap, ranked among *balanced* primes only | 5, 53, 211, 16787, 69623, … |
| **pairwise** | [A087770](https://oeis.org/A087770) | a chain, not a maximum: gap below *and* gap above both beat the previous term's | 2, 3, 7, 23, 89, 211, 1847, … |
| **balanced-lonely** | not yet in OEIS — [draft](oeis/submit/edits.yaml) | lonely records that are also balanced primes | 5, 53, 211, 26923643849953, 187891466722913 |

Several sequences are in play at once, so `a(n)` would be ambiguous. Terms are
written `gap(n)`, `lonely(n)`, `aloof(n)`, `equidistant(n)` and `pairwise(n)`:
the *n*th term of A002386, A023186, A096265, A058867 and A087770. The full list
of related sequences, covered or not, is in [`oeis/README.md`](oeis/README.md).

Equidistant and balanced-lonely are easy to conflate. A058867 ranks balanced
primes only against each other, so 16787, with gaps (24, 24), is a term there
even though `lonely(9) = 16033` had already reached 24 with gaps (26, 24).
Balanced-lonely requires a record over *all* primes, so it is a 5-term
subsequence of A058867's 30.

## Reproducing the results

Requires a C compiler and Python 3; nothing else.

```
make                 # build ./sieve
make test            # exact prime lists vs Eratosthenes, Miller-Rabin and pi(n)
make test-slow       # adds the 2^64 window, the OEIS reproduction to 1e7,
                     #   and an 8-way parallel merge vs the serial result
```

Run the scan from zero. With no `--to` it runs open-ended in rounds of about
ten minutes, merging after each; Ctrl-C (or SPACE to pause) stops cleanly, and
rerunning the same command resumes:

```
python3 pgaps.py --jobs 8 --out myrun              # open-ended
python3 pgaps.py --to 1e14 --jobs 8 --out myrun    # or stop at a bound
python3 pgaps.py --out myrun --status              # each sequence's frontier
```

When a sequence is added to a run that has already come a long way, the
driver asks whether to catch it up from zero first or to skip that for now.
Skipping keeps every sequence advancing and holds the new one's candidates
until a later catch-up; `--catch-up` and `--skip-catch-up` answer in advance.

Then check it:

```
python3 check_oeis.py myrun            # is the SCAN right?
python3 oeis_audit.py --results myrun  # is OEIS complete?
```

With `--results`, `oeis_audit.py` also regenerates
[`oeis/submit/`](oeis/submit/): every contribution the data supports right now,
as one draft per sequence, plus the files to upload and a bookmarklet that
fills the OEIS edit form
-- new terms, completeness bounds, stale b-files and a-files, one-way
cross-references -- with progress read from `oeis/submissions.txt`. The file
is generated, so it is never edited by hand.

`check_oeis.py` diffs every term below the run's frontier against the
published b-files, position by position, and re-tests every record prime with
a deterministic Miller-Rabin independent of the sieve. `oeis_audit.py` reports
which family members lag their siblings, which lack b-files or a-files, and
where the frontier stands against each family. Both read cached copies in
[`oeis/`](oeis/README.md); add `--refresh` to refetch.

Use `--jobs` equal to the free *performance* cores. Wall time on an M1 Max
with 8 workers, from the measured rate curve:

| to | covers | 8 workers | core-hours |
|----|--------|-----------|------------|
| 1e14 | gap(59), lonely(52), aloof(62), equidistant(29) | 2.7 h | 21 |
| 9.42e14 | every published lonely and equidistant term | 30 h | 243 |
| 1.70e15 | every published aloof term; gap(64) | 58 h | 467 |
| 2.07e15 | where [`fresh/`](fresh/README.md) stands | 73 h | 586 |

Those figures are for the current binary. `fresh/` itself took about 850
core-hours, since part of it ran before the 2x speedup and A058867 was caught
up separately; see [`oeis/README.md`](oeis/README.md).

### Output

Each sequence gets a file of record lines:

```
<n> <prime> <value> <gap_below> <gap_above> <prev_prime> <next_prime>
```

The first two columns are an OEIS b-file. The last two make each line a
self-contained certificate: `prev`, `prime` and `next` are prime and nothing
lies between them. `frontier.txt` holds, per sequence, the point below which
the scan is provably contiguous; nothing may be claimed above it.
[`fresh/README.md`](fresh/README.md) describes the run directory in full.

## How it works

**The sieve** (`sieve.c`) uses a mod-210 wheel (2·3·5·7), keeping the 48
residues coprime to 210, bit-packed densely at n/35
bytes, sieving in 512 KB segments across the full 64-bit range. The inner loop
replays a precomputed marking pattern: for each prime, the word offsets and
masks recur exactly every 192 wheel steps, so marking needs no division. Prime
extraction count-trailing-zeros its way through each word, and each sieving
prime carries a cursor from one segment to the next.

**The records** come from a three-prime sliding window; `./sieve --gaps` keeps
a running maximum per sequence and flushes each record as it is found.

**The parallel driver** (`pgaps.py`) shards each round across workers by
estimated time, not length. Its merge is the correctness argument: a worker
cannot know whether its local best beats everything below its shard, so it
emits *candidates*, and a serial pass applies the running-maximum rule in
order. A global record must also be a local record in its own shard, so none
can be missed. Results merge only below the contiguous frontier, since merging
across an unfinished shard could promote a smaller value when the real record
sits in the hole.

**Gaps across boundaries.** Each worker, including the first in a new round,
starts up to 100,000 integers before its assigned range (less for small
shards). This overlap reconstructs the three-prime window, so a gap crossing
a worker or round boundary is caught by the following worker or round. The
merge keeps these discoveries even when their centre prime is below the new
round's start, and removes duplicates. This relies on the overlap containing
enough preceding primes; the code does not dynamically check that condition.
An interrupted worker instead restores its last two primes from its checkpoint.
At the final endpoint, a gap whose upper prime lies beyond the endpoint is
still unresolved: the reported frontier can reach that endpoint before the
crossing gap is recorded. Continuing the scan resolves it.

**The ceiling** is 2^64 ≈ 1.84e19, a deliberate choice of word size, because
128-bit division would slow every scan. Time binds long before that: from
today's frontier, 1e16 is about 16 days away on 8 cores and gap(65) at 4.38e16
about four months. Confirmed gap records already reach 1.014e20, past the
ceiling, so there is published data to check against across the whole range,
though the next checkpoint after gap(64) is gap(65), 26x further out.

## History

The project began in September 2026 as a benchmarking exercise. It took a
mod-210 wheel sieve that an earlier attempt had left broken (it printed
`2 3 5 7` for any limit) and measured it against Mike Koss's April 2021
Software Drag Race entry, kept verbatim in [`reference/`](reference/README.md).

1. **Correctness.** Four bugs were fixed: a table initialised as if it were
   input, residue 1 dropped from the wheel, a shared `break` that suppressed
   all sieving, and a floating-point `floor(sqrt)` one low. The old tests
   compared only prime *counts*, which cannot catch a wheel that drops one
   prime and invents another; they were replaced with exact-list comparisons.
2. **Speed.** A mask pattern, wheel-stepped multiples, popcount counting and a
   division-free pattern build took limit 1e6 from 0.920 ms to **0.098 ms**:
   1.7x the mod-30 reference in 2.2x less memory. That compares two whole
   implementations, not wheel sizes in isolation. Of the memory saving, only
   1/7 comes from mod 210 over mod 30; the rest is dense packing, and the
   larger wheel costs `k / 210` addressing and a 192-step pattern. 64-bit words
   beat 32-bit once a pattern exists, reversing the 2021 finding.
3. **Range.** Windowed sieving was extended to 2^64, fixing two overflows that
   returned confident wrong answers rather than failing.
4. **Record gaps.** `--gaps` was added and reproduced A002386, A023186 and
   A096265 from zero. A single-threaded seeded run ([`results/`](results/README.md))
   was followed by the parallel driver and the unseeded run in `fresh/`.
5. **Throughput.** CTZ extraction and per-prime cursors together sped the scan
   up 1.98x at 5e14, and balanced-lonely and A058867 tracking were added, with
   A058867 caught up over ground already covered.

Two mistakes shaped the tooling. An "8 new aloof terms" claim turned out to be
data already published under A031133/A031134, so `check_oeis.py` now checks
whole families, not single A-numbers. And a driver killed by `timeout` orphaned
its workers, which silently dropped lonely(44) until the check caught it. The
driver now locks its directory and cannot exit without stopping its workers.

Timings are from an Apple M1 Max (8 performance + 2 efficiency cores, 64 GB),
macOS 26.5, Apple clang 21, `-O3 -march=native -flto`. On Apple silicon
`sysctl hw.l1dcachesize` reports the *efficiency* cores' caches; the
performance cores are under `hw.perflevel0.*` (128 KB L1d, 12 MB L2 per
cluster of four).

## Layout

```
sieve.c            the sieve; ./sieve <limit>, --from <lo> <hi>, --count, --gaps
pgaps.py           parallel driver: shard, scan, merge, catch up a new sequence
check_oeis.py      term-by-term check of a run against the OEIS b-files
oeis_audit.py      where each family's terms, b-files and a-files stand
oeis/              cached b-files, progress summary, TODO, draft submissions
fresh/             the unseeded from-zero scan, committed at each checkpoint
results/           the earlier single-threaded seeded scan, to 5.6e12
test_sieve.py      the test suite; --slow adds the long checks
bench.py           timing harness against reference/mod30
reference/         Mike Koss's 2021 mod-30 drag-race entry, verbatim
Makefile           all, test, test-slow, test-widths, bench, reference, clean
```
