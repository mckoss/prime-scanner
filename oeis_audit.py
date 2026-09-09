#!/usr/bin/env python3
"""Audit the gap / lonely / aloof sequence families for missing OEIS data.

The goal is completeness of the record, not new terms. Within a family every
sequence describes the same records -- the primes, their neighbours, the span,
the indices -- so they should all reach the same depth. Where one is shorter
than its siblings, its b-file is stale and can be extended from published data
alone. Where a family has no a-file, the bounding primes that make each record
checkable are not written down anywhere in a single place.

    python3 oeis_audit.py            # audit, using the cached copies
    python3 oeis_audit.py --refresh  # refetch from OEIS first
"""

import argparse
import json
import os
import re
import subprocess
import sys

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oeis", "audit")

# sieve.c stores every value in an unsigned long, so nothing above this
# is reachable no matter how long the scan runs.
ULONG_MAX = 2 ** 64 - 1

FAMILIES = {
    "gap": {
        "records": "maximal prime gaps",
        "extent": ("A002386", 0),
        "members": {
            "A002386": "prime at the lower end",
            "A000101": "prime at the upper end",
            "A005250": "the gap size",
            "A005669": "index of the lower prime",
            "A107578": "index of the upper prime",
            "A053695": ("differences between successive record gaps", -1),
        },
    },
    "lonely": {
        "records": "lonely primes -- record min(gap below, gap above)",
        "extent": ("A023186", 0),
        "members": {
            "A023186": "the lonely prime",
            "A023187": "the distance to the nearer neighbour",
        },
    },
    "aloof": {
        "records": "aloof primes -- record nextprime(p) - prevprime(p)",
        # A031134 holds the upper neighbour and runs one index below A096265,
        # which carries an extra a(1) = 2 having no lower neighbour.
        "extent": ("A031134", 1),
        "members": {
            "A096265": "the aloof prime",
            "A031133": "the lower neighbour",
            "A031134": "the upper neighbour",
            "A031132": "the span between the neighbours",
            "A122412": "index of the lower prime",
            "A122413": "index of the upper prime",
        },
    },
}


def fetch(url, path, refresh):
    if os.path.exists(path) and not refresh:
        return True
    os.makedirs(os.path.dirname(path), exist_ok=True)
    r = subprocess.run(["curl", "-sSfL", "-A", "Mozilla/5.0", url, "-o", path])
    if r.returncode != 0:
        if os.path.exists(path):
            os.remove(path)
        return False
    return True


def entry(aid, refresh):
    path = os.path.join(CACHE, f"{aid}.json")
    if not fetch(f"https://oeis.org/search?q=id:{aid}&fmt=json", path, refresh):
        return None
    try:
        d = json.load(open(path))
    except Exception:
        return None
    if not d:
        return None
    return d[0] if isinstance(d, list) else d["results"][0]


def bfile_terms(aid, refresh):
    """Number of terms in the b-file, or None if the sequence has none.

    OEIS synthesizes a b-file from the DATA section when none was uploaded, so
    a b-file that merely echoes DATA counts as missing.
    """
    path = os.path.join(CACHE, f"b{aid[1:]}.txt")
    if not fetch(f"https://oeis.org/{aid}/b{aid[1:]}.txt", path, refresh):
        return None, False
    text = open(path, errors="replace").read()
    synth = "synthesized" in text.split("\n")[0].lower()
    n = sum(1 for l in text.split("\n") if l.strip() and l[0].isdigit())
    return n, synth


def afile(rec, aid):
    """This sequence's OWN a-file: free-form data, e.g. a bounding-prime table.

    Entries often link another sequence's a-file, which says nothing about
    whether this one has documented its bounding primes.
    """
    own = re.compile(rf"/{aid}/a{aid[1:]}\.(txt|pdf)")
    return [l for l in (rec.get("link") or []) if own.search(l)]


def scan_days(lo, hi):
    """Days from lo to hi at the rate pgaps.py measured, or None."""
    try:
        import importlib.util
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pgaps.py")
        spec = importlib.util.spec_from_file_location("_pg", p)
        pg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pg)
    except Exception:
        return None
    if hi <= lo:
        return 0.0
    n, tot, x = 2000, 0.0, lo
    for i in range(1, n + 1):
        y = lo * (hi / lo) ** (i / n)
        tot += (y - x) / pg.scan_rate((x + y) / 2)
        x = y
    return tot / (8 * 4.39 / 8) / 86400        # 8 workers at the measured duty


