# Published source tables

These committed snapshots are inputs to `oeis_sources.py` and the OEIS audit.
They are independent of the scan's merged results and its completeness bounds.
Retrieved September 26, 2026. Both text files preserve the source bytes (the
Oliveira e Silva table is the verbatim decompression of the downloaded gzip).

## A052187: first balanced triple at each distance

- File: [b052187.txt](b052187.txt), 72 terms.
- Source: <https://oeis.org/A052187/b052187.txt>
- Definition and attribution: <https://oeis.org/A052187>
- Table credited to Jerry M. Lagrou; terms 1..39 from Donovan Johnson,
  terms 40..53 from Giovanni Resta.
- OEIS data: CC BY-SA 4.0, under the
  [OEIS license agreement](https://oeis.org/wiki/The_OEIS_End-User_License_Agreement).

Row `n p` gives the lower prime; the common distance is 2 for n=1 and
6*(n-1) otherwise. Add that distance to obtain the middle prime.
The table includes A052187(72)=2422627449333671, giving our
equidistant(31)=2422627449334097 at distance 426. This prime triple was
already published even though A058867 still stops at term 30. Extending
A058867 is appropriate, with attribution and independent confirmation.

This is a first-occurrence table indexed by distance, not an ordered list
of record primes. Its 72 rows do not imply 72 equidistant records or a
completeness bound on other distances. The audit matches complete triples.

## Oliveira e Silva: first occurrences of prime gaps

- File: [oliveira-silva-gaps.txt](oliveira-silva-gaps.txt).
- Download: <https://sweet.ua.pt/tos/gaps/t0.txt.gz>
- Author's explanatory page: <https://sweet.ua.pt/tos/gaps.html>
- Related paper: Tomas Oliveira e Silva, Siegfried Herzog, and Silvio Pardi,
  *Empirical verification of the even Goldbach conjecture and computation
  of prime gaps up to 4*10^18*, Mathematics of Computation 83 (2014),
  2033-2060. <https://doi.org/10.1090/S0025-5718-2013-02787-1>

This is the author's full companion data table, not a transcription of the
paper's shorter printed tables. It retains its copyright notice, finder
credits, count columns, record markers, and unknown (`?`) entries. The
header says last updated April 7, 2012, with copyright 2012-2016. It reports
coverage to 4*10^18 and double checking to 4*10^17. Retrieval date is not
the computation date. No new license is asserted for this source.

Each row gives a gap size, its first lower prime, occurrence count, and
finder. The audit inspects both endpoints and determines the adjacent
prime outside the published gap. Before reporting a checkpoint it checks
the three primes and every intervening odd integer with deterministic
Miller-Rabin. It never infers global record status from a local check.

At aloof span 1152, the earliest qualifying future endpoints in this table
are 25016149672698647 (1098+60=1158), 28269785077312447
(1038+142=1180), and 29835422457878441 (160+1106=1266). The source credits
the underlying gaps to B. Nyman. These guarantee improvement by the first
point, but earlier stronger records may supersede any of them. Neither
future candidates nor their positions are written into scan results.

The report recomputes witnesses using the current aloof frontier and span.
Arrival times are intentionally absent: they depend on current hardware,
worker count, throughput, and pauses, not on the source table.

## Snapshot integrity and updates

SHA-256 of the committed text files:

- `b052187.txt`: `ed835dd743c72d6a343e1cf0d85aa4120c3cd42fec67e4482f80e52a9450d880`
- `oliveira-silva-gaps.txt`: `8bb9fda9e6fd85ff31790f5708c57fc6419d8edd4a736f28cbcfa1b214f75cfb`

To update a snapshot, download its source to a temporary file, compare it
with the committed copy, retain the original bytes and attribution, update
the retrieval date/checksum here, then run `python3 test_audit.py` and
`make audit`. Network fetching is not needed for these source comparisons.
