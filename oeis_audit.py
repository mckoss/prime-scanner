#!/usr/bin/env python3
"""Audit the gap / lonely / aloof sequence families for missing OEIS data.

The goal is completeness of the record, not new terms. Within a family every
sequence describes the same records -- the primes, their neighbours, the span,
the indices -- so they should all reach the same depth. Where one is shorter
than its siblings, its b-file is stale and can be extended from published data
alone. Where a family has no a-file, the bounding primes that make each record
checkable are not written down anywhere in a single place.

The report is a coverage table: one row per sequence, one column per place a
term of it can live -- the DATA section, the b-file, an a-file, our committed
snapshot under oeis/, and what a scan directory holds today.

    python3 oeis_audit.py                   # audit, using the cached copies
    python3 oeis_audit.py --refresh         # refetch from OEIS first
    python3 oeis_audit.py --results fresh   # add that run's column and frontier
"""

import argparse
import json
import os
import re
import subprocess
import sys

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oeis", "audit")
SNAPSHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oeis")

# sieve.c stores every value in an unsigned long, so nothing above this
# is reachable no matter how long the scan runs.
ULONG_MAX = 2 ** 64 - 1


def member(role, col=None, local=None, delta=0, needs_both=False):
    """One sequence within a family.

    col        which column of our 7-field record rows holds its terms:
               1 n  2 prime  3 value  4 gap_below  5 gap_above  6 prev  7 next.
               None means a scan cannot produce it at all.
    local      stem of the b-file snapshot we keep under oeis/, if we keep one.
    delta      terms this sequence has relative to the records themselves.
    needs_both a record needs BOTH neighbours to contribute a term, so the
               p = 2 record -- which has no lower neighbour -- does not count.
    """
    return {"role": role, "col": col, "local": local,
            "delta": delta, "needs_both": needs_both}