def frontier_report(results, refresh):
    """Where this scan stands against each family's deepest published term."""
    fpath = os.path.join(results, "frontier.txt")
    if not os.path.exists(fpath):
        print(f"\n  no {fpath}; skipping the frontier comparison")
        return
    front = int(open(fpath).read().split()[0])
    print(f"\n\n#################### FRONTIER vs PUBLISHED ####################")
    print(f"\n  {results}/frontier.txt = {front:,}  ({front:.4e})\n")
    for fam, info in FAMILIES.items():
        aid, off = info["extent"]
        pub = bfile_terms_list(aid, refresh)
        ours = [int(l.split()[1]) for l
                in open(os.path.join(results, f"{fam}.txt"))
                if l.strip() and l[0].isdigit()] \
            if os.path.exists(os.path.join(results, f"{fam}.txt")) else []
        if not pub:
            continue
        extent = pub[-1]
        n_pub = len(pub) + off
        ahead = front > extent
        print(f"  {fam:<7} published to {extent:.4e} ({n_pub} terms, via {aid})")
        print(f"  {'':7} ours       {len(ours)} terms, frontier {front:.4e}")
        if ahead:
            new = len(ours) - n_pub
            print(f"  {'':7} -> frontier is PAST it: "
                  f"{max(new,0)} term(s) beyond publication"
                  + ("  <- submittable" if new > 0 else ""))
        elif extent > ULONG_MAX:
            print(f"  {'':7} -> past this program's 2^64 ceiling "
                  f"({ULONG_MAX:.4e}) -- unreachable, and nothing to contribute")
        else:
            d = scan_days(front, extent)
            when = f"~{d:.1f} days at the measured rate" if d is not None else ""
            print(f"  {'':7} -> {extent/front:.1f}x to go   {when}")
        print()


def bfile_terms_list(aid, refresh):
    path = os.path.join(CACHE, f"b{aid[1:]}.txt")
    if not fetch(f"https://oeis.org/{aid}/b{aid[1:]}.txt", path, refresh):
        return []
    return [int(l.split()[1]) for l in open(path, errors="replace")
            if l.strip() and l[0].isdigit()]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
             formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true",
                    help="refetch entries and b-files from OEIS")
    ap.add_argument("--results", metavar="DIR",
                    help="a scan directory (e.g. fresh); also report where its "
                         "frontier stands against each family's published extent")
    args = ap.parse_args()

    todo_b, todo_a = [], []
    for fam, info in FAMILIES.items():
        print(f"\n=== {fam}: {info['records']}")
        rows, deepest = [], 0
        for aid, role in info["members"].items():
            role, delta = role if isinstance(role, tuple) else (role, 0)
            rec = entry(aid, args.refresh)
            if rec is None:
                print(f"  ?? {aid}  could not fetch")
                continue
            n, synth = bfile_terms(aid, args.refresh)
            data_n = len(rec["data"].split(","))
            have_b = n is not None and not synth
            terms = n if have_b else data_n
            deepest = max(deepest, terms - delta)
            rows.append((aid, role, terms, have_b, afile(rec, aid), delta))

        print(f"  {'seq':<9} {'terms':>6} {'b-file':>7}  role")
        for aid, role, terms, have_b, af, delta in rows:
            short = terms < deepest + delta
            mark = "!!" if (short or not have_b) else "OK"
            print(f"  {mark} {aid:<9} {terms:>5}{'*' if not have_b else ' '} "
                  f"{'yes' if have_b else 'NO':>6}  {role}")
            if not have_b:
                # OEIS synthesizes a b-file from DATA, and DATA holds ~260
                # characters. If every known term already fits there, an
                # uploaded b-file adds nothing until the sequence grows.
                why = ("no uploaded b-file, but DATA already holds every known "
                       "term -- low priority")
                if terms < deepest + delta:
                    why = (f"no b-file, and DATA is "
                           f"{deepest + delta - terms} short of its siblings")
                todo_b.append((fam, aid, terms, deepest, why))
            elif short:
                todo_b.append((fam, aid, terms, deepest,
                               f"stale: {deepest + delta - terms} behind its siblings"))
        print(f"  deepest member: {deepest} terms      (* = DATA only, no b-file)")

        any_af = [(aid, af) for aid, _, _, _, af, _ in rows if af]
        if any_af:
            for aid, af in any_af:
                print(f"  a-file: {aid} -> {af[0][:88]}")
        else:
            print(f"  a-file: NONE -- no single table gives the bounding primes")
            todo_a.append(fam)

    print("\n\n#################### TO DO ####################")
    print("\nb-files to add or extend (all from already-published data):")
    if todo_b:
        for fam, aid, terms, deepest, why in todo_b:
            print(f"  [{fam:<6}] {aid}: {terms} terms, {why} (deepest {deepest})")
    else:
        print("  none -- every family member is at the same depth")
    print("\na-files -- a single table giving the bounding primes:")
    for fam in FAMILIES:
        if fam in todo_a:
            print(f"  [{fam:<6}] MISSING on every member -- nothing documents "
                  f"the neighbours that make each record checkable")
        else:
            print(f"  [{fam:<6}] present (check it is current: an a-file is "
                  f"free-form and is not regenerated)")

    if args.results:
        frontier_report(args.results, args.refresh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
