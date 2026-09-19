#!/usr/bin/env python3
"""Check what oeis/submit/ holds before any of it is uploaded to OEIS.

An uploaded b-file that breaks the spec is rejected by the server, and an
a-file with a stray non-ASCII byte is worse -- it is accepted and then wrong.
Neither shows up in the generator's own output, so it is checked here.

    python3 test_submit.py

There is no YAML parser in this environment and the repo has no dependencies,
so edits.yaml is checked structurally rather than parsed. The checks cover the
shapes the generator actually emits: a colon inside a flow sequence, or an
unquoted scalar carrying a comma, would both change what a real parser reads.
"""

import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUBMIT = os.path.join(HERE, "oeis", "submit")

fails = []


def check(cond, what):
    if not cond:
        fails.append(what)
    return cond


def read(name):
    return open(os.path.join(SUBMIT, name), "rb").read()


# --- every generated file is plain ASCII with LF endings -------------------
# The b-file spec is explicit: ASCII, no BOM, LF, no tabs, final newline.
# a-files are free-form but go in the same archive, so they are held to it too.
# Files whose layout belongs to their original author: we change the data and
# leave the presentation alone. They still have to be clean ASCII.
INHERITED = {"a005250.txt"}

for name in sorted(os.listdir(SUBMIT)):
    if not re.fullmatch(r"[ab]\d{6}\.txt", name):
        continue
    raw = read(name)
    check(not raw.startswith(b"\xef\xbb\xbf"), f"{name}: has a UTF-8 BOM")
    check(all(b < 128 for b in raw), f"{name}: has non-ASCII bytes")
    check(b"\r" not in raw, f"{name}: has CR (not LF-only)")
    check(b"\t" not in raw, f"{name}: has tabs")
    check(raw.endswith(b"\n"), f"{name}: no final newline")
    text = raw.decode()
    # ~~~~ only expands in the edit form; an uploaded file would show it raw
    check("~~~~" not in text, f"{name}: has a literal ~~~~ (form-only markup)")
    check("Mike Koss" in text, f"{name}: does not name the contributor")
    if name in INHERITED:
        continue
    check(b"\n\n" not in raw, f"{name}: has a blank line")
    head = [l for l in text.splitlines() if l.startswith("#")]
    body = [l for l in text.splitlines() if l and not l.startswith("#")]
    check(head, f"{name}: no comment header at all")
    joined = "\n".join(head)
    check("github.com/mckoss/prime-scanner" in joined,
          f"{name}: header has no source URL")
    check("CC BY-SA" in joined, f"{name}: header has no licence line")

    if name.startswith("b"):
        ns = []
        for l in body:
            f = l.split()
            check(len(f) == 2, f"{name}: '{l[:40]}' is not `n a(n)`")
            if len(f) == 2 and f[0].lstrip("-").isdigit():
                ns.append(int(f[0]))
        check(ns == list(range(ns[0], ns[0] + len(ns))),
              f"{name}: indices are not consecutive from {ns[0] if ns else '?'}")
    else:
        # an a-file's columns are fixed-width; every data row has the same count
        counts = {len(l.split()) for l in body}
        check(len(counts) == 1,
              f"{name}: rows have differing column counts {sorted(counts)}")

# --- the b-files agree with what OEIS already publishes --------------------
CACHE = os.path.join(HERE, "oeis", "audit")


def published(stem):
    p = os.path.join(CACHE, stem)
    if not os.path.exists(p):
        return {}
    out = {}
    for l in open(p, errors="replace"):
        f = l.split()
        if len(f) >= 2 and f[0].lstrip("-").isdigit() and \
                re.fullmatch(r"-?\d+", f[1]):
            out[int(f[0])] = int(f[1])
    return out


for name in sorted(os.listdir(SUBMIT)):
    if not re.fullmatch(r"b\d{6}\.txt", name):
        continue
    ours = {}
    for l in read(name).decode().splitlines():
        if l.startswith("#") or not l.strip():
            continue
        f = l.split()
        ours[int(f[0])] = int(f[1])
    theirs = published(name)
    if not theirs:
        continue
    bad = [n for n in theirs if n in ours and ours[n] != theirs[n]]
    check(not bad,
          f"{name}: disagrees with the published b-file at n={bad[:5]}")
    check(len(ours) >= len(theirs),
          f"{name}: {len(ours)} terms, fewer than the published {len(theirs)}")

# --- edits.yaml ------------------------------------------------------------
y = open(os.path.join(SUBMIT, "edits.yaml")).read()
lines = y.splitlines()

check(y.endswith("\n"), "edits.yaml: no final newline")
check(all(ord(c) < 128 for c in y), "edits.yaml: has non-ASCII")
check("\t" not in y, "edits.yaml: has tabs")

