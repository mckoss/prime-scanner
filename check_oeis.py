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
    python3 check_oeis.py --refresh          # just update the cached b-files
"""

import argparse
import os
import subprocess
import sys
import time

SEQ = {"gap": ("A002386", "primes at the lower end of a record gap"),
       "lonely": ("A023186", "lonely primes"),
       "aloof": ("A096265", "aloof primes"),
       "equidistant": ("A058867", "record distance among balanced primes")}
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oeis")

# A096265 lists the aloof primes, but its b-file stops at 55 terms while the
# SAME records are published far deeper as a three-sequence family: the lower
# neighbour, the upper neighbour and the span. That family is indexed one lower
# than A096265, which carries an extra a(1) = 2 having no lower neighbour --
# so family term k is A096265 term k+1. Checking only A096265 makes records
# that are already published look like discoveries.
ALOOF_FAMILY = {"aloof-lower": ("A031133", 6),    # column 6 of ours: prev_prime
                "aloof-upper": ("A031134", 7),    # column 7 of ours: next_prime
                "aloof-span":  ("A031132", 3)}    # column 3 of ours: value
ALOOF_OFFSET = 1

# balanced.txt has no sequence of its own, but it is not unchecked: every
# balanced-lonely record must appear in equidistant.txt. If p beats every
# prime below it on min(gap below, gap above), it beats every *balanced*
# prime below it in particular, so p sets a record among balanced primes too.
# A058867 is that record sequence, and the scan now derives it independently,
# so the containment is checked against our own records as well as theirs.
BALANCED_SUPER = "equidistant"


STALE_DAYS = 30


def read_terms(path):
    """The a(n) column of a b-file, in order."""
    return [int(l.split()[1]) for l in open(path) if l.strip() and l[0].isdigit()]


def bfile(stem, aid, refresh=False):
    """The b-file, which is the full published data -- longer than the DATA
    section shown on the sequence page.

    These grow: A002386 went from 77 terms to 85 as ranks 78-85 were confirmed
    one at a time between 2018 and 2026. A stale cache would report an already
    published term as ours, so say how old it is and offer to refetch.
    """
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{stem}.txt")

    if refresh or not os.path.exists(path):
        url = f"https://oeis.org/{aid}/b{aid[1:]}.txt"
        before = read_terms(path) if os.path.exists(path) else None
        tmp = path + ".new"
        r = subprocess.run(["curl", "-sSfL", "-A", "Mozilla/5.0", url, "-o", tmp])
        if r.returncode != 0 or not os.path.exists(tmp) or not os.path.getsize(tmp):
            if os.path.exists(tmp):
                os.remove(tmp)
            if before is None:
                sys.exit(f"could not fetch {url}")
            print(f"  ! {aid}: could not refresh; using the cached copy")
        else:
            after = read_terms(tmp)
            os.replace(tmp, path)
            if before is None:
                print(f"  + {aid}: fetched, {len(after)} terms")
            elif after == before:
                print(f"  = {aid}: unchanged, {len(after)} terms")
            else:
                # A published term appearing here is one this scan can no
                # longer claim, so name them rather than just counting.
                added = [t for t in after if t not in set(before)]
                gone = [t for t in before if t not in set(after)]
                print(f"  * {aid}: UPDATED, {len(before)} -> {len(after)} terms")
                for t in added[:5]:
                    print(f"      + a({after.index(t) + 1}) = {t}")
                if len(added) > 5:
                    print(f"      + ... and {len(added) - 5} more")
                for t in gone[:5]:
                    print(f"      - withdrawn: {t}")
    else:
        age = (time.time() - os.path.getmtime(path)) / 86400
        if age > STALE_DAYS:
            print(f"  ! {os.path.basename(path)} cached {age:.0f} days ago; "
                  f"rerun with --refresh to check for new published terms")
    return read_terms(path)


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
        if kind in ("balanced", "equidistant") and below != above:
            problems.append(f"{kind}({n}): {below} below, {above} above -- "
                            f"not balanced")
        want = {"gap": above, "lonely": min(below, above),
                "aloof": below + above, "balanced": below,
                "equidistant": below}[kind]
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


def coverage(directory):
    """How far each kind was scanned, when the run tracked that per kind.

    A kind added to an existing run is caught up separately, so for a while
    it is complete to a lower point than the rest. Comparing it against the
    published sequence up to the run's frontier would then report every term
    above its own bound as missing.
    """
    cov = {}
    path = os.path.join(directory, "coverage.txt")
    if os.path.exists(path):
        for line in open(path):
            if line.startswith("#") or not line.strip():
                continue
            f = line.split()
            if len(f) >= 2:
                cov[f[0]] = float(f[1])
        return cov

    # A run from before coverage.txt was written has none. Infer it the same
    # way pgaps.py does: a kind with no results file has never been scanned,
    # whatever the frontier says.
    fpath = os.path.join(directory, "frontier.txt")
    if not os.path.exists(fpath):
        return cov
    front = float(open(fpath).read().split()[0])
    for kind in SEQ:
        cov[kind] = front if os.path.exists(
            os.path.join(directory, f"{kind}.txt")) else 0.0
    return cov


def ours(directory, kind):
    path = os.path.join(directory, f"{kind}.txt")
    if not os.path.exists(path):
        return []
    return [int(l.split()[1]) for l in open(path)
            if not l.startswith("#") and l.strip()]


def rows(directory, kind):
    """Our full 7-column records, not just the primes."""
    out = []
    path = os.path.join(directory, f"{kind}.txt")
    if not os.path.exists(path):
        return out
    for line in open(path):
        if line.startswith("#") or not line.strip():
            continue
        f = [int(x) for x in line.split()]
        if len(f) == 7:
            out.append(f)
    return out


def check_aloof_family(directory, refresh, rc):
    """Compare aloof against A031133/A031134/A031132, not just A096265.

    A096265's b-file stops at 55 terms; the same records are published to 67
    in this family, which reaches 1.69e15. Judging "new" against A096265 alone
    reports long-published records as discoveries -- it did, for eight terms.
    """
    fam = {stem: bfile(stem, aid, refresh)
           for stem, (aid, _) in ALOOF_FAMILY.items()}
    lo, hi, span = fam["aloof-lower"], fam["aloof-upper"], fam["aloof-span"]
    got = rows(directory, "aloof")
    if not got or not lo:
        return rc

    # family term k is A096265 term k + ALOOF_OFFSET
    bad = []
    for k in range(1, min(len(lo), len(got) - ALOOF_OFFSET) + 1):
        n, p, value, below, above, prev, nxt = got[k + ALOOF_OFFSET - 1]
        if (lo[k - 1], hi[k - 1], span[k - 1]) != (prev, nxt, value):
            bad.append((k, n))

    covered = len(lo) + ALOOF_OFFSET          # A096265 index the family reaches
    status = "!! " if bad else "OK "
    print(f"  {status}aloof   A031133/4/2  ours {len(got):>3} terms | "
          f"family {len(lo)} terms = A096265 index {covered} "
          f"(to {hi[-1]:.3e})")
    for k, n in bad[:3]:
        print(f"       family term {k} disagrees with our aloof({n})")
        rc = 1
    if not bad:
        print(f"       {min(len(lo), len(got) - ALOOF_OFFSET)} term(s) agree on "
              f"lower, upper and span")
    beyond = len(got) - covered
    if beyond > 0:
        print(f"       {beyond} term(s) genuinely beyond the family:")
        for r in got[covered:]:
            print(f"         aloof({r[0]}) = {r[1]}  span {r[2]}")
    else:
        print(f"       nothing new: the family is {-beyond} term(s) AHEAD of "
              f"this scan (its next is at {hi[len(got) - ALOOF_OFFSET]:,})"
              if len(hi) > len(got) - ALOOF_OFFSET else
              f"       nothing new yet")
    return rc


def check_balanced(directory, rc):
    """Check balanced.txt against lonely.txt, and against equidistant.txt.

    Two independent things can go wrong and each has its own check: the filter
    could drop or invent a row (caught against lonely.txt, the only place its
    terms can come from), or a row could not be a balanced record at all
    (caught against equidistant.txt, which the sieve derives independently and
    which is itself diffed against A058867 above).
    """
    got, lonely = rows(directory, "balanced"), rows(directory, "lonely")
    if not lonely:
        return rc
    want = [r for r in lonely if r[5] and r[3] == r[4]]

    mine, theirs = [r[1] for r in got], [r[1] for r in want]
    status = "OK " if mine == theirs else "!! "
    print(f"  {status}balanced  (unpublished)  ours {len(got):>3} terms | "
          f"filtered from {len(lonely)} lonely records "
          f"(lonely records that are also balanced primes)")
    if mine != theirs:
        rc = 1
        for p in [x for x in theirs if x not in set(mine)][:3]:
            print(f"       lonely.txt has balanced {p}, balanced.txt does not")
        for p in [x for x in mine if x not in set(theirs)][:3]:
            print(f"       balanced.txt has {p}, which is not a balanced "
                  f"lonely record")

    problems = verify_rows(directory, "balanced")
    if problems:
        rc = 1
        print(f"       {len(problems)} record(s) fail verification:")
        for m in problems[:3]:
            print(f"         {m}")
    else:
        print(f"       {len(got)} record(s) verified prime (Miller-Rabin, "
              f"independent of the sieve)")

    super_ = [r[1] for r in rows(directory, BALANCED_SUPER)]
    if super_:
        missing = [p for p in mine if p not in set(super_)]
        if missing:
            rc = 1
            print(f"       {len(missing)} term(s) NOT in {BALANCED_SUPER}.txt, "
                  f"which must contain every one: {missing[:3]}")
        else:
            print(f"       all {len(mine)} appear in {BALANCED_SUPER}.txt "
                  f"({len(super_)} records), as they must")
    return rc


def main():
    ap = argparse.ArgumentParser(description=__doc__,
             formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", nargs="?",
                    help="results directory to check; omit with --refresh to "
                         "only update the cached b-files")
    ap.add_argument("--scanned", type=float,
                    help="upper limit actually scanned (default: the run's "
                         "own frontier.txt, so it cannot be overstated)")
    ap.add_argument("--no-verify", action="store_true",
                    help="skip the Miller-Rabin check of each record")
    ap.add_argument("--refresh", action="store_true",
                    help="refetch the b-files instead of using the cache; the "
                         "published sequences do get extended")
    args = ap.parse_args()

    if args.results is None:
        if not args.refresh:
            ap.error("give a results directory, or --refresh on its own "
                     "to just update the cached b-files")
        for kind, (aid, _) in SEQ.items():
            bfile(kind, aid, refresh=True)
        for stem, (aid, _) in ALOOF_FAMILY.items():
            bfile(stem, aid, refresh=True)
        return 0

    forced = args.scanned is not None
    cov = coverage(args.results)
    frontier = os.path.join(args.results, "frontier.txt")
    if args.scanned is None and os.path.exists(frontier):
        args.scanned = float(open(frontier).read().strip())
        print(f"  limit taken from frontier.txt: {args.scanned:.4e}")
    elif args.scanned is None:
        print("  no frontier.txt and no --scanned: comparing only as far as "
              "our own last term (weaker: cannot detect a missing tail)")

    if cov and len(set(cov.values())) > 1:
        low = min(cov, key=cov.get)
        print(f"  {low} is scanned only to {cov[low]:.4e}, below the "
              f"frontier -- it is checked against its own bound")

    rc = 0
    for kind, (aid, desc) in SEQ.items():
        pub, got = bfile(kind, aid, args.refresh), ours(args.results, kind)
        limit = args.scanned if forced else cov.get(kind, args.scanned)
        limit = limit or (max(got) if got else 0)
        expect = [p for p in pub if p <= limit]

        n = min(len(expect), len(got))
        bad = [(i + 1, got[i], expect[i]) for i in range(n) if got[i] != expect[i]]

        status = "OK " if not bad and len(got) >= len(expect) else "!! "
        print(f"  {status}{kind:<11} {aid}  ours {len(got):>3} terms | "
              f"OEIS {len(expect):>3} below {limit:.3e}  ({desc})")
        for i, a, b in bad[:3]:
            print(f"       term {i}: ours {a}, OEIS {b}")
            rc = 1
        if not bad and len(got) > len(expect):
            if kind == "aloof":
                # A096265 is not the deepest published source for these
                # records; the family check below is authoritative.
                print(f"       {len(got) - len(expect)} term(s) past "
                      f"{aid}'s b-file -- see the family check below")
            else:
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

    rc = check_aloof_family(args.results, args.refresh, rc)
    rc = check_balanced(args.results, rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
