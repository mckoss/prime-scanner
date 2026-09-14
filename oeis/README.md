# OEIS: what the scan has established

The goal of this project is a better OEIS record for the gap, lonely, aloof
and equidistant prime families: independent confirmation of the published
terms, completeness bounds, and the bounding primes that make each record
checkable. This page summarises what the unseeded scan in
[`../fresh/`](../fresh/README.md) has established so far.
[`TODO.md`](TODO.md) is the working checklist, and [`proposed/`](proposed/)
holds the drafts.

## Progress

Snapshot of 2026-09-14, at the committed frontier of
**2,075,805,595,153,846**. Every sequence was scanned from zero with no seed, so
each published term below had to be re-derived to stay aligned. All four
per-sequence frontiers are level.

| family | published | reaches | ours | agreement | bound vs published |
|--------|-----------|---------|------|-----------|--------------------|
| gap, [A002386](https://oeis.org/A002386) | 85 | 1.014e20 | 64 | all 64 below the frontier | — (published is deeper) |
| lonely, [A023186](https://oeis.org/A023186) | 56 | 9.41e14 | 56 | all 56 | **2.2x** |
| aloof, [A031133](https://oeis.org/A031133)/[4](https://oeis.org/A031134)/[2](https://oeis.org/A031132) | 67 (= A096265 index 68) | 1.693e15 | 68 | all 67, on lower, upper and span | **1.2x** |
| aloof, [A096265](https://oeis.org/A096265) | 55 | 9.29e11 | 68 | all 55; its b-file is 13 behind | — |
| equidistant, [A058867](https://oeis.org/A058867) | 30 | 1.879e14 | 30 | all 30 | **11x** |
| balanced-lonely | not in OEIS | — | 5 | all inside A058867, as required | — |

`python3 check_oeis.py fresh` produces the agreement column. It diffs
position by position against the b-files below and re-tests every record
prime with deterministic Miller-Rabin, independent of the sieve.

What that adds up to:

- **Every published term below 2.07e15 is independently confirmed**: 218
  records across four families (64 + 56 + 68 + 30), with no omissions and no
  extras.
- **No new terms.** There is no lonely(57), aloof(69) or 31st A058867 term
  below 2.07e15. The result is the completeness bounds in the last column,
  which no targeted search can supply.
- **The last three gap checkpoints below 4.38e16** are confirmed: gap(62) =
  1189459969825483, gap(63) = 1686994940955803, gap(64) = 1693182318746371.
  The last is also aloof(68): its 1132 gap and the 20 below make a record
  span of 1152.
- **Bounding primes for every record.** Each line in `fresh/` carries both
  neighbours, and that is the data an a-file needs. OEIS has none for
  lonely or equidistant.

Beyond this point the scan gets no outside check until gap(65) at 4.38e16,
about four months away on 8 cores. It keeps running anyway, so every bound
above will rise before submission.

### What is being submitted

Nothing here is a discovery claim. In order (details in [`TODO.md`](TODO.md)):

1. **A096265 b-file**, 55 → 68 terms: [`proposed/b096265.txt`](proposed/b096265.txt).
   Terms 56–68 were already published under A031133/A031134, and all 68 are now
   independently confirmed here.
2. **Reverse cross-reference** from A031133/A031134 to A096265.
3. **New sequence: balanced-lonely primes**:
   [`proposed/balanced-lonely-primes.md`](proposed/balanced-lonely-primes.md).
4. **Search-bound comments** on A023186, A058867 and A031133, stating no
   further terms below the frontier.
5. **a-files** for lonely, aloof and equidistant from `fresh/`, and an update
   of Beveridge's gap a-file (75 rows against 85 terms).
6. b-files for A005669 and A107578 from Andersen–Luhn, and for A122412/3
   (needs π(p)).

## Compute cost

About **850 core-hours**, or roughly 4½ days of 8 performance cores on an
Apple M1 Max, not counting pauses and restarts. Per-round worker logs are
deleted each round, so the figure is reconstructed from wall-clock times
recorded in commits and the measured rate curve in `pgaps.py`:

| stage | range | basis | core-hours |
|-------|-------|-------|-----------:|
| all three original sequences | 0 → 3.86e14 | ~20 h wall × 8, snapshot of 2026-09-09 | 160 |
| same, still on the pre-speedup binary | 3.86e14 → 5.67e14 | rate curve × 1.74, the slowdown the row above shows | 83 |
| A058867 catch-up | 0 → 2.61e14 | 7.2 h wall × 8, between two commits | 57 |
| A058867 catch-up | 2.61e14 → 5.67e14 | rate curve | 80 |
| all four sequences | 5.67e14 → 2.07e15 | rate curve | 446 |
| **total** | | | **≈ 830** |

The last two rows ran under a single driver for 80.5 hours of wall time. With
all 8 cores busy the whole time that would be 644 core-hours, against 526
modelled, so the true total lies between about 830 and 950. The A058867
catch-up cost ~140 of those only because the sequence was added after the
scan had started. From scratch on today's binary, the whole scan to 2.07e15
would take ~590 core-hours, 73 hours on 8 workers.

---

## The cached b-files

The published data `check_oeis.py` compares against is committed rather than
ignored, for three reasons:

- **The check runs offline.** No network, no outage, no rate limit.
- **The comparison is auditable.** "No new terms" means something only
  against a specific snapshot of what was published.
- **Updates become visible.** A002386 went from 77 to 85 terms as ranks 78–85
  were confirmed between 2018 and 2026. Because the files are tracked, a
  refresh shows up as a diff.

| file | sequence | records | terms | extent |
|------|----------|---------|-------|--------|
| `gap.txt` | [A002386](https://oeis.org/A002386) | primes at the lower end of a record gap | 85 | 1.014e20 |
| `lonely.txt` | [A023186](https://oeis.org/A023186) | record of min(gap below, gap above) | 56 | 9.41e14 |
| `aloof.txt` | [A096265](https://oeis.org/A096265) | record of nextprime(p) − prevprime(p) | 55 | 9.29e11 |
| `aloof-lower.txt` | [A031133](https://oeis.org/A031133) | lower neighbour of the same records | 67 | 1.693e15 |
| `aloof-upper.txt` | [A031134](https://oeis.org/A031134) | upper neighbour of the same records | 67 | 1.693e15 |
| `aloof-span.txt` | [A031132](https://oeis.org/A031132) | span between them | 67 | 1152 |
| `equidistant.txt` | [A058867](https://oeis.org/A058867) | record distance among *balanced* primes only | 30 | 1.879e14 |

Each file is named for the file in `fresh/` it is checked against, and this
table maps it to its A-number (upstream, `gap.txt` is `b002386.txt`). The three
`aloof-*` files are the aloof records published a second time and indexed one
lower: A096265 carries an extra a(1) = 2 with no lower neighbour, so family
term k is A096265 term k+1. Checking A096265 alone once made published records
look like discoveries, so the check reads the family.

`audit/` holds `oeis_audit.py`'s working copies of the wider set of entries it
inspects, and is not committed.

To update, with or without checking a run:

```
python3 check_oeis.py --refresh             # just update these files
python3 check_oeis.py fresh --refresh       # update, then check a run
```

It reports what moved and names any new terms, since a newly published term
is one the scan can no longer claim:

```
  = A002386: unchanged, 85 terms
  * A096265: UPDATED, 52 -> 55 terms
      + aloof(53) = 220578150113
```

A failed refetch keeps the good copy. Without `--refresh`, a cache older than
30 days draws a warning but is still used.

## Attribution

From [The On-Line Encyclopedia of Integer Sequences](https://oeis.org/),
licensed CC BY-SA 4.0 under [the OEIS End-User License
Agreement](https://oeis.org/wiki/The_OEIS_End-User_License_Agreement). The
files are renamed as above but their contents are unmodified. Individual
b-file contributors are named in each sequence's OEIS entry.
