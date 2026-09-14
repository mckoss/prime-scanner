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

## Status 2026-09-14: publishing checkpoint reached

The bake is done, two days ahead of the plan. `fresh/frontier.txt` stands at
**2,075,805,595,153,846 (2.0758e15)** with all four sequences level, so the
A058867 catch-up (A2) is finished. The scan is still running, open-ended, and
the bound only improves from here — but nothing below waits on it.

`./check_oeis.py fresh` at that frontier, every record Miller-Rabin verified:

| family | ours | published below the frontier | result |
|--------|------|------------------------------|--------|
| gap, A002386 | 64 | 64 | agree |
| lonely, A023186 | 56 | 56 | agree |
| aloof, A096265 | 68 | 55 (b-file) | agree; 13 past its b-file |
| aloof, A031133/4/2 | 68 | 67 (= A096265 index 68) | agree on lower, upper and span |
| equidistant, A058867 | 30 | 30 | agree — the fourth running maximum is right |
| balanced (unpublished) | 5 | — | all 5 inside `equidistant.txt`, as they must be |

What the week bought, against the original plan:

| planned | frontier | outcome |
|---------|----------|---------|
| past **lonely(56)** | 9.41e14 | confirmed `941114429467073`; **no lonely(57)** below 2.07e15 |
| **gap(62)** | 1.19e15 | confirmed `1189459969825483` |
| **gap(63)**, **gap(64)** | 1.69e15 | confirmed `1686994940955803`, `1693182318746371` |
| past the aloof family | 1.69e15 | aloof(67), aloof(68) confirmed; **no aloof(69)** below 2.07e15 |
| A058867 catch-up | 2.07e15 | caught up; its 30 terms reproduced, **no 31st** below 2.07e15 |

`1693182318746371` is both gap(64) and aloof(68): the 1132 gap above it is a
record on its own, and with the 20 below it a record span of 1152.

No new terms, then — the result is **completeness bounds**, every one of them
now at 2.07e15, which is 11x A058867's published reach, 2.2x A023186's and
1.2x A031134's.

Use the frontier in `fresh/frontier.txt` at submission time, not `round.txt`:
the round's end is where the scan is working, not where it is complete.

Do **not** pass `--to` to the running scan; it is open-ended and should stay so.

## Submission order

1. **B1 — A096265 b-file.** Ready; every term now confirmed here.
2. **D — A031133/A031134 reverse link to A096265.** Goes with B1.
3. **A — balanced lonely primes.** Refresh the bound, then submit.
4. **E — search-bound comments** on A023186, A058867 and A031133.
5. **B5/B6, C — A058867/A058868 b-files and a-files, lonely/aloof a-files.**
   Built from `fresh/`; no longer blocked.
6. B2/B3 (A005669, A107578) from Andersen–Luhn — independent of this scan.
7. B4 (A122412/3) — needs `primecount`.

State every bound rounded **down** from `fresh/frontier.txt`: "no further terms
below 2*10^15", never 2.1*10^15.

---

## A. New sequence — balanced lonely primes

Draft: [`proposed/balanced-lonely-primes.md`](proposed/balanced-lonely-primes.md)
Terms: `<run>/balanced.txt`, filtered out of `lonely.txt` at every merge.

- [x] update the completeness bound: the draft says 2*10^15 as of 2026-09-14
- [ ] recheck it against the frontier at submission time, rounded down
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

## A2. A058867 — caught up

**Done.** Caught up from zero and rolled back in with the other three; at
2.07e15 it reproduces all 30 published terms and finds no 31st. What it
contributes is a completeness bound 11x past A058867's last term, and the
bounding primes for an a-file. The rest of this section is how it was run.

Its 30 terms stop at **1.879e14** and the scan is well past that, so it was the
one family here with genuinely new terms within reach rather than a tidy-up of
the published record.

Its records are maxima *within the balanced primes*, so no filter over
`lonely.txt` can produce them — `sieve.c` now keeps a fourth running maximum
for it. That leaves it at zero while the other three sit at the frontier, so
it has to be caught up over ground already scanned:

