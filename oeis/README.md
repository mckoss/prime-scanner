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

They are small: 2.7 KB for all three.

| file | sequence | records | terms | extent |
|------|----------|---------|-------|--------|
| `gap.txt` | [A002386](https://oeis.org/A002386) | primes at the lower end of a record gap | 85 | 1.014e20 |
| `lonely.txt` | [A023186](https://oeis.org/A023186) | record of min(gap below, gap above) | 56 | 9.41e14 |
| `aloof.txt` | [A096265](https://oeis.org/A096265) | record of nextprime(p) − prevprime(p) | 55 | 9.29e11 |

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
