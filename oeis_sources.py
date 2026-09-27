"""Published source tables used by the audit, separate from scan results."""

from functools import lru_cache
from pathlib import Path
import re

from check_oeis import miller_rabin

SOURCE_DIR = Path(__file__).resolve().parent / "oeis" / "sources"
BALANCED_URL = "https://oeis.org/A052187/b052187.txt"
GAPS_URL = "https://sweet.ua.pt/tos/gaps/t0.txt.gz"
ULONG_MAX = 2**64 - 1


@lru_cache(maxsize=None)
def balanced_triples():
    """Middle prime -> (source index, lower prime, distance, upper prime).

    These are first occurrences at individual distances, NOT a complete
    record sequence. A052187(1) has distance 2; the rest have 6*(n-1).
    """
    out = {}
    for line in (SOURCE_DIR / "b052187.txt").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        n, lower = map(int, line.split())
        distance = 2 if n == 1 else 6 * (n - 1)
        out[lower + distance] = (n, lower, distance, lower + 2 * distance)
    return out


def balanced_matches(rows):
    """Match entire triples, retaining scan indices and source indices."""
    matches = {}
    for row in rows:
        n, p, value, below, above, lower, upper = row
        source = balanced_triples().get(p)
        if source is None:
            continue
        k, pp, d, np = source
        if (value, below, above, lower, upper) != (d, d, d, pp, np):
            raise ValueError(f"equidistant({n}) disagrees with A052187({k})")
        matches[n] = source
    return matches


def balanced_credit(n, source):
    k, lower, distance, _ = source
    return (f"a({n}) = A052187({k}) + {distance}; the prime triple was "
            "already tabulated in A052187 (table credited to Jerry M. "
            "Lagrou and earlier contributors), and is independently "
            "confirmed by this scan.")


@lru_cache(maxsize=None)
def first_gaps():
    """(gap, lower prime, original finder) from the verbatim source table.

    Asterisks mark records in the source. Rows with '?' are absent gap
    sizes, not zero-valued primes or known first occurrences.
    """
    rows = []
    for line in (SOURCE_DIR / "oliveira-silva-gaps.txt").read_text().splitlines():
        if not re.match(r"^\s*\d", line):
            continue
        fields = line.split(None, 3)
        gap = int(fields[0].rstrip("*"))
        if fields[1].rstrip("*") == "?":
            continue
        lower = int(fields[1].rstrip("*"))
        int(fields[2])  # Require the published count column.
        rows.append((gap, lower, fields[3] if len(fields) > 3 else ""))
    return rows


def adjacent_prime(p, direction):
    q = p + 2 * direction
    while 2 < q <= ULONG_MAX:
        if miller_rabin(q):
            return q
        q += 2 * direction
    raise ValueError(f"no adjacent odd prime in range for {p}")


def verify_triple(lower, p, upper):
    """Certify adjacency locally; this does not certify global record status."""
    if not 2 < lower < p < upper <= ULONG_MAX:
        raise ValueError("prime triple is outside the supported odd-prime range")
    found = [q for q in range(lower, upper + 1, 2) if miller_rabin(q)]
    if found != [lower, p, upper]:
        raise ValueError(f"not consecutive primes: {lower}, {p}, {upper}")


def aloof_checkpoints(frontier, threshold, limit=3):
    """Earliest qualifying endpoints in the source, not promised next terms.

    Compute only small neighborhoods. Never feed these points to the scan's
    merge or raise its completeness frontier. Filter against the CURRENT
    aloof span so checkpoints become obsolete as the scan advances.
    """
    endpoints = []
    for gap, lower, finder in first_gaps():
        upper = lower + gap
        if not 2 < lower < upper < ULONG_MAX:
            continue
        endpoints += [(lower, gap, lower, upper, finder),
                      (upper, gap, lower, upper, finder)]
    hits = []
    for p, gap, lower, upper, finder in sorted(endpoints):
        if p <= frontier:
            continue
        pp, np = ((adjacent_prime(p, -1), upper) if p == lower else
                  (lower, adjacent_prime(p, 1)))
        if np - pp <= threshold:
            continue
        verify_triple(pp, p, np)
        hits.append({"prime": p, "below": p - pp, "above": np - p,
                     "span": np - pp, "lower": pp, "upper": np,
                     "source_gap": gap, "source_prime": lower,
                     "finder": finder})
        if len(hits) == limit:
            break
    return hits