```
make                                        # the sieve must know the new kind
python3 pgaps.py --out fresh --status       # equidistant sits at 0
python3 pgaps.py --out fresh --jobs 8       # warns, asks, then catches up
```

The driver notices on its own, says what it is about to do, and waits for a
yes. Catch-up rounds scan only the lagging sequence and merge only its file,
so `gap.txt`, `lonely.txt` and `aloof.txt` are left byte-for-byte alone; the
other three roll back in when the scan reaches their frontier. About **2.3
days** from zero at the measured rate. See
[`../fresh/README.md`](../fresh/README.md) for the per-sequence
`frontier.txt`.

It is caught up from **zero, unseeded**, not from A058867's published terms.
The point of `fresh/` is a record with no external dependencies, and a seeded
run would inherit exactly the completeness assumption the scan exists to
replace.

- [x] run the catch-up
- [x] `check_oeis.py fresh` — the term-by-term diff against A058867 below its
      own bound, which is the check that the fourth running maximum is right:
      30 of 30 agree
- [ ] then B and C below, for A058867/A058868

## B. b-files — stale within their own family

Each is fixable from already-published data; none is a discovery claim.

| # | sequence | state | source | status |
|---|----------|-------|--------|--------|
| 1 | **A096265** | 55 terms, 12 behind its siblings | A031133/A031134, and now this scan | **ready to submit**: [`proposed/b096265.txt`](proposed/b096265.txt) — all 68 terms match `fresh/aloof.txt`, so it is an independent confirmation, not a transcription. Header and [`proposed/README.md`](proposed/README.md) updated 2026-09-14 |
| 2 | **A005669** | 82 terms, 3 behind | "Index via primecount.exe" column of [Andersen–Luhn](https://www.pzktupel.de/RecordGaps/risinggap.php) | not started |
| 3 | **A107578** | 80 terms, 5 behind | `A107578(n) = A005669(n) + 1`, verified at all 80 shared terms | not started |
| 4 | A122412 / A122413 | 52 terms, 15 behind | needs π(p) at p ≈ 1.69e15 — real compute (`primecount`) | not started |
| 5 | **A058867** | 30 terms, no uploaded b-file (DATA only) | `fresh/equidistant.txt` | unblocked — adds no terms, so low value without the a-file |
| 6 | A058868 | 30 terms, no uploaded b-file (DATA only) | the distance column of `fresh/equidistant.txt` | unblocked — same |
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
| lonely | **missing** | build from this scan: prime, both neighbours, both gaps — all 56 records, complete to 2.07e15 |
| equidistant | **missing** | build from this scan; `fresh/equidistant.txt` has all 30, complete to 2.07e15 |

Beveridge's file is the format to copy: one column per contributing sequence,
with a header naming the A-number each column belongs to. Not our 7-column
layout — theirs is the established convention.

## D. Cross-references

- [ ] A031133 and A031134 cite A031131/2/4 and A122412/3 but **not** A096265,
      so the aloof duplication is findable in only one direction. Propose the
      reverse link.

## E. Search-bound comments

The scan's completeness bounds exist nowhere in OEIS except as a line in the
new sequence (A). Each family whose published terms the scan has passed can
take a one-line comment in the usual form:

| sequence | last published term | comment |
|----------|---------------------|---------|
| A023186 (and A023187) | lonely(56) = 941114429467073 | no further terms below 2*10^15 |
| A058867 (and A058868) | 187891466722913 | no further terms below 2*10^15 |
| A031133/4/2 (and A096265) | aloof(68) = 1693182318746371 | no further terms below 2*10^15 |

- [ ] check each entry for an existing search-limit comment, and word the new
      one to supersede it
- [ ] submit, citing an exhaustive scan from 0 and the date

---

## Notes

- OEIS is CC BY-SA 4.0; the b-files in `oeis/` are committed with attribution.
- Submissions go through draft → proposed → editor review (pink boxes) →
  approval. Days to weeks.
- Terms are written `gap(n)`, `lonely(n)`, `aloof(n)` here, never `a(n)` —
  three sequences are in play and A002386/A096265 genuinely collide at n=62,63.
