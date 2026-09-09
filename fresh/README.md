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
a(56) =   1032148488557   span 678
a(57) =   3605572653889   span 690
a(58) =   4079970755417   span 700
a(59) =   5061226833937   span 760
a(60) =  12772332382939   span 780
a(61) =  19535748743177   span 838
a(62) =  21185697626267   span 900
a(63) = 117102787055963   span 944
```

A096265 was published to a(55) = 929,156,727,137. `a(56)` was also found by the
earlier single-threaded run in `results/`, which had been *seeded* with the 55
published terms; this run rediscovered it having been told nothing, which is
the stronger of the two claims.

None of these have been submitted to OEIS or confirmed by a second
implementation.

## What is left to check against

[A023186](https://oeis.org/A023186/b023186.txt) is the deepest published
sequence an exhaustive scan can actually consume — its b-file runs to
a(56) = 941,114,429,467,073 (9.41e14), about 2.4x the current frontier. Two of
its terms still lie ahead:

```
a(55) = 475963705368391   (4.76e14)
a(56) = 941114429467073   (9.41e14)
```

A002386 has 85 published terms, but only 61 of them fall below 9.41e14 and
this run already holds all 61 — the next maximal gap is
a(62) = 1,189,459,969,825,483, past that limit. Its remaining terms reach 1e20
and come from targeted gap searches rather than exhaustive scans, so they are
not something a scan like this reaches.

So for the rest of the run the published data offers exactly two more checks,
both from A023186, and everything found in A096265 along the way is new. That
makes 941,114,429,467,074 the natural stopping point, which is the target the
[top-level README](../README.md#11-reproducing-the-published-sequences-from-scratch)
uses:

```
python3 pgaps.py --to 941114429467074 --jobs 8 --out fresh
```

Passing `--to` to the running open-ended scan is not necessary to get there —
it is the same walk — but it makes the run terminate at the limit instead of
scanning on past the last thing there is to compare against.
