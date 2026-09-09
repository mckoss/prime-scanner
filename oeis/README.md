# OEIS b-files

The published data `check_oeis.py` compares against, committed rather than
ignored. Three reasons:

- **The check runs offline.** No network, no OEIS outage, no rate limit.
- **The comparison is auditable.** "8 terms beyond the published sequence" only
  means something relative to a specific snapshot of what was published. These
  files are that snapshot.
- **Updates become visible.** These sequences grow — A002386 went from 77 terms
  to 85 as ranks 78–85 were confirmed between 2018 and 2026. Tracked, a
  `check_oeis.py --refresh` shows up as a diff instead of silently changing
  what "new" means.

The last three are the aloof records published a second time, under different
A-numbers and indexed one lower (A096265 carries an extra a(1) = 2 with no
lower neighbour, so family term k is A096265 term k+1). They run to 1.693e15
where A096265's own b-file stops at 9.29e11 — checking only A096265 makes
long-published records look like discoveries, which is exactly what happened.

| file | sequence | records | terms | extent |
|------|----------|---------|-------|--------|
| `gap.txt` | [A002386](https://oeis.org/A002386) | primes at the lower end of a record gap | 85 | 1.014e20 |
| `lonely.txt` | [A023186](https://oeis.org/A023186) | record of min(gap below, gap above) | 56 | 9.41e14 |
| `aloof.txt` | [A096265](https://oeis.org/A096265) | record of nextprime(p) − prevprime(p) | 55 | 9.29e11 |
| `aloof-lower.txt` | [A031133](https://oeis.org/A031133) | lower neighbour of the same records | 67 | 1.693e15 |
| `aloof-upper.txt` | [A031134](https://oeis.org/A031134) | upper neighbour of the same records | 67 | 1.693e15 |
| `aloof-span.txt` | [A031132](https://oeis.org/A031132) | span between them | 67 | 1152 |
| `equidistant.txt` | [A058867](https://oeis.org/A058867) | record distance among *balanced* primes only | 30 | 1.879e14 |

`equidistant.txt` is the published counterpart of `fresh/equidistant.txt`,
which the sieve derives from zero like the others. It is also what
`balanced.txt` is checked against: every balanced-lonely term must appear in
it, because a prime that beats all primes on `min(gap)` beats the balanced
ones in particular. See [`TODO.md`](TODO.md) for why the two are not the same
sequence — the distinction is easy to miss and expensive to miss.

Each is named for the record it holds, matching the file it is checked
against — `oeis/gap.txt` is the published counterpart of `fresh/gap.txt`. The
A-number lives here rather than in the filename, so this table is the mapping;
upstream these are `b002386.txt`, `b023186.txt` and `b096265.txt`.

A b-file is the full published data and is longer than the DATA section shown
on the sequence page, which is why these are what the check reads.

To update, with or without checking a run:

```
python3 check_oeis.py --refresh             # just update these files
python3 check_oeis.py fresh --refresh       # update, then check a run
```

It refetches all three and reports what moved, naming any new terms:

```
  = A002386: unchanged, 85 terms
  * A096265: UPDATED, 52 -> 55 terms
      + aloof(53) = 220578150113
```

A term appearing there is one this scan can no longer claim as new, which is
why they are named rather than counted. A failed refetch keeps the good copy.
Without `--refresh`, a cached file more than 30 days old draws a warning but is
still used.

## Attribution

From The [Online Encyclopedia of Integer Sequences](https://oeis.org/),
licensed CC BY-SA 4.0 under [the OEIS End-User License
Agreement](https://oeis.org/wiki/The_OEIS_End-User_License_Agreement). The
files are renamed as above but their contents are unmodified. Individual
b-file contributors are named in each sequence's OEIS entry.
