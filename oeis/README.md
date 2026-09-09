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

| file | sequence | terms | extent |
|------|----------|-------|--------|
| `b002386.txt` | [A002386](https://oeis.org/A002386) — record gaps, lower end | 85 | 1.014e20 |
| `b023186.txt` | [A023186](https://oeis.org/A023186) — lonely primes | 56 | 9.41e14 |
| `b096265.txt` | [A096265](https://oeis.org/A096265) — aloof primes | 55 | 9.29e11 |

A b-file is the full published data and is longer than the DATA section shown
on the sequence page, which is why these are what the check reads.

To update: `python3 check_oeis.py <results> --refresh`. It refetches all three
and reports what moved, naming any new terms:

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
files are unmodified. Individual b-file contributors are named in each
sequence's OEIS entry.
