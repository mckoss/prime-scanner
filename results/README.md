# Search results

Live output of `./sieve --gaps --out results`. The search resumes from
`progress.txt`, so it can be stopped and restarted at any time:

```
./sieve --gaps --out results 50000000000000
```

## Files

| file | contents |
|------|----------|
| `gap.txt` | record prime gaps — [A005250](https://oeis.org/A005250) / [A002386](https://oeis.org/A002386) |
| `lonely.txt` | record distance to the *nearer* neighbour — [A023186](https://oeis.org/A023186) |
| `aloof.txt` | record total span between *both* neighbours — [A096265](https://oeis.org/A096265) |
| `progress.txt` | checkpoints; the last line is the resume point |

Each results line is

```
<n> <prime> <value> <gap_below> <gap_above> <prev_prime> <next_prime>
```

The first two columns are an OEIS b-file. The last two make every line
self-contained proof: check that `prev`, `prime` and `next` are all prime and
that nothing lies between them, and the record stands without rerunning the
scan. `value` is whichever quantity that sequence maximises — `gap_above` for
gaps, `min(below, above)` for lonely, `below + above` for aloof.

## Seeding

`gap.txt` and `lonely.txt` were seeded with the published record in force at
the search start (~9.3e11), so the scan would not re-report the many terms
already known below it. `aloof.txt` was seeded with all 55 published terms of
A096265, so it reads as the complete sequence.

Because thresholds are recovered from these files rather than from
`progress.txt`, seeding a search to extend a published sequence is simply a
matter of writing its known terms here first.

## Status

A096265 was published to aloof(55) = 929,156,727,137, and this search found

```
aloof(56) = 1032148488557    span 678    1032148488143 < p < 1032148488821
```

**This was not a new term.** The same record is published as A031133(55) /
A031134(55) / A031132(55) — a three-sequence family holding the lower
neighbour, upper neighbour and span, indexed one below A096265. That family
reaches 67 terms (A096265 index 68, or 1.693e15), so aloof records were
already published well past this point; A096265's own b-file merely stopped
at 55. See [`../fresh/README.md`](../fresh/README.md) for the full account.

Every record in these files reproduces a published term exactly, which is a
useful running check on the scan:

| record | matches |
|--------|---------|
| gap #2, #3, #4 | gap(51), gap(52), gap(53) |
| lonely #2, #3 | lonely(45), lonely(46) |
| every aloof record | the A031133/A031134/A031132 family |
