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
6. **A087770 extension.** Tracking was added on 2026-09-14 as `pairwise`, and
   the sequence has 29 terms, stale since 2003. Our lonely(51) already proves
   a(30) ≤ 26923643849953, so new terms are expected once the scan covers it.
7. b-files for A005669 and A107578 from Andersen–Luhn, and for A122412/3
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

## Related OEIS sequences

Every sequence this project covers, and every related sequence it has looked
at and decided not to. `python3 oeis_audit.py` finds the related ones: it
follows cross-references both ways from the covered sequences, and keeps
those sharing at least 3 terms above 1000 with our records.

Columns: **a-file** — the entry has its own a-file; **b-file** — terms in its
uploaded b-file, or `DATA n` when none is uploaded; **here** — terms `fresh/`
holds at the 2026-09-14 checkpoint.

### Covered

| sequence | name here | what it holds | a-file | b-file | here |
|----------|-----------|---------------|:------:|-------:|-----:|
| [A002386](https://oeis.org/A002386) | **gap** | lower prime of a record gap | — | 85 | 64 |
| [A000101](https://oeis.org/A000101) | gap | upper prime of a record gap | yes | 85 | 64 |
| [A005250](https://oeis.org/A005250) | gap | the record gap size | yes | 85 | 64 |
| [A053695](https://oeis.org/A053695) | gap | differences between record gaps | — | 84 | 63 |
| [A023186](https://oeis.org/A023186) | **lonely** | record min(gap below, gap above) | — | 56 | 56 |
| [A023187](https://oeis.org/A023187) | lonely | that distance | — | DATA 56 | 56 |
| [A096265](https://oeis.org/A096265) | **aloof** | record nextprime(p) − prevprime(p) | — | 55 | 68 |
| [A031133](https://oeis.org/A031133) | aloof | lower neighbour, indexed one lower | — | 67 | 67 |
| [A031134](https://oeis.org/A031134) | aloof | upper neighbour, indexed one lower | — | 67 | 67 |
| [A031132](https://oeis.org/A031132) | aloof | the span | — | DATA 67 | 67 |
| [A058867](https://oeis.org/A058867) | **equidistant** | record distance among balanced primes only | — | DATA 30 | 30 |
| [A058868](https://oeis.org/A058868) | equidistant | that distance | — | DATA 30 | 30 |
| [A087770](https://oeis.org/A087770) | **pairwise** | both gaps beat the previous term's | — | DATA 29 | catch-up pending |
| not in OEIS | **balanced** | lonely records that are balanced primes | — | — | 5 |

### In a covered family, but not computable here

These need π(p), the prime's index, which a scan does not count. `primecount`
can supply it.

| sequence | family | what it holds | a-file | b-file |
|----------|--------|---------------|:------:|-------:|
| [A005669](https://oeis.org/A005669) | gap | index of the lower prime | — | 82 |
| [A107578](https://oeis.org/A107578) | gap | index of the upper prime | yes | 80 |
| [A122412](https://oeis.org/A122412) | aloof | index of the lower neighbour | — | 52 |
| [A122413](https://oeis.org/A122413) | aloof | index of the upper neighbour | — | 52 |

### Open: worth tracking, not yet tracked

| sequence | what it holds | a-file | b-file | why it matters |
|----------|---------------|:------:|-------:|----------------|
| [A120384](https://oeis.org/A120384) | record geometric mean of the two gaps | — | 54 | a running maximum like lonely and aloof, and its b-file stops at 3.16e10; not yet examined in depth |

### Not tracked: not record sequences

A scan can only improve an entry whose terms are records it visits in order.
First-occurrence tables list the least prime for each value of some quantity,
so they have holes wherever that value has not been seen yet. Their terms
come out of the same scan, but not as a complete prefix.

| sequence | what it holds | a-file | b-file | why not |
|----------|---------------|:------:|-------:|---------|
| [A102723](https://oeis.org/A102723) | least prime with every integer within n composite | — | 479 | first occurrences; its b-file ends at lonely(56), so lonely(57) would extend it too |
| [A023188](https://oeis.org/A023188) | least prime at each nearest-prime distance | — | 191 | first occurrences |
| [A120937](https://oeis.org/A120937) | least prime with both gaps ≥ 2n | — | DATA 35 | first occurrences |
| [A054342](https://oeis.org/A054342) | first balanced prime at each distance | — | 53 | first occurrences |
| [A046931](https://oeis.org/A046931) | least prime whose neighbours are exactly 2n apart | — | 312 | first occurrences |
| [A000230](https://oeis.org/A000230) | least prime starting a gap of exactly 2n | — | 721 | first occurrences |
| [A001632](https://oeis.org/A001632) | least prime ending a gap of exactly 2n | — | 595 | first occurrences |
| [A100964](https://oeis.org/A100964) | least prime starting a gap ≥ 2n | — | 775 | the gap records re-indexed by size |
| [A111870](https://oeis.org/A111870) | record merit, gap / log p | — | 39 | a subset of A002386 |
| [A111943](https://oeis.org/A111943) | record gap / log² p | — | DATA 12 | a subset of A002386 |
| [A051650](https://oeis.org/A051650) | lonely *numbers*: record distance to the nearest prime | — | 211 | over all integers, not primes |
| [A051652](https://oeis.org/A051652) | least number at each distance from a prime | yes | 228 | over all integers |
| [A051728](https://oeis.org/A051728) | least number at distance 2n from a prime | — | DATA 38 | over all integers |
| [A051729](https://oeis.org/A051729) | least number at distance 2n+1 from a prime | — | DATA 37 | over all integers |
| [A051730](https://oeis.org/A051730) | distance from A051650(n) to its nearest prime | — | 211 | over all integers |
| [A182315](https://oeis.org/A182315) | primes whose next gap exceeds log² n | — | DATA 18 | a threshold set, not records; its terms come from A002386 |
| [A124147](https://oeis.org/A124147) | primes with p < √g·e^√g | — | DATA 13 | a threshold set; all but 5 and 13 are in A002386 |

### Not tracked: dense

A record sequence grows roughly geometrically, so a scan to 2e15 yields tens of
terms. A dense sequence yields millions, and nobody uploads a b-file that size.
The audit calls a sequence dense when its b-file holds more than 1000 terms
and the terms add under 0.005 digits each.

| sequence | what it holds | a-file | b-file | why not |
|----------|---------------|:------:|-------:|---------|
| [A211073](https://oeis.org/A211073) | every prime followed by a gap ≥ log²(p)/2 | — | 10000 | dense: 10000 terms reach only 1.1e12 |
| [A079296](https://oeis.org/A079296) | all primes, ordered by √q − √p | — | 10000 | dense: it is every prime, reordered |
| [A391411](https://oeis.org/A391411) | first prime of each new pattern of two consecutive gaps | yes | 7500 | dense: 7500 terms reach only 4.2e9 |

### Not yet reviewed

The audit also surfaces these, each sharing at least 3 large terms with our
records. None has been judged yet. A330428 looks likeliest to matter: its last
term is our lonely(51).

A002540, A053302, A058193, A060771, A073861, A075051, A075741, A084105,
A103709, A104138, A123995, A123996, A134266, A138198, A167236, A205827,
A209407, A214757, A224522, A241886, A243593, A268140, A309877, A330428,
A335366, A335367, A350095, A350096.

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
| `pairwise.txt` | [A087770](https://oeis.org/A087770) | both gaps beat the previous term's (a chain) | 29 | 9.16e12 |

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
