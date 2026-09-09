# Proposed new sequence: balanced lonely primes

Suggested by Michel Marcus in review of a comment on
[A023186](https://oeis.org/A023186): submit the intersection as its own
sequence rather than as a comment there.

Not currently in OEIS — a search for `5, 53, 211, 26923643849953` returns
nothing.

## Draft entry

**Name**

    Balanced lonely primes: terms of A023186 that are also balanced primes
    (A006562), i.e. record-setting isolated primes exactly equidistant from
    their two nearest prime neighbors.

**Data**

    5, 53, 211, 26923643849953, 187891466722913

**Offset**  `1,1`

**Comments**

    A prime p qualifies if it sets a new record for the distance to its
    nearest neighboring prime (A023186) and is the average of the previous
    and following prime (A006562), so the gaps on both sides are equal.

    A023186(1) = 2 is excluded: it has no lower neighbor, so it is not a
    balanced prime.

    There are no further terms below 4.06e14. The terms of A023186 were
    rederived from zero by an exhaustive scan, so the sequence is complete
    below that bound. - Mike Koss, <date>

    It appears that there are infinitely many terms, but this is not known.

**Example**

    5              has neighbors (3, 7),                             both at distance 2.
    53             has neighbors (47, 59),                           both at distance 6.
    211            has neighbors (199, 223),                         both at distance 12.
    26923643849953 has neighbors (26923643849563, 26923643850343),   both at distance 390.
    187891466722913 has neighbors (187891466722493, 187891466723333), both at distance 420.

**Cross-references**  `Cf. A023186, A023187, A006562, A096265.`

**Keywords**  `nonn,more`

`more` because the sequence is certainly incomplete above the search bound.
No b-file: five terms fit in DATA.

## Notes for the submission

- The completeness bound is the strongest line in the entry, and it is the one
  thing a targeted search cannot supply. State the bound, not just the terms.
- State infinitude as an appearance, never a claim — OEIS is strict about
  guess vs. theorem.
- Offer to reduce the A023186 comment to `Cf.` this sequence once it is
  allocated, so the list is not maintained in two places.
- The bound rises as the scan advances; use the frontier at submission time.

## Verification

Every term checked against this project's own exhaustive scan: `p - prev`,
`next - p`, equality of the two gaps, and each of `prev`, `p`, `next` prime by
deterministic Miller-Rabin.

A trap worth recording: `fresh/lonely.txt` stores A023186(1) = 2 as
`below=1, above=1, prev=0`, so a naive `below == above` filter returns 2 as
balanced. It is not — 2 has no lower neighbor, and A006562 begins 5, 53, 157.
