#!/usr/bin/env python3
"""Compare a results directory against the published OEIS sequences.

For a from-scratch run (no --seed), every term should match from a(1) up to
wherever the scan reached. Any disagreement below that point is a real
discrepancy -- in this program, or in OEIS.

    python3 check_oeis.py results
    python3 check_oeis.py results --scanned 9.41e14
"""

import argparse
import os
import subprocess
import sys

SEQ = {"gap": ("A002386", "primes at the lower end of a record gap"),
       "lonely": ("A023186", "lonely primes"),
       "aloof": ("A096265", "aloof primes")}
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".oeis-cache")


def bfile(aid):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"b{aid[1:]}.txt")
    if not os.path.exists(path):
        url = f"https://oeis.org/{aid}/b{aid[1:]}.txt"
        r = subprocess.run(["curl", "-sSfL", "-A", "Mozilla/5.0", url, "-o", path])
        if r.returncode != 0:
            sys.exit(f"could not fetch {url}")
    return [int(l.split()[1]) for l in open(path) if l.strip() and l[0].isdigit()]


def ours(directory, kind):
    path = os.path.join(directory, f"{kind}.txt")
    if not os.path.exists(path):
        return []
    return [int(l.split()[1]) for l in open(path)
            if not l.startswith("#") and l.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
             formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results")
    ap.add_argument("--scanned", type=float,
                    help="upper limit actually scanned; terms above it are "
                         "not expected to be present")
    args = ap.parse_args()

    rc = 0
    for kind, (aid, desc) in SEQ.items():
        pub, got = bfile(aid), ours(args.results, kind)
        limit = args.scanned or (max(got) if got else 0)
        expect = [p for p in pub if p <= limit]

        n = min(len(expect), len(got))
        bad = [(i + 1, got[i], expect[i]) for i in range(n) if got[i] != expect[i]]

        status = "OK " if not bad and len(got) >= len(expect) else "!! "
        print(f"  {status}{kind:<7} {aid}  ours {len(got):>3} terms | "
              f"OEIS {len(expect):>3} below {limit:.3e}  ({desc})")
        for i, a, b in bad[:3]:
            print(f"       term {i}: ours {a}, OEIS {b}")
            rc = 1
        if not bad and len(got) > len(expect):
            for p in got[len(expect):]:
                print(f"       NEW: a({got.index(p) + 1}) = {p} "
                      f"(beyond the published sequence)")
        elif len(got) < len(expect):
            print(f"       missing {len(expect) - len(got)} term(s) OEIS has, "
                  f"e.g. {expect[len(got)]}")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
