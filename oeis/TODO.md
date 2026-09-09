# OEIS to-do

Goal: improve the published record for the gap / lonely / aloof families. Not
to find unpublished values — those come as a by-product, and the exhaustive
scan's real currency is **completeness bounds**, which targeted searches cannot
supply.

Two tools, different jobs — neither replaces the other:

    ./check_oeis.py fresh          # is the SCAN right? term-by-term diff vs
                                   # published, plus Miller-Rabin on every record
    ./oeis_audit.py --results fresh  # is OEIS complete? which family members lag
                                   # their siblings, which lack a-files, and where
                                   # the frontier stands against each family

Add `--refresh` to either to refetch from OEIS.

## Plan: bake one week, then submit

Started 2026-09-09 at frontier 4.09e14. At the measured 8-worker rate:

| date | frontier | what it unlocks |
|------|----------|-----------------|
| ~Sep 11 | 9.41e14 | past **lonely(56)**, A023186's last published term — genuinely new lonely records from here |
| ~Sep 12 | 1.19e15 | **gap(62)** checkpoint |
| ~Sep 15 | 1.69e15 | **gap(63)**, **gap(64)**, and past the A031133/4 aloof family — genuinely new aloof records from here |
| ~Sep 16 | ~1.77e15 | submit |

Waiting the week is worth it: every completeness bound below gets ~4x stronger,
and the aloof terms stop being transcribed from A031133/A031134 and become
independently confirmed here.

Do **not** pass `--to` to the running scan; it is open-ended and should stay so.

---

## A. New sequence — balanced lonely primes

Draft: [`proposed/balanced-lonely-primes.md`](proposed/balanced-lonely-primes.md)
Terms: `<run>/balanced.txt`, filtered out of `lonely.txt` at every merge.

- [ ] refresh the completeness bound to the frontier at submission time
- [x] **distinguish it from A058867 in the Comments** — see below; an editor
      will ask, and the entry should answer before they do
- [x] add `A058867` and `A054342` to the cross-references
- [ ] submit; say nothing about whether the sequence is infinite
- [ ] offer to reduce the A023186 comment to `Cf.` the new A-number

Suggested by Michel Marcus in review. Not currently in OEIS.

### It is not A058867, and the difference is subtle

[A058867](https://oeis.org/A058867) is "equidistant lonely primes", whose
distances "are maximal: each distance is larger than all such previous
distances". **Such** is doing the work: the record is taken *within the
equidistant primes*, not against all primes. Ours is the intersection of
A023186 with A006562 — a record against **every** prime that also happens to
be balanced. That is strictly stronger, so ours is a subsequence of A058867:
5 of its 30 terms, namely its first three and its last two.

The cleanest example is its 4th term, 16787:

| prime | gaps (below, above) | min | in A058867 | in A023186 |
|-------|--------------------|-----|------------|------------|
| 16033 | (26, 24) | 24 | no — not balanced | **yes**, sets the record at 24 |
| 16787 | (24, 24) | 24 | **yes** — first balanced prime to reach 24 | no — 24 ties, and a record must be strictly larger |

So A058867 admits 16787 on a distance that A023186 had already reached with a
lopsided prime. 22546768250359 (its 28th term) is the same story at 348,
against `lonely(49) = 16303344721399` with gaps (348, 378).

### A058867 itself is extendable, but not from what we scan

Its 30 terms stop at 1.879e14, and this scan is already past that. But its
records are maxima *within the balanced primes*, and `sieve.c` keeps running
maxima only for the gap, lonely and aloof records — so no filter over
`lonely.txt` can produce them. Extending it means a fourth running maximum in
the sieve and a rescan from zero (~2.5 days at the measured rate).

Not started, and not obviously worth it: decide before the submission goes in,
because if it is done, A058867 and the new sequence should be submitted
together.

## B. b-files — stale within their own family

Each is fixable from already-published data; none is a discovery claim.

| # | sequence | state | source | status |
|---|----------|-------|--------|--------|
| 1 | **A096265** | 55 terms, 12 behind its siblings | A031133/A031134 | **file ready**: [`proposed/b096265.txt`](proposed/b096265.txt) — after Sep 15, terms 64–68 are confirmed here rather than transcribed |
| 2 | **A005669** | 82 terms, 3 behind | "Index via primecount.exe" column of [Andersen–Luhn](https://www.pzktupel.de/RecordGaps/risinggap.php) | not started |
| 3 | **A107578** | 80 terms, 5 behind | `A107578(n) = A005669(n) + 1`, verified at all 80 shared terms | not started |
| 4 | A122412 / A122413 | 52 terms, 15 behind | needs π(p) at p ≈ 1.69e15 — real compute (`primecount`) | not started |
| — | A023187, A031132 | no uploaded b-file | DATA already holds every known term | low priority |

A053695 looks 1 short but is a difference sequence; 84 against A005250's 85 is
complete.

## C. a-files — the bounding primes

The gap in the record you cared about: a b-file is `n a(n)` only, so the
neighbours that make a term checkable are published nowhere. An a-file is
free-form and is where they belong.

| family | state | action |
|--------|-------|--------|
| gap | **stale** — Beveridge's [a005250.txt](https://oeis.org/A005250/a005250.txt) has 75 rows against 85 terms, last updated Oct 2010 | extend to 85 |
| aloof | **missing** | build from A031133/A031134/A031132 — can be done today, no scan needed |
| lonely | **missing** | build from this scan: prime, both neighbours, both gaps |

Beveridge's file is the format to copy: one column per contributing sequence,
with a header naming the A-number each column belongs to. Not our 7-column
layout — theirs is the established convention.

## D. Cross-references

- [ ] A031133 and A031134 cite A031131/2/4 and A122412/3 but **not** A096265,
      so the aloof duplication is findable in only one direction. Propose the
      reverse link.

---

## Notes

- OEIS is CC BY-SA 4.0; the b-files in `oeis/` are committed with attribution.
- Submissions go through draft → proposed → editor review (pink boxes) →
  approval. Days to weeks.
- Terms are written `gap(n)`, `lonely(n)`, `aloof(n)` here, never `a(n)` —
  three sequences are in play and A002386/A096265 genuinely collide at n=62,63.