block_indent = None
for i, l in enumerate(lines, 1):
    indent = len(l) - len(l.lstrip())
    if block_indent is not None:
        if l.strip() and indent > block_indent:
            continue                      # inside a folded/literal scalar
        block_indent = None
    if l.lstrip().startswith("#") or not l.strip():
        continue
    body = l.split(" #", 1)[0]
    # `key: >-` and a bare `- >-` list item both open a block scalar
    if re.search(r"(:|^\s*-)\s*[>|]-?\s*$", body):
        block_indent = indent
        continue
    for m in re.finditer(r"\[([^\]]*)\]", body):
        inner = m.group(1)
        # a bare colon inside a flow sequence turns an item into a mapping
        unquoted = re.sub(r'"[^"]*"', "", inner)
        check(":" not in unquoted,
              f"edits.yaml:{i}: unquoted colon in a flow sequence: {inner[:50]}")
    m = re.match(r"^\s*-?\s*[A-Za-z_][A-Za-z_0-9]*:\s+(\S.*)$", body)
    if m and m.group(1)[0] not in "\"'>|[":
        check("," not in m.group(1),
              f"edits.yaml:{i}: unquoted scalar with a comma: {l.strip()[:60]}")

# Generated files date the DATA, not the run: a wall-clock date would rewrite
# every file on every run and would misdate the terms to anyone reading them
# on OEIS. Every date in a generated header must be one of the two provenance
# dates -- when the scan last advanced, or when the table was retrieved.
as_of = re.search(r"^data_as_of: (\d{4}-\d{2}-\d{2})", y, re.M)
check(as_of, "edits.yaml: no data_as_of")
if as_of:
    idx = os.path.join(HERE, "oeis", "andersen-luhn-index.txt")
    retrieved = re.search(r"retrieved (\d{4}-\d{2}-\d{2})",
                          open(idx).read()) if os.path.exists(idx) else None
    allowed = {as_of.group(1)} | ({retrieved.group(1)} if retrieved else set())
    for name in sorted(os.listdir(SUBMIT)):
        if not re.fullmatch(r"[ab]\d{6}\.txt", name):
            continue
        text = read(name).decode()
        for d in set(re.findall(r"\d{4}-\d{2}-\d{2}", text)):
            check(d in allowed,
                  f"{name}: dated {d}, which is neither the scan date "
                  f"{as_of.group(1)} nor a table retrieval date")

# Each a-file states the bound its own family reached. The pairwise scan
# trails the others, so a shared "searched all below" would be a false claim.
bounds = {}
for name in sorted(os.listdir(SUBMIT)):
    if not re.fullmatch(r"a\d{6}\.txt", name) or name in INHERITED:
        continue
    m = re.search(r"Searched all below ([\d,]+)", read(name).decode())
    check(m, f"{name}: header states no searched bound")
    if m:
        bounds[name] = int(m.group(1).replace(",", ""))
fr = os.path.join(HERE, "fresh", "frontier.txt")
if os.path.exists(fr) and bounds:
    per = {}
    for l in open(fr):
        f = l.split()
        if len(f) == 2 and f[1].isdigit():
            per[f[0]] = int(f[1])
    if "pairwise" in per and "a087770.txt" in bounds:
        check(bounds["a087770.txt"] == per["pairwise"],
              f"a087770.txt claims {bounds['a087770.txt']}, but the pairwise "
              f"frontier is {per['pairwise']}")

check(re.search(r"^check_oeis: pass$", y, re.M),
      "edits.yaml: check_oeis is not passing")
check(re.search(r"^  signature: \"~~~~\"", y, re.M),
      "edits.yaml: signature is not the OEIS four-tilde shortcut")

# Every A-number a draft targets must appear in `order`, and vice versa.
order = re.search(r"^order: \[(.*)\]$", y, re.M)
check(order, "edits.yaml: no order list")
if order:
    listed = order.group(1).replace(" ", "").split(",")
    aids = re.findall(r"^- aid:\s+(A\d{6})$", y, re.M)
    check(listed == sorted(aids),
          f"edits.yaml: order {listed} != drafts {sorted(aids)}")

# --- the manifest describes what is actually there -------------------------
man = {}
for l in open(os.path.join(SUBMIT, "MANIFEST.txt")):
    if l.startswith("#") or not l.strip():
        continue
    h, n = l.split()
    man[n] = h
for name, want in man.items():
    got = hashlib.sha256(read(name)).hexdigest()[:16]
    check(got == want, f"MANIFEST.txt: {name} is {got}, listed as {want}")
on_disk = {f for f in os.listdir(SUBMIT) if f != "MANIFEST.txt"}
check(on_disk == set(man),
      f"MANIFEST.txt: covers {sorted(set(man))}, directory has "
      f"{sorted(on_disk)}")

# --- uploads named in edits.yaml exist -------------------------------------
for path in re.findall(r"^    path: (\S+)$", y, re.M):
    check(os.path.exists(os.path.join(HERE, path)), f"edits.yaml: missing {path}")

n = len([f for f in os.listdir(SUBMIT)])
if fails:
    print(f"{len(fails)} problem(s) in {SUBMIT}:")
    for f in fails:
        print(f"  !! {f}")
    sys.exit(1)
print(f"oeis/submit/: {n} files, all checks pass")
