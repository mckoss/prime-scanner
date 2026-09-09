# Search results — from scratch, in parallel

Live output of `pgaps.py`, the parallel driver, run open-ended across 8 workers:

```
python3 pgaps.py --jobs 8 --out fresh
```

Unlike [`results/`](../results/README.md), this search was **not seeded**. It
started at 0 with every threshold at zero and re-derived all four sequences
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
| `equidistant.txt` | record distance among the *balanced* primes alone — [A058867](https://oeis.org/A058867) |
| `balanced.txt` | the subset of `lonely.txt` whose two gaps are equal — not yet in OEIS, see [`../oeis/TODO.md`](../oeis/TODO.md) |
| `frontier.txt` | the point below which **every** sequence here is complete — see below |
| `coverage.txt` | how far each sequence is scanned, which is not always the same point — see below |

Each results line is

```
<n> <prime> <value> <gap_below> <gap_above> <prev_prime> <next_prime>
```

The first two columns are an OEIS b-file. The last two make every line
self-contained proof: check that `prev`, `prime` and `next` are all prime and
that nothing lies between them, and the record stands without rerunning the
scan. `value` is whichever quantity that sequence maximises — `gap_above` for
gaps, `min(below, above)` for lonely, `below + above` for aloof.

`equidistant.txt` maximises the same quantity as `lonely.txt` but over a
different population: only the primes whose two gaps are equal, ranked against
each other. That makes it neither a filter of the lonely records nor derivable
from them — `A058867(4) = 16787` enters on a distance of 24 that `lonely(9) =
16033` had already reached with gaps (26, 24). It is a fourth running maximum
in the sieve, not a view of the third.

`balanced.txt` is the odd one out: it maximises nothing. It is `lonely.txt`
filtered to `gap_below == gap_above` (and `prev != 0`, since p = 2 has no
lower neighbour), so `value` is simply that common distance. A balanced lonely
prime is a lonely record by definition, so the filter cannot miss one —
`lonely.txt` already holds every term there can be below the frontier, which
is why the workers collect nothing for it and it needs no threshold.

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
are truncated to it, and the next round starts there.

### Why there is a second file

Adding a sequence to a run that has already scanned a long way puts that one
sequence at zero while the rest are at the frontier, so for a while a single
number cannot describe the run. `coverage.txt` records how far each is
actually scanned, and `pgaps.py` notices the gap on its own and runs
**catch-up rounds** for the lagging sequence over the range the others have
already covered — merging only that sequence, leaving the finished files
untouched. `pgaps.py --out fresh --status` shows where each one stands.

The two files are not redundant, and which is which matters:

- `coverage.txt` is per sequence, and it is where the run **resumes** from —
  the furthest any sequence has reached.
- `frontier.txt` is the **minimum** across them: the point below which every
  sequence here is complete. While a catch-up is pending it reads low, on
  purpose. Understating the bound costs nothing; overstating it would put a
  false completeness claim into an OEIS submission, which is the one thing
  this scan must never do.

Once a catch-up finishes the two agree again and stay agreed, because every
round after it scans all four sequences together. Disjoint frontiers are a
migration state, not a steady one.

## What is committed, and what is not

Committed: the four merged record files, `balanced.txt` derived from them,
and `frontier.txt` with `coverage.txt`. Together they are the complete,
resumable state of the search — drop them into an empty directory, rerun the
same command, and it picks up where it left off.

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
| aloof A096265 | 55 | 55 | 63 | all published — see below |

The middle column is the honest denominator: a term above the frontier is not
a miss, it is simply not reached yet.

**A096265's b-file is not the deepest source for aloof records**, so that last
row understates the published data badly. See "Aloof is not new ground" below.

### Aloof is not new ground

The eight aloof terms past A096265 are **not discoveries**. The same records
are published far deeper as a three-sequence family:

| sequence | holds |
|----------|-------|
| [A031133](https://oeis.org/A031133) | the lower neighbour |
| [A031134](https://oeis.org/A031134) | the upper neighbour |
| [A031132](https://oeis.org/A031132) | the span between them |

`prime(n+2) − prime(n)` is exactly `nextprime(p) − prevprime(p)` for the middle
prime, so these are the same records under a different name. They are indexed
one lower than A096265, which carries an extra a(1) = 2 having no lower
neighbour: **family term k is A096265 term k+1**.

Their b-files hold **67 terms, equivalent to A096265 index 68, reaching
1.693e15** — while A096265's own b-file stopped at 55. Checked against the
family, all 63 aloof records this scan has produced agree on lower neighbour,
upper neighbour and span, and the family is **5 terms ahead**, its next at
471,911,699,385,743.

So the scan has reproduced published aloof data, not extended it. That is a
real result — 63 terms rederived from zero, agreeing exactly — but it is
verification, not discovery, and the earlier claim of eight new terms was
wrong. `check_oeis.py` now compares against the family, so this cannot recur.

The genuine aloof frontier is 1.693e15, about 6.7 days from here — which is
also where the gap checkpoints run out. That one point is now the milestone for
both.

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
| A096265 aloof | still **validation** until 1.693e15 — the A031133/4/2 family is published that far, 5 terms ahead of this scan |
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

### Why opportunistic gap-hunting will not extend these sequences

The obvious shortcut is to skip ahead to a published record and hope a lucky
gap sits nearby. It does not work here, for three separate reasons.

*It is out of range.* The confirmed gap frontier, gap(85) = 1.014e20, is 5.5x
above this program's 1.84e19 ceiling — as are gap(81) through gap(84). The only
published maximal gap below the ceiling is gap(80) = 1.836e19, and everything
between it and gap(85) is already confirmed, so there is nothing there to find.

*It is a different program.* Searches at that height do not sieve. They
construct an interval where small primes divide everything, then PRP-test the
ends — the top of the Andersen–Luhn table is
`1217 • 888887# / 23# − 7636494`, a 385,713-digit number with a gap of
16,045,848. That needs bignum arithmetic and a completely different method.

*Its results would not be terms.* These are **record** sequences: term n is
defined by exceeding every earlier one, which you can only know by having seen
everything below. A lucky gap found at 1e25 has no index. That is exactly why
the Andersen–Luhn table has an unconfirmed section from rank 86 on, and why
OEIS publishes only the confirmed prefix.

The asymmetry is the real point. Exhaustive coverage stands at 1.014e20 for
gaps, 1.693e15 for aloof (via A031133/4/2, not A096265) and 9.41e14 for lonely.
The open ground is not above 2^64 — but it is nearer 1e15 than 1e12, and
lonely reaches it first.

### Opportunism that does work: gaps predict aloof records

Within range, the published gap list is useful in the other direction. A
maximal gap forces an aloof value at both of its endpoints, so A002386 says in
advance what this scan will find:

| at | prime | below | above | aloof | lonely |
|----|-------|-------|-------|-------|--------|
| gap(62) upper | 1,189,459,969,826,399 | 916 | 42 | **958** | 42 |
| gap(63) lower | 1,686,994,940,955,803 | 70 | 924 | **994** | 70 |
| gap(63) upper | 1,686,994,940,956,727 | 924 | 56 | **980** | 56 |
| gap(64) both ends | 1,693,182,318,746,371 and …747,503 | 20/1132 | 1132/20 | **1152** | 20 |

Against a current aloof record of 944, every one of those is a new record, so
the aloof value is guaranteed to be at least 958 by 1.19e15 and at least 1152
by 1.69e15. They are lower bounds, not predictions of the term itself — some
prime in between may do better — but they are checkpoints that cost nothing.

Note the last column. None of these threatens the lonely record of 432, and
that is structural: a maximal gap is lopsided (2/916, 70/924, 20/1132) and
lonely takes the *smaller* side. The gap list is silent about lonely records,
which is why lonely(n) has to be earned by scanning.

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
