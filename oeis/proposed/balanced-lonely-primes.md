# Proposed new sequence: balanced lonely primes

Suggested by Michel Marcus in review of a comment on
[A023186](https://oeis.org/A023186): submit the intersection as its own
sequence rather than as a comment there.

Not currently in OEIS — a search for `5, 53, 211, 26923643849953` returns
nothing. The near miss is [A058867](https://oeis.org/A058867), which is a
different sequence and contains this one; the Comments below say how, because
an editor will otherwise ask.

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

    Not to be confused with A058867, which is a supersequence of this one.
    A058867 takes its record within the balanced primes alone, so a balanced
    prime enters it by beating every earlier balanced prime; a term here must
    beat every earlier prime, balanced or not. A058867(4) = 16787 shows the
    difference: its gaps are (24, 24), but A023186 had already reached 24 at
    the prime 16033, whose gaps are (26, 24), so 16787 sets no record over all
    primes. This sequence is the 5 terms of A058867 that are in A023186.

    There are no further terms below 2*10^15. An exhaustive scan from zero
    rederived every term of A023186 and of A058867 below that bound, and found
    no others, so the sequence is complete there. - Mike Koss, <date>

**Example**

    5              has neighbors (3, 7),                             both at distance 2.
    53             has neighbors (47, 59),                           both at distance 6.
    211            has neighbors (199, 223),                         both at distance 12.
    26923643849953 has neighbors (26923643849563, 26923643850343),   both at distance 390.
    187891466722913 has neighbors (187891466722493, 187891466723333), both at distance 420.

**Cross-references**  `Cf. A006562, A023186, A023187, A054342, A058867, A096265.`

**Keywords**  `nonn,more`

`more` because the sequence is certainly incomplete above the search bound.
No b-file: five terms fit in DATA.

## Notes for the submission

- The completeness bound is the strongest line in the entry, and it is the one
  thing a targeted search cannot supply. State the bound, not just the terms.
- Say nothing about whether the sequence is infinite. Five terms and no theory
  support no statement in either direction, and "it appears that..." is still a
  claim. Erdős and Surányi proved there are infinitely many lonely primes
  (noted in A023186), but that says nothing about the ones that are balanced.
  If an editor asks, the answer is that it is unknown.
- Offer to reduce the A023186 comment to `Cf.` this sequence once it is
  allocated, so the list is not maintained in two places.
- The bound rises as the scan advances; use the frontier at submission time,
  rounded **down**. At 2026-09-14 `fresh/frontier.txt` stood at
  2,075,805,595,153,846, stated above as 2*10^15. Rounding to 2.1*10^15
  would claim ground the scan has not covered.

## Verification

Every term checked against this project's own exhaustive scan: `p - prev`,
`next - p`, equality of the two gaps, and each of `prev`, `p`, `next` prime by
deterministic Miller-Rabin.

The scan it filters is itself checked: at the 2026-09-14 frontier,
`check_oeis.py fresh` matches all 56 terms of A023186 and all 30 of A058867
position by position. It also confirms that all 5 terms here appear in
A058867, as they must.

A trap worth recording: `fresh/lonely.txt` stores A023186(1) = 2 as
`below=1, above=1, prev=0`, so a naive `below == above` filter returns 2 as
balanced. It is not — 2 has no lower neighbor, and A006562 begins 5, 53, 157.
