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
- terms 1–63 reproduce this project's own from-scratch exhaustive scan exactly
- format checked against the [b-file spec](https://oeis.org/wiki/B-files):
  pure ASCII, no BOM, LF endings, final newline, no tabs, `n a(n)` per line,
  indices consecutive from the offset

### Still worth doing before submitting

This scan reaches 1.693e15 in roughly a week. At that point terms 64–68 are
independently confirmed here rather than taken from A031133/A031134, which
makes the submission an independent verification instead of a transcription.

### Also worth proposing

`A031133` and `A031134` cross-reference A031131/2/4 and A122412/3 but **not**
A096265, so the link runs only one way. Adding the reverse would make the
duplication findable from either end.