FAMILIES = {
    "gap": {
        "records": "maximal prime gaps",
        "extent": ("A002386", 0),
        "members": {
            "A002386": member("prime at the lower end", col=2, local="gap"),
            "A000101": member("prime at the upper end", col=7),
            "A005250": member("the gap size", col=3),
            "A005669": member("index of the lower prime (needs pi(p))"),
            "A107578": member("index of the upper prime (needs pi(p))"),
            "A053695": member("successive record-gap differences",
                              col=3, delta=-1),
        },
    },
    "lonely": {
        "records": "lonely primes -- record min(gap below, gap above)",
        "extent": ("A023186", 0),
        "members": {
            "A023186": member("the lonely prime", col=2, local="lonely"),
            "A023187": member("distance to the nearer neighbour", col=3),
        },
    },
    "aloof": {
        "records": "aloof primes -- record nextprime(p) - prevprime(p)",
        # A031134 holds the upper neighbour and runs one index below A096265,
        # which carries an extra a(1) = 2 having no lower neighbour.
        "extent": ("A031134", 1),
        "members": {
            "A096265": member("the aloof prime", col=2, local="aloof"),
            "A031133": member("the lower neighbour", col=6,
                              local="aloof-lower", needs_both=True),
            "A031134": member("the upper neighbour", col=7,
                              local="aloof-upper", needs_both=True),
            "A031132": member("the span between them", col=3,
                              local="aloof-span", needs_both=True),
            "A122412": member("index of the lower prime (needs pi(p))"),
            "A122413": member("index of the upper prime (needs pi(p))"),
        },
    },
    "equidistant": {
        "records": "equidistant primes -- record distance among the BALANCED "
                   "primes only",
        "extent": ("A058867", 0),
        "members": {
            "A058867": member("the balanced prime", col=2,
                              local="equidistant", needs_both=True),
            "A058868": member("the distance to each neighbour", col=3,
                              needs_both=True),
        },
    },
    "balanced": {
        "records": "balanced-lonely primes -- lonely records whose two "
                   "neighbours are equidistant",
        # Not in OEIS, so there are no members to lay out in a table. It is a
        # filter on the lonely records rather than a record sequence, which is
        # why a scan needs no threshold for it and cannot be behind on it.
        "proposed": "oeis/proposed/balanced-lonely-primes.md",
        "related": ("A058867",
                    "records among balanced primes -- contains every "
                    "balanced-lonely term, and many that are not lonely "
                    "records"),
        "members": {},
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


def plain(link):
    """An OEIS link line with its HTML stripped, for printing."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", link)).strip()


def snapshot_terms(stem):
    """Terms in our committed copy of a b-file, or None if we keep none."""
    if not stem:
        return None
    path = os.path.join(SNAPSHOTS, f"{stem}.txt")
    if not os.path.exists(path):
        return None
    return sum(1 for l in open(path, errors="replace")
               if l.strip() and l[0].isdigit())


def load_rows(results, fam):
    """The 7-field record rows of a scan's <fam>.txt."""
    if not results:
        return []
    path = os.path.join(results, f"{fam}.txt")
    if not os.path.exists(path):
        return []
    rows = []
    for line in open(path):
        if line.startswith("#") or not line.strip():
            continue
        f = line.split()
        if len(f) == 7:
            rows.append([int(x) for x in f])
    return rows


def scan_terms(rows, m):
    """How many terms of this sequence the scan's records already hold."""
    if m["col"] is None or not rows:
        return None
    n = sum(1 for f in rows
            if f[m["col"] - 1] and not (m["needs_both"] and f[5] == 0))
    return max(n + m["delta"], 0)


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


def bfile_terms_list(aid, refresh):
    path = os.path.join(CACHE, f"b{aid[1:]}.txt")
    if not fetch(f"https://oeis.org/{aid}/b{aid[1:]}.txt", path, refresh):
        return []
    return [int(l.split()[1]) for l in open(path, errors="replace")
            if l.strip() and l[0].isdigit()]


def heading(text):
    print(f"\n{text}")
    print("=" * len(text))


def num(v):
    return "-" if v is None else str(v)


def survey(refresh, results):
    """Read every family, and print one coverage table per family."""
    run = os.path.basename(os.path.normpath(results)) if results else None
    col5 = f"{run}/" if run else None

    heading("COVERAGE  --  where each sequence's terms are written down")
    print("""
A family is one set of records described from several angles, so all of its
members should reach the same depth. Where a column is short, terms the
siblings already carry have not been written down in that place.

  DATA    the terms on the sequence page -- saturates near 260 characters
  b-file  the full published list, and the deep one; "-" means none uploaded
  a-file  free-form table, the only place the bounding primes can be published
  oeis/   our committed snapshot of the b-file, what check_oeis.py diffs against""")
    if col5:
        print(f"  {col5:<7} terms this run's records could supply today")
    print("\n! marks a sequence behind its siblings, or with no b-file of its own.")

    families = {}
    for fam, info in FAMILIES.items():
        rows = load_rows(results, fam)
        if "proposed" in info:
            families[fam] = {"seqs": [], "deepest": 0, "rows": rows,
                             "info": info}
            proposed_block(fam, info, rows, run, refresh)
            continue
        seqs, deepest = [], 0
        for aid, m in info["members"].items():
            rec = entry(aid, refresh)
            if rec is None:
                seqs.append({"aid": aid, "m": m, "gone": True})
                continue
            n, synth = bfile_terms(aid, refresh)
            data_n = len(rec["data"].split(","))
            have_b = n is not None and not synth
            terms = n if have_b else data_n
            deepest = max(deepest, terms - m["delta"])
            seqs.append({"aid": aid, "m": m, "gone": False, "data": data_n,
                         "b": n if have_b else None, "terms": terms,
                         "af": afile(rec, aid), "local": snapshot_terms(m["local"]),
                         "scan": scan_terms(rows, m)})
        families[fam] = {"seqs": seqs, "deepest": deepest,
                         "rows": rows, "info": info}

        head = (f"  {'sequence':<9}{'DATA':>6}{'b-file':>8}{'a-file':>8}"
                f"{'oeis/':>7}" + (f"{col5:>8}" if col5 else "") + "  role")
        lines = []
        for s in seqs:
            if s["gone"]:
                lines.append(f"  {s['aid']:<9}  could not fetch")
                continue
            short = s["terms"] < deepest + s["m"]["delta"]
            mark = "!" if (short or s["b"] is None) else " "
            line = (f"{mark} {s['aid']:<9}{s['data']:>6}{num(s['b']):>8}"
                    f"{('yes' if s['af'] else '-'):>8}{num(s['local']):>7}")
            if col5:
                line += f"{num(s['scan']):>8}"
            lines.append(f"{line}  {s['m']['role']}")

        title = f"{fam} -- {info['records']}"
        rule = "-" * max(len(title), len(head), *(len(l) for l in lines))
        print(f"\n\n{title}")
        print(rule)
        print(head)
        print("\n".join(lines))
        print(rule)
        behind = [f"{s['aid']} -{deepest + s['m']['delta'] - s['terms']}"
                  for s in seqs if not s["gone"]
                  and s["terms"] < deepest + s["m"]["delta"]]
        tail = f"deepest member: {deepest} terms"
        if behind:
            tail += ".  behind: " + ", ".join(behind)
        print(f"  {tail}")
    return families


def proposed_block(fam, info, rows, run, refresh):
    """A family this repo tracks that OEIS does not carry yet."""
    title = f"{fam} -- {info['records']}"
    print(f"\n\n{title}")
    print("-" * len(title))
    print(f"  not in OEIS.  draft: {info['proposed']}")
    if rows:
        print(f"  {run}/ holds {len(rows)} terms, the last {rows[-1][1]:,} "
              f"at distance {rows[-1][2]}")
        print(f"  complete below the frontier: it filters the lonely records, "
              f"so no term can be missing")
    aid, why = info["related"]
    pub = bfile_terms_list(aid, refresh)
    if pub:
        print(f"  related: {aid}, {len(pub)} terms to {pub[-1]:.4e}")
        print(f"           {why}")


def todo(families):
    heading("TO FIX  --  none of this is a discovery claim")

    print("\nb-files, extendable from already-published data:")
    any_b = False
    for fam, f in families.items():
        for s in f["seqs"]:
            if s["gone"]:
                continue
            deep = f["deepest"] + s["m"]["delta"]
            if s["b"] is None:
                # OEIS synthesizes a b-file from DATA, and DATA holds ~260
                # characters. If every known term already fits there, an
                # uploaded b-file adds nothing until the sequence grows.
                why = ("no b-file uploaded, but DATA holds every known term "
                       "-- low priority")
                if s["terms"] < deep:
                    why = f"no b-file, and DATA is {deep - s['terms']} short"
            elif s["terms"] < deep:
                why = f"{deep - s['terms']} behind its siblings ({deep})"
            else:
                continue
            any_b = True
            print(f"  {s['aid']}  [{fam:<8}] {s['terms']:>3} terms -- {why}")
    if not any_b:
        print("  nothing -- every family member is at the same depth")

    print("\na-files, the one place a record's bounding primes can be published:")
    for fam, f in families.items():
        if "proposed" in f["info"]:
            print(f"  [{fam:<8}] not applicable until the sequence exists "
                  f"-- see {f['info']['proposed']}")
            continue
        have = [s for s in f["seqs"] if not s["gone"] and s["af"]]
        if have:
            print(f"  [{fam:<8}] present on " +
                  ", ".join(s["aid"] for s in have) +
                  " -- free-form, so check it is current")
            for s in have:
                text = plain(s["af"][0])
                if len(text) > 72:
                    text = text[:71].rsplit(" ", 1)[0] + " ..."
                print(f"           {s['aid']}: {text}")
        else:
            note = "nothing documents the neighbours that make a record checkable"
            print(f"  [{fam:<8}] MISSING on every member -- {note}")
            if f["rows"]:
                both = sum(1 for r in f["rows"] if r[5])
                print(f"           this run supplies both neighbours for "
                      f"{both} of its {len(f['rows'])} records  <-- BUILDABLE NOW")


def frontier_report(families, results, refresh):
    """Where this scan stands against each family's deepest published term."""
    fpath = os.path.join(results, "frontier.txt")
    if not os.path.exists(fpath):
        print(f"\n  no {fpath}; skipping the frontier comparison")
        return
    text = open(fpath).read()
    head = text.split()
    cov = {}
    scanned = [f for f in families if "extent" in families[f]["info"]]
    if head and head[0].isdigit():
        # Legacy single-number frontier.txt: it applies to every sequence that
        # has a records file; one with no file was never scanned at all.
        front = int(head[0])
        for fam in scanned:
            cov[fam] = front if os.path.exists(
                os.path.join(results, f"{fam}.txt")) else 0
    else:
        for line in text.splitlines():
            if not line.startswith("#") and len(line.split()) >= 2:
                cov[line.split()[0]] = int(line.split()[1])
        front = max(cov.values()) if cov else 0

    heading("FRONTIER vs PUBLISHED")
    if len(set(cov.values())) > 1:
        print(f"\n  {results}/frontier.txt -- the sequences are at different "
              f"frontiers, so each is measured against its own:")
        for fam in scanned:
            if fam in cov:
                print(f"      {fam:<12} {cov[fam]:>22,}")
    else:
        print(f"\n  {results}/frontier.txt = {front:,}  ({front:.4e})")
    print()
    print(f"  {'family':<12}{'ours':>5}   {'published to':<14}{'terms':>6}  "
          f"{'via':<9} what is left")
    for fam, f in families.items():
        if "extent" not in f["info"]:
            continue
        aid, off = f["info"]["extent"]
        pub = bfile_terms_list(aid, refresh)
        if not pub:
            continue
        extent, n_pub = pub[-1], len(pub) + off
        ours = len(f["rows"])
        # A kind still catching up is measured against its own bound, not the
        # run's frontier, which it has not reached yet.
        reach = cov.get(fam, front)
        if reach > extent:
            new = ours - n_pub
            left = (f"PAST it -- {new} term(s) beyond publication  <-- SUBMITTABLE"
                    if new > 0 else "past it, but no term beyond publication yet")
        elif extent > ULONG_MAX:
            left = f"unreachable -- past our 2^64 ceiling, {ULONG_MAX:.3e}"
        elif reach == 0:
            left = f"not scanned yet -- catch-up will cover [0, {front:.4e})"
        else:
            d = scan_days(reach, extent)
            when = f", ~{d:.1f} days at the measured rate" if d is not None else ""
            left = f"{extent / reach:.1f}x to go{when}"
        print(f"  {fam:<12}{ours:>5}   {extent:<14.4e}{n_pub:>6}  {aid:<9} {left}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
             formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true",
                    help="refetch entries and b-files from OEIS")
    ap.add_argument("--results", metavar="DIR",
                    help="a scan directory (e.g. fresh); adds a column for what "
                         "it could supply, and compares its frontier to each "
                         "family's published extent")
    args = ap.parse_args()

    families = survey(args.refresh, args.results)
    todo(families)
    if args.results:
        frontier_report(families, args.results, args.refresh)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
