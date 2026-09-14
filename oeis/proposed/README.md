# Proposed OEIS submission

## `b096265.txt` — extend A096265 from 55 terms to 68

Not a discovery. A096265's b-file has 55 terms reaching 9.29e11, while the
same records are published to 67 terms reaching 1.693e15 as
[A031133](https://oeis.org/A031133) (lower neighbour),
[A031134](https://oeis.org/A031134) (upper neighbour) and
[A031132](https://oeis.org/A031132) (span). A096265 already cross-references
A031132 and even notes the index offset — "record distances corresponding to
a(2) onward" — so the information was never hidden, merely never propagated
back into A096265's own b-file. Anyone consulting A096265 alone gets the short
list, which is exactly the mistake this project made.

`A096265(k+1)` is the unique prime strictly between `A031133(k)` and
`A031134(k)`, so terms 56..68 follow from data OEIS has already approved.

### How this file was built and checked

- terms 56–68 derived as the prime between each `A031133`/`A031134` pair;
  each interval verified to contain **exactly one** prime, or the record would
  not be well defined
- `A031134(k) − A031133(k) == A031132(k)` at all 67 terms
- terms 1–55 reproduce the published b096265 exactly
- **all 68 terms reproduce this project's own from-scratch exhaustive scan
  exactly**, which found no aloof(69) below 2*10^15 (frontier
  2,075,805,595,153,846 on 2026-09-14). So the file is an independent
  verification of A031133/A031134, not a transcription of them, and the header
  says so.
- format checked against the [b-file spec](https://oeis.org/wiki/B-files):
  pure ASCII, no BOM, LF endings, final newline, no tabs, `n a(n)` per line,
  indices consecutive from the offset

Before submitting, recheck against the frontier then current and date the
header. The completeness bound in it is rounded down.

### Also worth proposing

`A031133` and `A031134` cross-reference A031131/2/4 and A122412/3 but **not**
A096265, so the link runs only one way. Adding the reverse would make the
duplication findable from either end.

---

# Audit: what else is missing

`python3 oeis_audit.py [--refresh]` walks the four families and reports where
one member is shallower than its siblings. Within a family every sequence
describes the *same* records, so any depth difference is stale bookkeeping that
can be fixed from published data alone.

## b-files

| priority | sequence | state | source for the fix |
|---|---|---|---|
| **1** | A096265 | 55 terms, **12 behind** | done — `b096265.txt` here, confirmed by the scan |
| **2** | A005669 | 82 terms, 3 behind | the "Index via primecount.exe" column of [Andersen–Luhn](https://www.pzktupel.de/RecordGaps/risinggap.php) |
| **3** | A107578 | 80 terms, 5 behind | `A107578(n) = A005669(n) + 1`, verified at all 80 shared terms |
| **4** | A122412 / A122413 | 52 terms, **15 behind** | needs π(p) at p ≈ 1.69e15 — real compute, e.g. `primecount` |
| low | A023187, A031132, A058867, A058868 | no uploaded b-file | DATA already holds every known term; only worth doing once they grow |

A053695 looks short at 84 terms but is a difference sequence, so 84 is complete
against A005250's 85. The audit accounts for that.

## a-files

An a-file is free-form, so it is where the bounding primes belong — the data
that makes each record checkable without rerunning a scan.

| family | state |
|---|---|
| gap | **stale.** Alex Beveridge's [a005250.txt](https://oeis.org/A005250/a005250.txt) has 75 rows against 85 known terms, last updated Oct 2010 |
| lonely | **missing entirely** — all 56 records with both neighbours are in `fresh/lonely.txt` |
| aloof | **missing entirely** — all 68 are in `fresh/aloof.txt` |
| equidistant | **missing entirely** — all 30 are in `fresh/equidistant.txt` |

The gap a-file is the model to copy: columns for the upper prime, the gap and
the prime index, with a header naming the A-number each column belongs to. The
same table for lonely, aloof and equidistant — prime, both neighbours, both
gaps — would let anyone verify a term from the entry alone, and would have made
this project's duplicate-sequence mistake impossible to miss. None of them is
blocked any longer; the scan covers every published term of all three.
