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

It then looks past the families. Every A-number a member cites in its
cross-references or comments, and every entry OEIS search finds citing a
member, is ranked by how many terms it shares with our record primes. Those
that overlap are listed with a verdict from TRIAGED, or flagged as not yet
reviewed; dense sets of primes, which could never become a b-file from a scan,
are listed apart. Shared terms are what surfaced A087770, which only a
cross-reference on A096265 mentions.

    python3 oeis_audit.py                   # audit, using the cached copies
    python3 oeis_audit.py --refresh         # refetch from OEIS first
    python3 oeis_audit.py --results fresh   # add that run, and rewrite oeis/TODO.md

With --results it ends by turning all of that into CONTRIBUTIONS -- new terms,
completeness bounds, stale b-files and a-files, one-way cross-references,
sequences to review -- and writes them to oeis/TODO.md. That file is generated;
progress on an item goes in oeis/submissions.txt under the item's id.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oeis", "audit")
XREF_CACHE = os.path.join(CACHE, "xref")
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
    "pairwise": {
        "records": "pairwise lonely primes -- BOTH gaps beat the previous "
                   "term's, a chain rather than a maximum",
        "extent": ("A087770", 0),
        "members": {
            # 2 is a(1) with nothing below it, so it counts without a lower
            # neighbour; the gap columns carry the chain, the value column
            # only the nearer distance.
            "A087770": member("the pairwise lonely prime", col=2,
                              local="pairwise"),
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


# NEIGHBOURS: sequences outside the families that a family member cites, or
# that cite one. A087770 -- a stale second definition of lonely primes -- sat
# one cross-reference away from A096265 for this whole project, unnoticed,
# because the families above were written down by hand and nothing looked
# past them. The crawl looks; the dicts below record what a person concluded.

# A neighbour is shown when its DATA shares at least this many terms with our
# record primes. Terms at or below NEIGHBOUR_FLOOR are left out of the count,
# since 2, 3, 7, 23, 89 ... open half the prime sequences in OEIS.
NEIGHBOUR_OVERLAP = 3
NEIGHBOUR_FLOOR = 1000

# A record or first-occurrence sequence grows roughly geometrically, so each
# term adds a roughly constant number of digits: the families here run 0.05 to
# 0.5 digits per term, and the slowest first-occurrence table seen, A104138,
# 0.016. A set of primes defined by a property ("primes followed by a long
# gap") instead fills its b-file with thousands of terms that barely grow:
# A211073 has 10000 to 1.1e12, 0.0013 digits per term. Nobody would upload a
# b-file like that from a scan, so however much it overlaps our records such a
# sequence is not a candidate. The cut sits between the two groups, and a
# b-file of DENSE_MIN_TERMS or fewer is never called dense whatever its growth.
DENSE_DIGITS_PER_TERM = 0.005
DENSE_MIN_TERMS = 1000


def verdict(note, open_=False):
    """What a person concluded about one neighbour.

    open_  it still needs action -- a stale entry this scan could extend, or
           one not yet understood -- so the report keeps flagging it.
    """
    return {"note": note, "open": open_}


TRIAGED = {
    "A120384": verdict("record geometric mean of the two gaps. b-file 54 "
                       "terms to 31587561361; not yet examined in depth",
                       open_=True),
    "A102723": verdict("least prime with every integer within n composite; "
                       "its b-file ends at lonely(56), so lonely(57) extends "
                       "it"),
    "A023188": verdict("first occurrence of each nearest-prime distance, not "
                       "a record; b-file stops at 145628792921569"),
    "A120937": verdict("least prime with both gaps >= 2n: first occurrences, "
                       "not records; 35 terms to 2198981"),
    "A054342": verdict("first balanced prime at each distance, not a record; "
                       "b-file stops at 28219476363451"),
    "A046931": verdict("least prime whose neighbours are exactly 2n apart: "
                       "first occurrences, not records; stops at 929156727137"),
    "A000230": verdict("least prime starting a gap of exactly 2n: first "
                       "occurrences, not records"),
    "A001632": verdict("least prime ending a gap of exactly 2n: first "
                       "occurrences, not records"),
    "A100964": verdict("least prime starting a gap >= 2n: the gap records "
                       "re-indexed by size, not a new sequence"),
    "A051650": verdict("lonely NUMBERS: records over all integers, not primes"),
    "A051652": verdict("over all integers, not primes"),
    "A051728": verdict("over all integers, not primes"),
    "A051729": verdict("over all integers, not primes"),
    "A051730": verdict("distances for A051650, over all integers, not primes"),
    "A111870": verdict("record merit gap/log p. A merit record is also a gap "
                       "record, so it is a subset of A002386"),
    "A111943": verdict("record gap/log^2 p. Such a record is also a gap "
                       "record, so it is a subset of A002386"),
}

# Neighbours that are not candidates at all, and why. The density rule finds
# the dense ones on its own; they are written down here so the reason survives
# a cache that has not fetched their b-files yet.
NOT_TRACKED = {
    "A211073": "dense: every prime followed by a gap >= log^2(p)/2 -- "
               "10000 b-file terms to 1.1e12",
    "A079296": "dense: all primes, reordered by sqrt(q) - sqrt(p) -- "
               "10000 b-file terms",
    "A391411": "dense: first prime of each new pattern of two gaps -- "
               "7500 b-file terms to 4.2e9",
    "A182315": "a threshold set (gap > log^2 n), not a record; OEIS notes "
               "its terms come from A002386",
    "A124147": "a threshold set (p < sqrt(g) exp(sqrt(g))), not a record; "
               "all but 5 and 13 are in A002386",
}


def fetch(url, path, refresh):
    if os.path.exists(path) and not refresh:
        return True
    os.makedirs(os.path.dirname(path), exist_ok=True)
    r = subprocess.run(["curl", "-sSfL", "-A", "Mozilla/5.0", url, "-o", path],
                       stderr=subprocess.DEVNULL)
    # The crawl makes dozens of requests; space them out for OEIS's sake.
    time.sleep(0.4)
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
    # pgaps.est_seconds() already has contention in its rates; dividing by a
    # duty factor on top, as this once did, made every estimate ~1.8x long.
    return pg.est_seconds(lo, hi, 8) / 86400


def bfile_terms_list(aid, refresh):
    path = os.path.join(CACHE, f"b{aid[1:]}.txt")
    if not fetch(f"https://oeis.org/{aid}/b{aid[1:]}.txt", path, refresh):
        return []
    terms = []
    for l in open(path, errors="replace"):
        f = l.split()
        if len(f) >= 2 and f[0].isdigit() and re.fullmatch(r"-?\d+", f[1]):
            terms.append(int(f[1]))
    return terms


AREF = re.compile(r"\bA(\d{6})\b")
# "A051697-A051702" and "A023186-A023188" name every sequence in between.
AREF_RANGE = re.compile(r"\bA(\d{6})\s*-\s*A?(\d{6})\b")


def cited(rec):
    """A-numbers an entry names in its cross-references and comments."""
    ids = set()
    for key in ("xref", "comment"):
        for line in rec.get(key) or []:
            for a, b in AREF_RANGE.findall(line):
                if 0 < int(b) - int(a) <= 20:
                    ids.update(f"A{i:06d}" for i in range(int(a), int(b) + 1))
            ids.update("A" + a for a in AREF.findall(line))
    return ids


def citing(aid, refresh):
    """Every entry OEIS search finds mentioning aid, ten to a page.

    This is the direction a hand-kept family misses: A087770 cites A023186,
    but A023186 says nothing back.
    """
    found, start = [], 0
    while start < 1000:
        path = os.path.join(XREF_CACHE, f"in-{aid}-{start}.json")
        url = f"https://oeis.org/search?q={aid}&fmt=json&start={start}"
        if not fetch(url, path, refresh):
            break
        try:
            page = json.load(open(path))
        except Exception:
            break
        if isinstance(page, dict):
            page = page.get("results")
        if not page:
            break
        found.extend(page)
        if len(page) < 10:
            break
        start += 10
    return found


def record_primes(results):
    """Every prime our records name: the snapshots, plus a run's rows."""
    primes = set()
    for name in os.listdir(SNAPSHOTS):
        if name.endswith(".txt"):
            for l in open(os.path.join(SNAPSHOTS, name), errors="replace"):
                f = l.split()
                if len(f) == 2 and f[0].isdigit() and f[1].isdigit():
                    primes.add(int(f[1]))
    for fam in FAMILIES:
        for r in load_rows(results, fam):
            primes.update((r[1], r[5], r[6]))
    return {p for p in primes if p > NEIGHBOUR_FLOOR}


def density(terms):
    """Digits added per b-file term, or None if the b-file is too short to say."""
    if len(terms) <= DENSE_MIN_TERMS:
        return None
    top = max(abs(t) for t in terms)
    return len(str(top)) / len(terms)


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
                         "rec": rec,
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


def neighbours(results, refresh):
    """Related sequences outside the families, and what is known about each."""
    heading("NEIGHBOURS  --  related sequences outside the families")
    print(f"""
Every A-number a family member cites, and every entry that cites a member,
kept when its DATA shares at least {NEIGHBOUR_OVERLAP} terms above {NEIGHBOUR_FLOOR} with our record
primes. ! marks one nobody has reviewed, or one reviewed and still open.""")

    members = {aid for info in FAMILIES.values() for aid in info["members"]}
    recs, link = {}, {}
    for aid in sorted(members):
        rec = entry(aid, refresh)
        if rec is None:
            continue
        for other in cited(rec):
            link.setdefault(other, set()).add("out")
        for other in citing(aid, refresh):
            n = f"A{other['number']:06d}"
            recs[n] = other
            link.setdefault(n, set()).add("in")

    ours = record_primes(results)
    shown = []
    for aid in sorted(set(link) - members):
        # An outbound citation nobody else returned has to be fetched, but
        # only when its overlap could matter -- which needs its DATA anyway.
        rec = recs.get(aid) or entry(aid, refresh)
        if rec is None:
            continue
        data = {int(x) for x in rec.get("data", "").split(",")
                if re.fullmatch(r"\d+", x.strip())}
        overlap = len(data & ours)
        if overlap >= NEIGHBOUR_OVERLAP:
            shown.append((overlap, aid, rec))
    shown.sort(key=lambda s: (-s[0], s[1]))

    cov = read_frontier(results)[0] if results else {}
    front = min(cov.values()) if cov else None

    candidates, dense = [], []
    for overlap, aid, rec in shown:
        terms = bfile_terms_list(aid, refresh)
        d = density(terms)
        why = NOT_TRACKED.get(aid)
        if why is None and d is not None and d < DENSE_DIGITS_PER_TERM:
            why = (f"dense: {len(terms)} b-file terms to {max(terms):.2g}, "
                   f"{d:.4f} digits per term")
        if why is not None:
            dense.append((aid, why))
            continue
        candidates.append((overlap, aid, rec, terms))

    print(f"\n  {'overlap':>7}  {'sequence':<9}{'link':<8}{'terms':>6}  "
          f"{'last term':<22}name")
    for overlap, aid, rec, terms in candidates:
        t = TRIAGED.get(aid)
        mark = "!" if t is None or t["open"] else " "
        last = f"{terms[-1]:<22}" if terms else f"{'-':<22}"
        cites = "+".join(sorted(link[aid], reverse=True))
        name = rec["name"]
        if len(name) > 60:
            name = name[:59].rsplit(" ", 1)[0] + " ..."
        print(f"{mark} {overlap:>7}  {aid:<9}{cites:<8}{len(terms):>6}  "
              f"{last}{name}")
        note = "not reviewed" if t is None else (
            ("OPEN: " if t["open"] else "") + t["note"])
        if front is not None and terms:
            note += (" [last term below the run's frontier]"
                     if terms[-1] < front else " [last term past the frontier]")
        print(f"{'':>20}{note}")

    if dense:
        print("\n  not tracked -- not record sequences, so never a b-file from a scan:")
        for aid, why in dense:
            print(f"    {aid}  {why}")
    return candidates, dense


# ---------------------------------------------------------------------------
# CONTRIBUTIONS -- the live TODO
#
# Everything above describes the state of OEIS and of a scan. This turns it
# into things a person can submit, and writes them to oeis/TODO.md. The file
# is regenerated on every run with --results, so it is never edited by hand:
# progress on an item is recorded in oeis/submissions.txt under the item's id,
# and the next run files the item accordingly.
# ---------------------------------------------------------------------------

TODO_PATH = os.path.join(SNAPSHOTS, "TODO.md")
NOTES_PATH = os.path.join(SNAPSHOTS, "NOTES.md")
SUBMISSIONS = os.path.join(SNAPSHOTS, "submissions.txt")

# First line of a generated TODO.md. The hash covers everything after it, so
# a hand edit -- the one thing that would be lost on regeneration -- shows.
STAMP = "<!-- generated by oeis_audit.py; sha256 {} -->"
STAMP_RE = re.compile(r"<!-- generated by oeis_audit\.py; sha256 ([0-9a-f]{64}) -->")
ITEM_ID_RE = re.compile(r"`((?:terms|bound|new|b-file|a-file|xref|scan|review):"
                        r"[A-Za-z0-9:]+)`")
PROPOSED = os.path.join(SNAPSHOTS, "proposed")

# drafted: work exists but is not submitted -- the item stays in its group.
# submitted: waiting on an editor.  The rest close the item.
OPEN_STATUSES = ("drafted",)
REVIEW_STATUSES = ("submitted",)
CLOSED_STATUSES = ("approved", "declined", "skip")
STATUSES = OPEN_STATUSES + REVIEW_STATUSES + CLOSED_STATUSES

# Where a b-file for a sequence no scan can produce comes from. A member not
# listed here with col=None needs real compute to extend.
SOURCES = {
    "A005669": "the \"Index via primecount.exe\" column of Andersen and Luhn's "
               "table, https://www.pzktupel.de/RecordGaps/risinggap.php",
    "A107578": "A005669(n) + 1, which holds at every term both publish",
}

GROUPS = (
    ("terms", "New terms",
     "Terms past everything OEIS has, from an exhaustive scan. Submit only "
     "while check_oeis.py passes."),
    ("bound", "Completeness bounds",
     "The scan has passed every published term, so each entry can say where "
     "its search stands. Round the bound down; never claim ground not covered."),
    ("new", "New sequences", ""),
    ("bfile", "b-files from published or scanned data", ""),
    ("afile", "a-files: the bounding primes",
     "A b-file is `n a(n)` only. An a-file is free-form, and the one place a "
     "record's neighbouring primes can be published."),
    ("xref", "Cross-references", ""),
    ("scan", "Waiting on the scan",
     "Nothing to submit yet; listed so the wait is visible."),
    ("compute", "Needs compute beyond the scan", ""),
    ("review", "Related sequences to review",
     "Found by the neighbour crawl; see oeis/README.md for those already judged."),
    ("low", "Low priority",
     "DATA already holds every known term, so a b-file adds nothing until the "
     "sequence grows."),
)


def item(group, id_, title, *detail):
    return {"group": group, "id": id_, "title": title, "detail": list(detail)}


def read_submissions():
    """{item id: (status, date, note)} from oeis/submissions.txt."""
    status = {}
    if not os.path.exists(SUBMISSIONS):
        return status
    for n, line in enumerate(open(SUBMISSIONS), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        f = line.split(None, 3)
        if len(f) < 2 or f[1] not in STATUSES:
            print(f"  ! {SUBMISSIONS}:{n}: expected '<id> <status> [date] "
                  f"[note]' with status one of {', '.join(STATUSES)}")
            continue
        status[f[0]] = (f[1], f[2] if len(f) > 2 else "",
                        f[3] if len(f) > 3 else "")
    return status


def bound_text(x):
    """x rounded DOWN to two significant figures, in OEIS's 2.1*10^15 style.

    Rounding up would claim ground the scan has not covered.
    """
    if x < 100:
        return str(int(x))
    e = len(str(int(x))) - 1
    m = int(x) // 10 ** (e - 1)
    whole, tenth = divmod(m, 10)
    return f"{whole}*10^{e}" if tenth == 0 else f"{whole}.{tenth}*10^{e}"


def afile_url(link):
    m = re.search(r'href="(/A\d{6}/a\d{6}\.txt)"', link)
    return f"https://oeis.org{m.group(1)}" if m else None


def afile_coverage(url, fam_seqs, refresh):
    """(terms found, terms published) for the member the a-file tabulates.

    An a-file is free-form, but a table that is current contains the primes.
    Counting which published terms appear in it is enough to see it is stale.
    Which member it tabulates is not recorded anywhere -- Beveridge's gap
    table lists upper primes, not A002386's lower ones -- so take the member
    it matches best. Small terms are left out: 2, 3, 5 ... appear in any table.
    """
    path = os.path.join(CACHE, "afile", url.rsplit("/", 1)[1])
    if not fetch(url, path, refresh):
        return None
    tokens = set(re.findall(r"\d+", open(path, errors="replace").read()))
    best = None
    for s in fam_seqs:
        if s["gone"] or s["m"]["col"] not in (2, 6, 7):
            continue
        terms = [t for t in bfile_terms_list(s["aid"], refresh) if t > 1000]
        if terms:
            got = sum(1 for t in terms if str(t) in tokens)
            if best is None or got > best[0]:
                best = (got, len(terms))
    return best


def stamped(body):
    return STAMP.format(hashlib.sha256(body.encode()).hexdigest()) + "\n" + body


def overwrite_refusal(path):
    """Why path must not be overwritten, or None if it is safe to.

    Only a file this script wrote, and nobody has touched since, is safe:
    anything else holds words that exist nowhere else.
    """
    if not os.path.exists(path):
        return None
    first, _, rest = open(path).read().partition("\n")
    m = STAMP_RE.fullmatch(first.strip())
    if not m:
        return "it was not written by oeis_audit.py"
    if hashlib.sha256(rest.encode()).hexdigest() != m.group(1):
        return "it has been edited since it was generated"
    return None


def noted_ids():
    """Item ids that oeis/NOTES.md has something to say about."""
    if not os.path.exists(NOTES_PATH):
        return set()
    return set(ITEM_ID_RE.findall(open(NOTES_PATH).read()))


def check_passes(results):
    """Whether check_oeis.py passes on this run, and its last lines if not."""
    here = os.path.dirname(os.path.abspath(__file__))
    r = subprocess.run([sys.executable, os.path.join(here, "check_oeis.py"),
                        results], capture_output=True, text=True)
    bad = [l for l in r.stdout.splitlines() if l.lstrip().startswith("!!")]
    return r.returncode == 0, bad


def contributions(families, results, candidates, refresh, check):
    """Every contribution the current data supports, as items."""
    items = []
    run = os.path.basename(os.path.normpath(results))
    cov, _ = read_frontier(results)

    for fam, f in families.items():
        info, rows = f["info"], f["rows"]

        if "proposed" in info:
            lonely_front = cov.get("lonely", 0)
            items.append(item(
                "new", f"new:{fam}",
                f"New sequence: {info['records'].split(' -- ')[0]}",
                f"draft: `{os.path.relpath(info['proposed'], 'oeis')}`",
                f"{len(rows)} terms in `{run}/{fam}.txt`, complete below "
                f"{bound_text(lonely_front)} (it filters the lonely records)"))
            continue

        aid, off = info["extent"]
        pub = bfile_terms_list(aid, refresh)
        reach = cov.get(fam, 0)
        if pub:
            extent, n_pub = pub[-1], len(pub) + off
            primary = [s["aid"] for s in f["seqs"] if s["m"]["col"] == 2]
            if reach > extent:
                new = rows[n_pub:] if len(rows) > n_pub else []
                if new:
                    gate = ("check_oeis.py passes" if check[0] else
                            "**BLOCKED: check_oeis.py fails** -- fix first")
                    items.append(item(
                        "terms", f"terms:{fam}",
                        f"Extend {', '.join(primary)} past its {n_pub} "
                        f"published terms ({len(new)} new)",
                        *[f"{fam}({r[0]}) = {r[1]}  (gaps {r[3]}, {r[4]}; "
                          f"{r[5]} < p < {r[6]})" for r in new[:6]],
                        f"complete below {bound_text(reach)}; {gate}"))
                # Every member listing the primes themselves states the same
                # bound: the record prime, and its neighbours where published.
                targets = sorted({s["aid"] for s in f["seqs"]
                                  if s["m"]["col"] in (2, 6, 7)} | {aid})
                items.append(item(
                    "bound", f"bound:{fam}",
                    f"Comment on {', '.join(targets)}: no further terms below "
                    f"{bound_text(reach)}",
                    f"last published term {extent:,}; the scan covers "
                    f"{reach / extent:.1f}x past it"))
            elif extent <= ULONG_MAX:
                d = scan_days(max(reach, 1), extent)
                when = ("unknown time" if d is None else
                        f"~{d * 1440:.0f} min" if d * 24 < 1 else
                        f"~{d * 24:.0f} h" if d < 2 else f"~{d:.0f} days")
                items.append(item(
                    "scan", f"scan:{fam}",
                    f"{fam}: scan to {aid}'s last term {extent:,}",
                    f"frontier {reach:,}; {when} at 8 workers. {len(rows)} of "
                    f"{n_pub} published terms confirmed so far"))

        deep = f["deepest"]
        for s in f["seqs"]:
            if s["gone"]:
                continue
            m, want = s["m"], deep + s["m"]["delta"]
            ready = os.path.join(PROPOSED, f"b{s['aid'][1:]}.txt")
            if s["terms"] < want:
                detail = [f"{s['terms']} terms against {want} in its family"]
                if os.path.exists(ready):
                    detail.append(f"file ready: `proposed/{os.path.basename(ready)}`")
                if m["col"] is not None:
                    detail.append(f"source: sibling b-files, or `{run}/{fam}.txt` "
                                  f"column {m['col']}")
                    group = "bfile"
                elif s["aid"] in SOURCES:
                    detail.append(f"source: {SOURCES[s['aid']]}")
                    group = "bfile"
                else:
                    detail.append("source: needs pi(p), the prime's index -- "
                                  "e.g. primecount")
                    group = "compute"
                items.append(item(group, f"b-file:{s['aid']}",
                                  f"b-file for {s['aid']} ({m['role'].split(' (')[0]})", *detail))
            elif s["b"] is None:
                items.append(item("low", f"b-file:{s['aid']}",
                                  f"b-file for {s['aid']} ({m['role'].split(' (')[0]})",
                                  f"DATA holds all {s['terms']} terms"))

        with_af = [s for s in f["seqs"] if not s["gone"] and s["af"]]
        if not with_af:
            both = sum(1 for r in rows if r[5])
            items.append(item(
                "afile", f"a-file:{fam}",
                f"a-file for the {fam} records: prime, both neighbours, both gaps",
                f"none on any of {', '.join(s['aid'] for s in f['seqs'])}",
                f"`{run}/{fam}.txt` has both neighbours for {both} of "
                f"{len(rows)} records" if rows else
                "no records in this run yet"))
        seen = set()
        for s in with_af:
            url = afile_url(s["af"][0])
            if url is None or url in seen:
                continue
            seen.add(url)
            got = afile_coverage(url, f["seqs"], refresh)
            if got and got[0] < got[1]:
                items.append(item(
                    "afile", f"a-file:{s['aid']}",
                    f"Update the a-file on {s['aid']}",
                    f"{plain(s['af'][0])}",
                    f"holds {got[0]} of {got[1]} published terms"))

    items += cross_reference_items(families)

    for overlap, aid, rec, terms in candidates:
        t = TRIAGED.get(aid)
        if t and t["open"]:
            items.append(item("review", f"review:{aid}",
                              f"Decide whether to track {aid}", t["note"]))
    unreviewed = [aid for _, aid, _, _ in candidates if aid not in TRIAGED]
    if unreviewed:
        items.append(item("review", "review:neighbours",
                          f"Review {len(unreviewed)} related sequences nobody "
                          f"has judged",
                          ", ".join(unreviewed),
                          "record each verdict in TRIAGED or NOT_TRACKED in "
                          "oeis_audit.py"))
    return items


def cross_reference_items(families):
    """Links that run one way only, and family members that never meet.

    A087770 cites A023186 but A023186 does not cite it back, which is how it
    stayed unnoticed. Within a family, a member that neither cites nor is
    cited by the family's prime sequence can only be found by accident.
    """
    items, recs = [], {}
    for f in families.values():
        for s in f["seqs"]:
            if not s["gone"]:
                recs[s["aid"]] = s["rec"]
    cites = {aid: cited(rec) for aid, rec in recs.items()}
    for x in sorted(recs):
        for y in sorted(recs):
            if x != y and x in cites[y] and y not in cites[x]:
                items.append(item("xref", f"xref:{x}:{y}",
                                  f"Add {y} to {x}'s cross-references",
                                  f"{y} already cites {x}"))
    for fam, f in families.items():
        primary = [s["aid"] for s in f["seqs"] if s["m"]["col"] == 2]
        for p in primary:
            for s in f["seqs"]:
                a = s["aid"]
                if a == p or a not in recs or p not in recs:
                    continue
                if a not in cites[p] and p not in cites[a]:
                    items.append(item("xref", f"xref:{p}:{a}",
                                      f"Cross-reference {p} and {a}",
                                      f"both describe the {fam} records; "
                                      f"neither cites the other"))
    return items


def render_todo(items, status, results, check):
    """oeis/TODO.md, from the items and the recorded statuses."""
    run = os.path.basename(os.path.normpath(results))
    notes = noted_ids()
    out = [
        "# OEIS contributions",
        "",
        f"> **GENERATED FILE -- DO NOT EDIT.** `python3 oeis_audit.py --results "
        f"{run}` rewrites it on every run, and refuses to if it has been "
        f"edited. Record progress in [`submissions.txt`](submissions.txt); "
        f"keep notes in [`NOTES.md`](NOTES.md), tagged with the item's id.",
        "",
        f"Generated {time.strftime('%Y-%m-%d')} from `{run}/`, the cached OEIS "
        f"entries, and [`submissions.txt`](submissions.txt).",
        "",
        "- **check_oeis.py:** " + ("all checks pass" if check[0] else
                                   "**FAILING** -- nothing below is safe to "
                                   "submit until it passes"),
        "- **Progress:** add `<id> <status> [date] [note]` to "
        "`submissions.txt`, where status is one of "
        + ", ".join(f"`{s}`" for s in STATUSES) + ".",
        "",
    ]
    for line in check[1][:5]:
        out.append(f"    {line.strip()}")
    if check[1]:
        out.append("")

    ids = {it["id"] for it in items}
    for key, title, blurb in GROUPS:
        group = [it for it in items if it["group"] == key
                 and status.get(it["id"], ("",))[0] not in
                 REVIEW_STATUSES + CLOSED_STATUSES]
        if not group:
            continue
        out += [f"## {title}", ""]
        if blurb:
            out += [blurb, ""]
        for it in group:
            st = status.get(it["id"])
            mark = f" _({st[0]} {st[1]})_" if st else ""
            out.append(f"- [ ] **{it['title']}**{mark}  ")
            out.append(f"  `{it['id']}`")
            for d in it["detail"]:
                out.append(f"  - {d}")
            if it["id"] in notes:
                out.append(f"  - notes: [`NOTES.md`](NOTES.md), under "
                           f"`{it['id']}`")
        out.append("")

    for label, which in (("In review", REVIEW_STATUSES),
                         ("Closed", CLOSED_STATUSES)):
        rows = [(i, st) for i, st in sorted(status.items()) if st[0] in which]
        if rows:
            out += [f"## {label}", ""]
            for i, (st, date, note) in rows:
                gone = "" if i in ids else " -- no longer generated"
                out.append(f"- `{i}` {st} {date} {note}{gone}".rstrip())
            out.append("")

    stale = [i for i, st in sorted(status.items())
             if i not in ids and st[0] in OPEN_STATUSES]
    if stale:
        out += ["## Recorded but no longer generated", "",
                "The data no longer supports these; close them in "
                "`submissions.txt` if they are done.", ""]
        out += [f"- `{i}` {status[i][0]} {status[i][1]}" for i in stale]
        out.append("")

    out += [
        "## Notes",
        "",
        "- Submissions go draft -> proposed -> editor review -> approval; "
        "days to weeks.",
        "- OEIS is CC BY-SA 4.0; the b-files in this directory are committed "
        "with attribution.",
        "- Terms are written `gap(n)`, `lonely(n)`, `aloof(n)`, "
        "`equidistant(n)`, `pairwise(n)` -- never `a(n)`, since several "
        "sequences are in play.",
        "",
    ]
    return "\n".join(out)


def read_frontier(results):
    """({sequence: frontier}, highest) from a run's frontier.txt, or ({}, 0)."""
    fpath = os.path.join(results, "frontier.txt")
    if not os.path.exists(fpath):
        return {}, 0
    text = open(fpath).read()
    head = text.split()
    cov = {}
    scanned = [f for f in FAMILIES if "extent" in FAMILIES[f]]
    if head and head[0].isdigit():
        # Legacy single-number frontier.txt: it applies to every sequence that
        # has a records file; one with no file was never scanned at all.
        front = int(head[0])
        for fam in scanned:
            cov[fam] = front if os.path.exists(
                os.path.join(results, f"{fam}.txt")) else 0
        return cov, front
    for line in text.splitlines():
        if not line.startswith("#") and len(line.split()) >= 2:
            cov[line.split()[0]] = int(line.split()[1])
    # A family with no line was added after the run last wrote this file, so
    # it has not been scanned at all -- not scanned to the run's frontier.
    for fam in scanned:
        cov.setdefault(fam, 0)
    return cov, (max(cov.values()) if cov else 0)


def frontier_report(families, results, refresh):
    """Where this scan stands against each family's deepest published term."""
    fpath = os.path.join(results, "frontier.txt")
    if not os.path.exists(fpath):
        print(f"\n  no {fpath}; skipping the frontier comparison")
        return
    cov, front = read_frontier(results)
    scanned = [f for f in families if "extent" in families[f]["info"]]

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
                         "it could supply, compares its frontier to each "
                         "family's published extent, and regenerates "
                         "oeis/TODO.md")
    ap.add_argument("--no-write", action="store_true",
                    help="with --results, print the contributions but leave "
                         "oeis/TODO.md alone")
    ap.add_argument("--force-write", action="store_true",
                    help="overwrite oeis/TODO.md even if it was edited by hand "
                         "-- whatever was edited is lost")
    ap.add_argument("--no-check", action="store_true",
                    help="skip running check_oeis.py (the TODO then says so)")
    args = ap.parse_args()

    families = survey(args.refresh, args.results)
    candidates, _ = neighbours(args.results, args.refresh)
    if not args.results:
        print("\n  add --results <dir> for the frontier comparison and the "
              "live TODO\n")
        return 0
    frontier_report(families, args.results, args.refresh)

    if args.no_check:
        check = (False, ["check_oeis.py was not run (--no-check)"])
    else:
        check = check_passes(args.results)
    items = contributions(families, args.results, candidates, args.refresh,
                          check)
    text = render_todo(items, read_submissions(), args.results, check)

    heading("CONTRIBUTIONS")
    print()
    print(text.split("## Notes")[0].rstrip())
    if not args.no_write:
        why = overwrite_refusal(TODO_PATH)
        if why and not args.force_write:
            print(f"\n  !! NOT writing {os.path.relpath(TODO_PATH)}: {why}.\n"
                  f"     Move anything worth keeping to NOTES.md or "
                  f"submissions.txt,\n     then rerun with --force-write.")
            return 1
        open(TODO_PATH, "w").write(stamped(text))
        print(f"\n  wrote {os.path.relpath(TODO_PATH)}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
