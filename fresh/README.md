# Search results — from scratch, in parallel

Live output of `pgaps.py`, the parallel driver, run open-ended across 8 workers:

```
python3 pgaps.py --jobs 8 --out fresh
```

Unlike [`results/`](../results/README.md), this search was **not seeded**. It
started at 0 with every threshold at zero and re-derived all three sequences
from the first term, so `gap.txt` begins at p=2 rather than at a published
record. That makes the whole file a check on the scanner rather than just its
tail: a seeded run can only be wrong about new terms, an unseeded one has to
reproduce every known term to stay aligned.

It has since passed the extent of `results/` (5.6e12), which this run covered
in its first few minutes, so `results/` is kept only as the record of the
original single-threaded scan.

## Files

| file | contents |
|------|----------|
| `gap.txt` | record prime gaps — [A005250](https://oeis.org/A005250) / [A002386](https://oeis.org/A002386) |
| `lonely.txt` | record distance to the *nearer* neighbour — [A023186](https://oeis.org/A023186) |
| `aloof.txt` | record total span between *both* neighbours — [A096265](https://oeis.org/A096265) |
| `frontier.txt` | the resume point — see below |

Each results line is

```
<n> <prime> <value> <gap_below> <gap_above> <prev_prime> <next_prime>
```

The first two columns are an OEIS b-file. The last two make every line
self-contained proof: check that `prev`, `prime` and `next` are all prime and
that nothing lies between them, and the record stands without rerunning the
scan. `value` is whichever quantity that sequence maximises — `gap_above` for
gaps, `min(below, above)` for lonely, `below + above` for aloof.

Because three sequences are in play at once, terms are written `gap(n)`,
`lonely(n)` and `aloof(n)` rather than `a(n)` — the nth term of A002386,
A023186 and A096265 respectively.

## The frontier, and why it is not a position

A single-threaded run resumes from the last line of `progress.txt`, because
everything below that point has been visited. That is not true of a parallel
run: eight workers advance through eight disjoint shards at once, so at any
instant the covered region is full of holes. Merging across a hole would
promote a later, smaller value to "record" when the real one sits in the gap.

So `frontier.txt` holds the highest point below which coverage is *provably
contiguous* — the start of the lowest shard still running. The merged files
are truncated to it, and the next round starts there. It is the only durable
resume state, and it only ever moves forward.

## What is committed, and what is not

Committed: the three merged record files and `frontier.txt`. Together they are
the complete, resumable state of the search — drop them into an empty
directory, rerun the same command, and it picks up at the frontier.

Not committed (see `.gitignore`):

| path | why |
|------|-----|
| `shards/` | per-worker candidates, checkpoints and logs. `pgaps.py` deletes and re-creates this tree at the start of **every** round, so its contents describe only the round in flight. Records worth keeping have already been merged upward. |
| `round.txt` | the `[lo, hi) jobs` of the round in flight; meaningless without the matching `shards/` tree. |
| `lock` | the driver's PID, to keep two drivers off one output directory. |

A worker's candidate file is *not* a record file: it holds every local maximum
that worker saw within its own shard, most of which lose to a larger value in
some other shard. Only the merge applies the running-maximum rule across all
of them.

## Status

Checked with `python3 check_oeis.py fresh`, a full positional diff against the
published b-files — every published term below the frontier must appear at the
same index, with nothing missing and nothing extra — plus a deterministic
Miller-Rabin re-test of each record, independent of the sieve.

Snapshot at frontier 385,545,873,435,488 (≈3.86e14, ~20 hours on 8 cores).
Rerun the command above for the current numbers — the scan is still moving.

| sequence | published | …below the frontier | ours | |
|----------|-----------|---------------------|------|---|
| gap A002386 | 85 | 61 | 61 | exact match |
| lonely A023186 | 56 | 54 | 54 | exact match |
| aloof A096265 | 55 | 55 | 63 | **8 terms beyond the published sequence** |

The middle column is the honest denominator: a term above the frontier is not
a miss, it is simply not reached yet. Only A096265 is fully consumed — it ends
at 9.29e11, which worker 0 passed in the first few minutes.

The new aloof terms:

```
aloof(56) =   1032148488557   span 678
aloof(57) =   3605572653889   span 690
aloof(58) =   4079970755417   span 700
aloof(59) =   5061226833937   span 760
aloof(60) =  12772332382939   span 780
aloof(61) =  19535748743177   span 838
aloof(62) =  21185697626267   span 900
aloof(63) = 117102787055963   span 944
```

A096265 was published to aloof(55) = 929,156,727,137. `aloof(56)` was also found by the
earlier single-threaded run in `results/`, which had been *seeded* with the 55
published terms; this run rediscovered it having been told nothing, which is
the stronger of the two claims.

None of these have been submitted to OEIS or confirmed by a second
implementation.

## How far can this go?

Not a precision question. The ceiling is a word size, not a limit of the
method: every prime, window bound and neighbour is stored in an
`unsigned long`, 64-bit here, so nothing above
ULONG_MAX = 18,446,744,073,709,551,615 ≈ 1.84e19 is representable. There is no
`__int128` anywhere in `sieve.c`. The frontier is roughly 48,000x below it.

That is a deliberate trade. The inner loop is bit-index arithmetic —
`s / BITS_PER_WORD`, `s % BITS_PER_WORD`, `p * wheel_scaled[t]` — all single
instructions at 64 bits and multi-instruction sequences at 128, with division
much the worse. Widening the type would slow every scan to buy range that
takes centuries to reach.

The ceiling is a real, usable 1.84e19 rather than "breaks somewhere near the
top", because the wheel indexes the bitmap by slot rather than by value, and
slots run at 48/210 = 0.229 of the value range:

```
ULONG_MAX        18,446,744,073,709,551,615
max slot index    4,216,398,645,419,326,127     4.38x of headroom
```

Three spots need care even so, each a fixed regression:

| | |
|---|---|
| `parse_args` | `strtoul`, not `atol` — a signed long saturates at 2^63 and the window silently came back empty |
| the candidate walk (`sieve.c:608`) | loops on the slot index, since the next *value* past the last wraps to a small number and restarted the walk |
| `ceil(lo / p)` (`sieve.c:342`) | written as `need = lo/p; if (need*p < lo) ++need`, because `(lo + p - 1)` wraps |

`isqrt_floor` likewise corrects its `double` seed by division rather than
`r*r`, so it stays exact to ULONG_MAX. `test_window_at_top_of_range` checks
the top 2000 integers below ULONG_MAX against Miller-Rabin; it is marked slow
because at that height the sieving primes run to sqrt(2^64) = 4,294,967,296.

Worth noting the ceiling is not where knowledge runs out: confirmed A002386
terms reach 1.014e20, 5.5x *above* it. Even a scan at the ceiling would still
have published data to check against.

Memory is not the constraint either. Each worker holds the sieving primes up
to sqrt(hi), 8 bytes each:

| hi | sieving primes | per worker | 8 workers |
|----|----------------|-----------|-----------|
| 1e15 | 1.8e6 | 14 MB | 0.1 GB |
| 1e16 | 5.4e6 | 41 MB | 0.3 GB |
| 1e18 | 4.8e7 | 368 MB | 2.9 GB |
| 2^64 | 1.9e8 | 1.5 GB | 11.5 GB |

The binding constraint is time. Integrating the measured rate curve from the
current frontier, at the 8-worker throughput actually observed here:

| target | added time |
|--------|-----------|
| 9.41e14 — last published A023186 term | +2.6 days |
| 1.19e15 — gap(62) | +3.9 days |
| 1.69e15 — gap(64) | +6.7 days |
| 1e16 | +66 days |
| 4.38e16 — gap(65) | +1.1 years |
| 1e18 | ~47 years |
| 2^64 | ~1500 years |

## Extending, not just validating

9.41e14 is only a milestone for *validation* — it is where the published
A023186 data runs out. It is not a stopping point for the search, and past it
the sequences change roles:

| sequence | past 9.41e14 |
|----------|--------------|
| A096265 aloof | **extension** — published data ended at 9.3e11; every term since is new, 8 so far |
| A023186 lonely | **extension** — published data ends at lonely(56) = 941,114,429,467,073; lonely(55) = 475,963,705,368,391 is the last one still ahead |
| A002386 gaps | still **validation** — confirmed terms run to 1.014e20, past this program's own 1.84e19 ceiling, so it supplies free checkpoints forever |

That last row is the useful one: A002386 costs nothing and keeps confirming the
scan long after the other two have gone past what anyone has published. But the
checkpoints are not evenly spaced, and there is a notable drought:

```
gap(62) = 1189459969825483   1.19e15
gap(63) = 1686994940955803   1.69e15
gap(64) = 1693182318746371   1.69e15
gap(65) = 43841547845541059  4.38e16   <- 26x jump, no maximal gap in between
```

### Is the A002386 b-file trustworthy that far out?

Worth asking, because a list of record gaps can be built two ways: by scanning
every integer, or by hunting for large gaps directly. The second method finds
genuine gaps but cannot prove there is no smaller record hiding in the
unsearched space between them, and a list built that way would have holes.

The b-file is the first kind, all the way to the end. Andersen and Luhn's
[Record Prime Gaps](https://www.pzktupel.de/RecordGaps/risinggap.php) table —
the source OEIS links — splits at exactly the b-file's last term:

| rank | gap start | status |
|------|-----------|--------|
| 1–85 | up to 1.014e20 | **confirmed**, each with a named "Verification of the *n*th maximum gap" and a date |
| 86+ | 3.94e25 and up | **unconfirmed** — known large gaps, not proven to be the next record |

OEIS stops the b-file at 85, so it publishes only the confirmed prefix. The
confirmations are recent and were done one rank at a time: 78 in 2018, 81 in
Dec 2023, 82 in May 2024, 83 in Oct 2024, 84 in Jan 2026, 85 in May 2026.

Two consequences. First, no intermediate term is missing below 1.014e20, so
every gap checkpoint this scan can reach is sound — the confirmed frontier
(1.014e20) is already past this program's own arithmetic ceiling (1.84e19).
Second, the b-file grows, which is why `check_oeis.py` warns when its cache is
over a month old and takes `--refresh`. A stale cache would report a published
term as a discovery.

One caution against reading too much into the shape of the data: merit
(`gap / ln p`) sits near 34–35 for ranks 76–82 and then jumps to 37.7, 37.8 and
40.2 for ranks 83–85, and rank 84 is 3.3x rank 83. That looks like the
signature of a hole, but it is not — those three ranks carry verification dates
like the rest. Unusually high-merit gaps are simply rare and clustered.

So **1.7e15 is the meaningful milestone**, not 9.41e14: about a week from the
current frontier, it collects the last three gap checkpoints available for a
very long way, while extending A023186 and A096265 past everything published.
Beyond it the scan runs 26x — call it a year — with no external check at all
until 4.38e16.

At the recent cadence of aloof records (~4 per decade of magnitude) that week
should also yield two or three new A096265 terms and one or two new A023186
terms.

Nothing needs to be passed to the running scan to do this: it is open-ended
already and will simply keep going. Adding `--to` would only make it stop.
