#!/usr/bin/env python3
"""Compare a results directory against the published OEIS sequences.

This is a full positional diff of two *complete* lists, not a spot check of
isolated terms. The results being compared come from an exhaustive scan --
every integer in range is visited and the merge applies the running-maximum
rule -- so term i of ours must equal term i of theirs, with nothing missing
and nothing extra below the scanned limit.

Three things are checked:

  1. every published term below the limit appears, at the same index;
  2. no extra term appears below the limit (which would mean OEIS missed one);
  3. each record is genuinely a record: prev, prime and next are all prime
     and no prime lies between them, tested by deterministic Miller-Rabin,
     independently of the sieve that produced them.

The limit is taken from the run's own frontier.txt unless --scanned overrides
it, so it cannot be overstated by accident.

    python3 check_oeis.py results
    python3 check_oeis.py verify --scanned 9.41e14
"""

import argparse
import os
import subprocess
import sys
import time

SEQ = {"gap": ("A002386", "primes at the lower end of a record gap"),
       "lonely": ("A023186", "lonely primes"),
       "aloof": ("A096265", "aloof primes")}
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".oeis-cache")


STALE_DAYS = 30


def bfile(aid, refresh=False):
    """The b-file, which is the full published data -- longer than the DATA
    section shown on the sequence page.

    These grow: A002386 went from 77 terms to 85 as ranks 78-85 were confirmed
    one at a time between 2018 and 2026. A stale cache would report an already
    published term as ours, so say how old it is and offer to refetch.
    """
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"b{aid[1:]}.txt")
    if refresh or not os.path.exists(path):
        url = f"https://oeis.org/{aid}/b{aid[1:]}.txt"
        tmp = path + ".new"
        r = subprocess.run(["curl", "-sSfL", "-A", "Mozilla/5.0", url, "-o", tmp])
        got = os.path.exists(tmp) and os.path.getsize(tmp) > 0
        if r.returncode != 0 or not got:
            if os.path.exists(tmp):
                os.remove(tmp)
            if os.path.exists(path):
                print(f"  ! could not refresh {url}; using the cached copy")
            else:
                sys.exit(f"could not fetch {url}")
        else:
            os.replace(tmp, path)
    else:
        age = (time.time() - os.path.getmtime(path)) / 86400
        if age > STALE_DAYS:
            print(f"  ! {os.path.basename(path)} cached {age:.0f} days ago; "
                  f"rerun with --refresh to check for new published terms")
    return [int(l.split()[1]) for l in open(path) if l.strip() and l[0].isdigit()]


def miller_rabin(n):
    """Deterministic for n < 3.3e24, so it covers the whole 64-bit range."""
    if n < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in small:
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def verify_rows(directory, kind):
    """Confirm each record's prime triple, without trusting the sieve."""
    path = os.path.join(directory, f"{kind}.txt")
    problems = []
    if not os.path.exists(path):
        return problems
    for line in open(path):
        if line.startswith("#") or not line.strip():
            continue
        f = [int(x) for x in line.split()]
        if len(f) != 7:
            problems.append(f"malformed line: {line.strip()}")
            continue
        n, p, value, below, above, prev, nxt = f
        if prev == 0:
            continue                       # p = 2 has no lower neighbour
        for q in (prev, p, nxt):
            if not miller_rabin(q):
                problems.append(f"{kind}({n}): {q} is not prime")
        if p - prev != below or nxt - p != above:
            problems.append(f"{kind}({n}): neighbours disagree with the gaps")
        want = {"gap": above, "lonely": min(below, above),
                "aloof": below + above}[kind]
        if value != want:
            problems.append(f"{kind}({n}): value {value}, expected {want}")
        for q in range(prev + 1, p):
            if miller_rabin(q):
                problems.append(f"{kind}({n}): {q} lies between {prev} and {p}")
                break
        for q in range(p + 1, nxt):
            if miller_rabin(q):
                problems.append(f"{kind}({n}): {q} lies between {p} and {nxt}")
                break
    return problems


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
                    help="upper limit actually scanned (default: the run's "
                         "own frontier.txt, so it cannot be overstated)")
    ap.add_argument("--no-verify", action="store_true",
                    help="skip the Miller-Rabin check of each record")
    ap.add_argument("--refresh", action="store_true",
                    help="refetch the b-files instead of using the cache; the "
                         "published sequences do get extended")
    args = ap.parse_args()

    frontier = os.path.join(args.results, "frontier.txt")
    if args.scanned is None and os.path.exists(frontier):
        args.scanned = float(open(frontier).read().strip())
        print(f"  limit taken from frontier.txt: {args.scanned:.4e}")
    elif args.scanned is None:
        print("  no frontier.txt and no --scanned: comparing only as far as "
              "our own last term (weaker: cannot detect a missing tail)")

    rc = 0
    for kind, (aid, desc) in SEQ.items():
        pub, got = bfile(aid, args.refresh), ours(args.results, kind)
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
                print(f"       NEW: {kind}({got.index(p) + 1}) = {p} "
                      f"(beyond the published sequence)")
        elif len(got) < len(expect):
            print(f"       missing {len(expect) - len(got)} term(s) OEIS has, "
                  f"e.g. {expect[len(got)]}")
            rc = 1

        if not args.no_verify:
            problems = verify_rows(args.results, kind)
            if problems:
                rc = 1
                print(f"       {len(problems)} record(s) fail primality "
                      f"verification:")
                for m in problems[:3]:
                    print(f"         {m}")
            else:
                print(f"       {len(got)} record(s) verified prime "
                      f"(Miller-Rabin, independent of the sieve)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
