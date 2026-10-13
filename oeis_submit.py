#!/usr/bin/env python3
"""Turn the audit's contributions into a reviewable submission script.

oeis_audit.py decides WHAT can be contributed. This turns that into the
things you actually hand to OEIS:

    oeis/submit/edits.yaml     one entry per draft, in schedule order
    oeis/submit/b*.txt         b-files, ready to upload
    oeis/submit/a*.txt         a-files, ready to upload
    oeis/submit/index.html     the numbered worklist, with the bookmarklet
    oeis/submit/panel.html     the status panel, shown beside the edit form
    oeis/submit/fill.js        the shim the bookmarklet injects
    oeis/submit/payload.js     the drafts and the file contents, as JS

A draft is per SEQUENCE, not per contribution: every change to A096265 --
its b-file, its a-file, its cross-references -- is one OEIS
submission, so they are grouped that way here.

Nothing in this module talks to oeis.org. The generated files are read by a
browser you drive yourself; the tool fills forms and never submits one.
"""

import hashlib
import html
import json
import os
import re
import time

# Who the generated files credit, and how signed fields are written.
#
# `signature` is OEIS's four-tilde shortcut: the edit form's processor expands
# it to the contributor's linked name and the date AT SUBMISSION TIME. That
# matters because a draft sits for days before it is proposed, so a literal
# date baked in here would be wrong by the time an editor reads it. The
# shortcut only works in form fields -- uploaded b-files and a-files never
# pass through the form processor, so their headers carry a literal name and
# the date the data was generated, which is what a file header should say.
ATTRIB = {
    "name": "Mike Koss",
    "source": "https://github.com/mckoss/prime-scanner",
    "signature": "~~~~",
    "license": "OEIS data CC BY-SA 4.0",
}

EDIT_URL = "https://oeis.org/edit?seq={}"
NEW_URL = "https://oeis.org/edit"
PORT = 8017


# ---------------------------------------------------------------------------
# The edit vocabulary
#
# Each op names a field of the OEIS edit form. The form's editable widgets are
# contenteditable divs with id "edit_<Field>", copied into hidden inputs by its
# own copyin() on submit, so these names are the form's, not the %-codes that
# appear in the published entry. The %-code is carried along for readers.
# ---------------------------------------------------------------------------

CODE = {"Name": "%N", "Data": "%S", "Offset": "%O", "Comment": "%C",
        "Link": "%H", "Xref": "%Y", "Keyword": "%K", "Author": "%A",
        "Ext": "%E", "Example": "%e", "Ref": "%D"}


def op(field, action, **kw):
    d = {"field": field, "code": CODE.get(field, ""), "action": action}
    d.update(kw)
    return d


def signed(text):
    """A single-paragraph comment, signed the way the Style Sheet asks.

    Multi-paragraph contributions take `From ~~~~: (Start)` ... `(End)`
    instead of a trailing signature -- an editor corrected exactly this on
    A023186 twice before it landed right, so it is worth getting right here.
    """
    text = text.strip()
    if "\n" in text:
        return f"From {ATTRIB['signature']}: (Start)\n{text}\n(End)"
    return f"{text} - {ATTRIB['signature']}"


# ---------------------------------------------------------------------------
# Generated files: b-files and a-files
# ---------------------------------------------------------------------------

def header(lines):
    return "".join(f"# {l}\n".replace("# \n", "#\n") for l in lines)


def attribution_lines(byline, bound=None, checked=None):
    """The credit and provenance block every generated file carries.

    `byline` dates the DATA, not the run: a file regenerated today from a scan
    that last advanced last week should say last week, or it misdates itself to
    whoever reads it on OEIS -- and re-running the generator would rewrite every
    file for no reason.

    `bound` is the family's own frontier, never the deepest in the run. The
    pairwise scan trails the others by a factor of three, so "searched all
    below" the run maximum would be a false claim on an A087770 file.
    """
    out = [byline]
    if bound:
        out.append(f"Searched all below {bound:,}: every record up to that")
        out.append("bound is present, and there is no further one below it.")
    if checked:
        out.append(checked)
    out.append(f"Source: {ATTRIB['source']}")
    out.append(ATTRIB["license"])
    return out


def scan_byline(date):
    return f"{ATTRIB['name']}. Data as of {date}, when the scan last advanced."


def table_byline(date):
    return (f"{ATTRIB['name']}. From Andersen and Luhn's table, "
            f"retrieved {date}.")


def bfile(aid, pairs, note, byline, bound=None, checked=None):
    """`n a(n)`, with a comment header naming where the terms came from.

    The b-file spec allows comment lines before the data. Published b-files
    use them for exactly this -- b096265.txt opens "computed by Ken Takusagawa
    ... and Hugo Pfoertner" -- so prior contributors keep their credit.
    """
    out = [f"{aid}, {len(pairs)} terms.", ""]
    out += note if isinstance(note, list) else [note]
    out += [""] + attribution_lines(byline, bound, checked)
    body = "".join(f"{n} {v}\n" for n, v in pairs)
    return header(out) + body


# One a-file per family. A b-file is `n a(n)` and nothing else, so the
# bounding primes -- the data that makes a record checkable without rerunning
# a scan -- have nowhere else to live. Columns map to A-numbers wherever one
# exists; the gaps are p - pp and np - p, so publishing both neighbours
# publishes both gaps. Beveridge's a005250.txt does the same and says so.
AFILE = {
    "lonely": {
        "aid": "A023186",
        "title": "lonely prime records with bounding primes",
        "cols": [("n", "index", "", lambda r: r[0]),
                 ("p", "the lonely prime", "A023186", lambda r: r[1]),
                 ("d", "min(p-pp, np-p), the record", "A023187",
                  lambda r: r[2]),
                 ("pp", "previous prime", "", lambda r: r[5] or None),
                 ("np", "next prime", "", lambda r: r[6])],
    },
    "aloof": {
        "aid": "A096265",
        "title": "aloof prime records with bounding primes",
        "cols": [("n", "index", "", lambda r: r[0]),
                 ("p", "the aloof prime", "A096265", lambda r: r[1]),
                 ("span", "np - pp, the record", "A031132",
                  lambda r: r[2] if r[5] else None),
                 ("pp", "previous prime", "A031133", lambda r: r[5] or None),
                 ("np", "next prime", "A031134", lambda r: r[6])],
    },
    "equidistant": {
        "aid": "A058867",
        "title": "equidistant prime records with bounding primes",
        "cols": [("n", "index", "", lambda r: r[0]),
                 ("p", "the balanced prime", "A058867", lambda r: r[1]),
                 ("d", "p - pp = np - p, the record", "A058868",
                  lambda r: r[2]),
                 ("pp", "previous prime", "", lambda r: r[5] or None),
                 ("np", "next prime", "", lambda r: r[6])],
    },
    "pairwise": {
        "aid": "A087770",
        "title": "pairwise lonely prime records with bounding primes",
        # Both gaps carry the record here -- each beats the previous term's --
        # so neither alone is the value, and both are named outright.
        "cols": [("n", "index", "", lambda r: r[0]),
                 ("p", "the pairwise lonely prime", "A087770",
                  lambda r: r[1]),
                 ("gb", "p - pp", "", lambda r: r[3] if r[5] else None),
                 ("ga", "np - p", "", lambda r: r[4]),
                 ("pp", "previous prime", "", lambda r: r[5] or None),
                 ("np", "next prime", "", lambda r: r[6])],
    },
}


def afile(fam, rows, byline, bound, checked):
    spec = AFILE[fam]
    cols = spec["cols"]
    # p = 2 is a term but has no previous prime, so the cells that need one
    # -- pp, and a span or lower gap measured from it -- read "-" rather than
    # dropping the row, which keeps the a-file aligned with the b-file.
    key = [f"{c[0]:<5}{c[1]}" + (f" ({c[2]})" if c[2] else "") for c in cols]
    body = [["-" if (v := c[3](r)) is None else str(v) for c in cols]
            for r in rows]
    if any("-" in b for b in body):
        key.append("-    none: p = 2 has no previous prime")
    head = [f"a{spec['aid'][1:]}.txt -- {spec['title']}", ""] + key + [""]
    head += attribution_lines(byline, bound, checked) + [""]
    w = [max(len(c[0]), max((len(b[i]) for b in body), default=0))
         for i, c in enumerate(cols)]
    out = header(head)
    out += "# " + "  ".join(f"{c[0]:>{w[i]}}" for i, c in enumerate(cols)) + "\n"
    for b in body:
        out += "  " + "  ".join(f"{v:>{w[i]}}" for i, v in enumerate(b)) + "\n"
    return out


# ---------------------------------------------------------------------------
# The Andersen-Luhn index table
# ---------------------------------------------------------------------------

def index_table(path):
    """{n: (gap, prime, index)} from the committed copy, or {}.

    A005669 and A107578 are indices pi(p), which no scan of ours produces.
    The table is the only published source; it is committed rather than
    refetched so the data is versioned and reviewable in a diff.
    """
    if not os.path.exists(path):
        return {}
    out = {}
    for line in open(path):
        if line.lstrip().startswith("#") or not line.strip():
            continue
        f = line.split()
        if len(f) == 4:
            out[int(f[0])] = (int(f[1]), int(f[2]), int(f[3]))
    return out


# ---------------------------------------------------------------------------
# edits.yaml
# ---------------------------------------------------------------------------

def q(s):
    """A YAML scalar: quoted when it could be read as anything else."""
    s = str(s)
    if s == "":
        return '""'
    if re.fullmatch(r"[A-Za-z0-9 ./_+*^=-]+", s) and not s[0].isdigit() \
            and not s.endswith(":"):
        return s
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def block(text, indent):
    """A folded scalar. Long prose stays readable in the file."""
    pad = " " * indent
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > 74:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    return ">-\n" + "".join(f"{pad}{l}\n" for l in lines).rstrip("\n")


def render_yaml(drafts, new_seqs, other, meta):
    o = [f"# oeis/submit/edits.yaml -- GENERATED by `oeis_audit.py --results "
         f"{meta['run']}`; do not edit.",
         "# One entry per OEIS draft. Only fields that CHANGE appear.",
         "# Record progress in oeis/submissions.txt, keyed by `items`.",
         "",
         f"data_as_of: {meta['date']}"
         "          # the date the scan last advanced, not the run date",
         f"run:        {meta['run']}",
         f"frontier:   {meta['frontier']}",
         f"check_oeis: {'pass' if meta['check'] else 'NOT PASSING'}"
         + ("" if meta["check"] else
            f"   # {meta.get('check_note') or 'nothing here is safe to submit'}"),
         "",
         "attribution:",
         f"  name:      {q(ATTRIB['name'])}",
         f'  source:    "{ATTRIB["source"]}"',
         f"  signature: {q(ATTRIB['signature'])}"
         "          # OEIS expands this to name + date on submit",
         f"  license:   {q(ATTRIB['license'])}",
         ""]

    if other.get("draft_limit"):
        opened = other.get("open_drafts") or []
        o.append(f"open_drafts: [{', '.join(opened)}]"
                 f"          # OEIS allows {other['draft_limit']} at a time")
        o.append("")
    if drafts:
        o.append("order: [" + ", ".join(d["aid"] for d in drafts) + "]")
        o += ["", "drafts:", ""]
    for d in drafts:
        o.append(f"- aid:   {d['aid']}")
        o.append(f"  role:  {q(d['role'])}")
        o.append(f'  url:   "{d["url"]}"')
        o.append("  items: ["
                 + ", ".join('"%s"' % i for i in d["items"]) + "]")
        if d.get("status"):
            o.append(f"  status: {d['status']}")
        if d.get("slot"):
            o.append(f"  slot:  {d['slot']}"
                     + ("          # no free OEIS draft slot"
                        if d["slot"] == "waits" else ""))
        if d.get("blocked_on"):
            o.append("  blocked_on:")
            o += [f"  - {q(b)}" for b in d["blocked_on"]]
        if d.get("notes"):
            o.append("  notes: true")
        o.append(f"  summary: {block(d['summary'], 4)}")
        if d.get("to_editors"):
            o.append(f"  to_editors: {block(d['to_editors'], 4)}")
        if d.get("uploads"):
            o.append("  uploads:")
        for u in d.get("uploads") or []:
            o += [f"  - kind: {u['kind']}",
                  f"    path: {u['path']}",
                  f"    rows: {u['rows']}",
                  f"    from: {q(u['from'])}"]
            if u.get("desc"):
                o.append(f"    link: {q(u['desc'])}")
        if d["edits"]:
            o.append("  edits:")
        for e in d["edits"]:
            o.append(f"  - field:  {e['field']}"
                     + (f"            # {e['code']}" if e["code"] else ""))
            o.append(f"    action: {e['action']}"
                     + ("            # optional" if e.get("optional") else ""))
            if "add" in e:
                o.append("    add:")
                for aid, note in e["add"].items():
                    o.append(f"      {aid}: {q(note)}")
            if "find" in e:
                o.append(f"    find:   {q(e['find'])}")
            if "text" in e:
                o.append(f"    text: {block(e['text'], 6)}")
            if "terms" in e:
                o.append(f"    after_n: {e['after_n']}"
                         f"                # appends past a({e['after_n']}) ="
                         f" {e['after_n_term']}")
                o.append("    terms:")
                for t, why in e["terms"]:
                    o.append(f"    - {t}" + (f"    # {why}" if why else ""))
        o.append("")

    for ns in new_seqs:
        if not o[-1] == "":
            o.append("")
        o += ["new_sequences:", "",
              f'- id:     "{ns["id"]}"',
              f"  role:   {q(ns['role'])}",
              f'  url:    "{ns["url"]}"']
        if ns.get("status"):
            o.append(f"  status: {ns['status']}")
        if ns.get("notes"):
            o.append("  notes: true")
        o.append(f"  summary: {block(ns['summary'], 4)}")
        o.append(f"  to_editors: {block(ns['to_editors'], 4)}")
        o.append("  entry:")
        e = ns["entry"]
        o.append(f"    name: {block(e['name'], 6)}")
        o.append(f"    offset: {q(e['offset'])}")
        o.append("    data: [" + ", ".join(str(x) for x in e["data"]) + "]")
        o.append(f'    keywords: "{e["keywords"]}"')
        o.append(f"    author: {q(e['author'])}")
        o.append("    comments:")
        for c in e["comments"]:
            o.append(f"    - {block(c, 6)}")
        o.append("    example: |-")
        for l in e["example"].splitlines():
            o.append(f"      {l}")
        o.append("    xrefs:")
        for aid, note in e["xrefs"].items():
            o.append(f"      {aid}: {q(note)}")
        if ns.get("no_bfile"):
            o.append(f"  no_bfile: {q(ns['no_bfile'])}")
        o.append("")

    for key, title in (("blocked", "blocked"), ("pending", "pending"),
                       ("review", "review")):
        rows = other.get(key) or []
        if not rows:
            continue
        o.append(f"# {title}: no OEIS field edit; carried so nothing is lost.")
        o.append(f"{title}:")
        for r in rows:
            o.append(f'- id:     "{r["id"]}"')
            o.append(f"  reason: {q(r['reason'])}")
        o.append("")
    return "\n".join(o).rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# Writing it all out
# ---------------------------------------------------------------------------

def write(path, text, manifest):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(text)
    manifest[os.path.basename(path)] = \
        hashlib.sha256(text.encode()).hexdigest()[:16]
    return text


# ---------------------------------------------------------------------------
# The browser side
#
# A bookmarklet injects fill.js into the OEIS edit page. fill.js mounts
# panel.html from localhost in an iframe pinned beside the form; the two talk
# over postMessage, because the panel is cross-origin with oeis.org and cannot
# touch its DOM. The panel keeps batch progress in its own localStorage, which
# survives every page load; the CURRENT sequence's state is not remembered at
# all but re-derived from the live form each time, so it stays right through
# reloads and hand edits.
#
# The form's own copyin() submits each field's innerHTML, not its text, so a
# field is read by unescaping innerHTML and written by setting textContent --
# the same round-trip typing by hand produces.
# ---------------------------------------------------------------------------

FILL_JS = r"""
(function () {
  var PORT = %(port)d, ORIGIN = 'http://localhost:' + PORT;
  if (window.__oeisFill) { window.__oeisFill.rescan(); return; }

  var seqEl = document.querySelector('input[name=seq]');
  var SEQ = seqEl ? seqEl.value : null;

  // A field's text is escaped in its innerHTML, so any real tag is layout: a
  // field reopened from a saved draft holds one <p> per line. Turn those
  // into newlines, or the field reads as one line and a write would put the
  // tags back as literal text.
  function read(f) {
    var d = document.getElementById('edit_' + f);
    if (!d) return null;
    var h = d.innerHTML
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/(p|div)>\s*<(p|div)\b[^>]*>/gi, '\n')
      .replace(/<[^>]*>/g, '');
    var t = document.createElement('textarea');
    t.innerHTML = h;
    return t.value;
  }
  // Written back in the field's own layout: one <p> per line if it was in
  // paragraphs, where a bare newline would show as a space and join lines.
  function write(f, v) {
    var d = document.getElementById('edit_' + f);
    if (!d) return false;
    if (/<p\b/i.test(d.innerHTML)) {
      d.innerHTML = v.split('\n').map(function (l) {
        return '<p>' + (l ? l.replace(/&/g, '&amp;').replace(/</g, '&lt;')
                             .replace(/>/g, '&gt;') : '<br>') + '</p>';
      }).join('');
    } else d.textContent = v;
    return true;
  }

  function addXrefs(cur, adds) {
    var miss = adds.filter(function (a) {
      return new RegExp('\\b' + a[0] + '\\b').test(cur) === false; });
    if (!miss.length) return null;
    var frag = miss.map(function (a) {
      return a[1] ? a[0] + ' (' + a[1] + ')' : a[0]; }).join(', ');
    var lines = (cur || '').split('\n');
    for (var i = 0; i < lines.length; i++) {
      if (/^\s*Cf\./.test(lines[i])) {
        lines[i] = lines[i].replace(/\s*\.\s*$/, '') + ', ' + frag + '.';
        return lines.join('\n');
      }
    }
    return (cur && cur.trim() ? cur.trim() + '\n' : '') + 'Cf. ' + frag + '.';
  }

  function appendData(cur, afterTerm, terms) {
    var t = (cur || '').trim().replace(/,\s*$/, '');
    var last = t.split(',').pop().trim();
    if (last === String(terms[terms.length - 1])) return null;
    if (last !== String(afterTerm))
      throw 'DATA ends at ' + last + ', expected ' + afterTerm +
            ' -- published data moved; not touching it';
    return t + ', ' + terms.join(', ');
  }

  // OEIS writes the uploaded b-file's link line crediting only the uploader;
  // put back the earlier contributors, keeping the href OEIS chose.
  function creditLine(cur, up, text) {
    var href = 'href="/' + SEQ + '/' + up + '"';
    var want = text.replace(/href="[^"]*"/, href);
    var lines = (cur || '').split('\n');
    for (var i = 0; i < lines.length; i++) {
      if (lines[i].indexOf(href) < 0) continue;
      if (lines[i].trim() === want.trim()) return null;
      lines[i] = want;
      return lines.join('\n');
    }
    throw 'no link line for ' + up;
  }

  // Drop the one line containing `find` -- the link to a file an upload is
  // replacing. Already gone means already applied.
  function removeLine(cur, find) {
    var lines = (cur || '').split('\n');
    var keep = lines.filter(function (l) { return l.indexOf(find) < 0; });
    return keep.length === lines.length ? null : keep.join('\n');
  }

  function addLine(cur, text) {
    var probe = text.replace(/\s+/g, ' ').slice(0, 45);
    if ((cur || '').replace(/\s+/g, ' ').indexOf(probe) >= 0) return null;
    return (cur && cur.trim() ? cur.trim() + '\n' : '') + text;
  }

  // What each edit would produce, or null if it is already applied. Used both
  // to report status and to perform the change -- one code path, so the panel
  // can never claim a state the fill would not produce.
  function plan(e) {
    var cur = read(e.field);
    if (cur === null) return { err: 'no field ' + e.field };
    try {
      var v = null;
      if (e.action === 'add' && e.add)
        v = addXrefs(cur, e.add);
      else if (e.action === 'append')
        v = appendData(cur, e.after_n_term, e.terms);
      else if (e.action === 'add')
        v = addLine(cur, e.text);
      else if (e.action === 'remove')
        v = removeLine(cur, e.find);
      else if (e.action === 'credit_bfile_link') {
        var u = (draft.uploads || []).filter(function (x) {
          return x.kind === 'b-file'; })[0];
        var up = u && uploadedAs(u);
        if (!up) return { wait: 'after the b-file is uploaded: Save Changes, '
                                + 'reopen the draft, and Fill this' };
        v = creditLine(cur, up, e.text);
      }
      return v === null ? { done: true } : { val: v };
    } catch (msg) { return { err: String(msg) }; }
  }

  // The form's upload boxes are upload_file0, upload_file1, ... A file goes
  // in the box already holding it, else the first empty one, so attaching
  // twice is harmless and a page with fewer boxes than files says so.
  function box(k) {
    return document.querySelector('input[name=upload_file' + k + ']');
  }
  function holder(name) {
    for (var k = 0, inp; (inp = box(k)); k++)
      if (inp.files && inp.files.length && inp.files[0].name === name) return k;
    return -1;
  }
  // A file an earlier save of this draft already uploaded. OEIS writes a %%H
  // line linking the stored copy -- renamed <stem>_<k>.txt when the name is
  // taken -- for a b-file by itself and for an a-file from its link text.
  // The link is looked for in the Link field and, on a page without one
  // (the draft view a save lands on), anywhere on the page. Only a link the
  // published entry did not have counts, and never the file an update
  // replaces.
  function uploadedAs(u) {
    var stem = u.name.replace(/\.txt$/, ''), re = new RegExp(
      '/' + SEQ + '/(' + stem + '(_\\d+)?\\.txt)', 'g'), m;
    var cur = read('Link');
    if (cur === null) {
      cur = '';
      var as = document.querySelectorAll ? document.querySelectorAll('a[href]')
                                         : [];
      for (var i = 0; i < as.length; i++)
        cur += (as[i].getAttribute('href') || '') + '\n';
    }
    while ((m = re.exec(cur)))
      if ((m[2] || !u.published) && m[1] !== u.replaces) return m[1];
    return null;
  }
  function attach(u) {
    if (uploadedAs(u)) return { ok: true, uploaded: uploadedAs(u) };
    var k = holder(u.name);
    if (k >= 0) return { ok: true, slot: k };
    for (k = 0; box(k) && box(k).files && box(k).files.length; k++) {}
    var inp = box(k);
    if (!inp)
      return { err: k ? 'every upload box on this page is in use: Save '
                        + 'Changes, reopen the draft, and attach ' + u.name
                      : 'no upload box on this page' };
    try {
      var dt = new DataTransfer();
      dt.items.add(new File([u.content], u.name, { type: 'text/plain' }));
      inp.files = dt.files;
      inp.dispatchEvent(new Event('change', { bubbles: true }));
    } catch (err) { return { err: 'attach failed: ' + err }; }
    var cb = document.getElementById('upload_bfile' + k);
    if (u.kind === 'b-file' && cb && !cb.checked) cb.click();
    if (u.desc) write('upload_' + k, u.desc);
    return { ok: true, slot: k };
  }

  var draft = null, panel = null, credit = null;

  // An extended b-file's %%H line must credit whoever computed the earlier
  // terms: "Name, <a>Table ...</a> (terms 1..50 from Ken Takusagawa)". The
  // line OEIS writes on upload names only the uploader, so it stays flagged
  // until it carries the credit -- whether or not a draft for it is still
  // in this batch. On the edit form it comes with the corrected Link field;
  // on a page without one (the draft view) it can only be flagged.
  function creditCheck() {
    if (!credit) return null;
    var want = '(' + credit.text + ')', cur = read('Link');
    if (cur === null) {
      var t = (document.body && document.body.innerText) || '';
      return t.indexOf(credit.name + ', <a href="/' + SEQ + '/b') >= 0
             && t.indexOf(want) < 0 ? { want: want } : null;
    }
    var re = new RegExp('href="/' + SEQ + '/b\\d{6}(_\\d+)?\\.txt"');
    var lines = cur.split('\n');
    for (var i = 0; i < lines.length; i++) {
      var l = lines[i].trim();
      if (!re.test(l) || l.indexOf(credit.name + ',') !== 0) continue;
      if (l.indexOf(want) >= 0) return null;
      lines[i] = l.replace(/<\/a>.*$/, '</a> ' + want);
      return { want: want, line: l, fixed: lines[i], val: lines.join('\n') };
    }
    return null;
  }

  function states() {
    if (!draft) return [];
    return draft.edits.map(function (e) {
      var p = plan(e);
      return { field: e.field, code: e.code, action: e.action,
               optional: !!e.optional, done: !!p.done, err: p.err || null, wait: p.wait || null,
               cur: read(e.field), next: p.val || null };
    });
  }

  function post(msg) {
    if (panel && panel.contentWindow)
      panel.contentWindow.postMessage(msg, ORIGIN);
  }
  function uploadStates() {
    return draft ? (draft.uploads || []).map(function (u) {
      return { name: u.name, slot: holder(u.name),
               uploaded: uploadedAs(u) }; }) : [];
  }
  // The cross-references as they stand: the Xref field on the form, or on a
  // page without one -- the draft view a save lands on -- the page's text.
  function xrefText() {
    var x = read('Xref');
    if (x !== null) return x;
    return (document.body && document.body.innerText) || '';
  }
  function report() {
    post({ type: 'STATE', seq: SEQ, states: states(),
           uploads: uploadStates(), xref: xrefText(), credit: creditCheck(),
           saved: /\/draft\//.test(location.pathname) });
  }

  window.addEventListener('message', function (ev) {
    if (ev.origin !== ORIGIN) return;
    var m = ev.data || {};
    if (m.type === 'READY') {
      draft = m.draft || null;
      credit = m.credit || null;
      report();
    } else if (m.type === 'CREDIT_FIX') {
      var c = creditCheck();
      if (c && c.val) write('Link', c.val);
      report();
    } else if (m.type === 'FILL') {
      var e = draft.edits[m.index], p = plan(e);
      if (p.val) write(e.field, p.val);
      report();
    } else if (m.type === 'FILL_ALL') {
      // Optional edits -- suggested cross-references -- are filled one by
      // one, by choice, never in bulk.
      draft.edits.forEach(function (e) {
        if (e.optional) return;
        var p = plan(e);
        if (p.val) write(e.field, p.val);
      });
      var errs = {};
      // The form takes one upload per save, so attach the first file not
      // yet uploaded -- the b-file comes first -- and leave the rest for the
      // next save.
      var ups = draft.uploads || [];
      for (var i = 0; i < ups.length; i++) {
        if (uploadedAs(ups[i])) continue;
        var r = attach(ups[i]);
        if (r.err) errs[i] = r.err;
        break;
      }
      post({ type: 'ATTACHED', errs: errs });
      report();
    } else if (m.type === 'ATTACH') {
      var r = attach(draft.uploads[m.index]), one = {};
      if (r.err) one[m.index] = r.err;
      post({ type: 'ATTACHED', errs: one, index: m.index });
      report();
    } else if (m.type === 'NAVIGATE') {
      location.href = m.url;
    } else if (m.type === 'RESCAN') {
      report();
    } else if (m.type === 'SAVE_GO') {
      go();
    } else if (m.type === 'WIDTH') {
      panel.style.width = m.px + 'px';
      document.body.style.marginRight = m.px + 'px';
    }
  });

  // Save Changes is held for a moment so the panel can record the draft in
  // the tracker before the page goes away. The panel answers SAVE_GO, and if
  // it never does the save goes ahead anyway. Only a save is held: any other
  // button on the form submits as usual.
  var going = false, held = null;
  function go() {
    if (!held) return;
    var h = held;
    held = null;
    going = true;
    try {
      if (h.form.requestSubmit) h.form.requestSubmit(h.submitter || undefined);
      else h.form.submit();
    } catch (err) { h.form.submit(); }
  }
  if (document.addEventListener)
    document.addEventListener('submit', function (ev) {
      if (going || !draft) return;
      var b = ev.submitter;
      if (b && !/save/i.test(b.value || b.textContent || '')) return;
      ev.preventDefault();
      held = { form: ev.target, submitter: b };
      post({ type: 'SAVING', seq: SEQ, states: states(),
             uploads: uploadStates(), xref: xrefText() });
      setTimeout(go, 4000);
    }, true);

  panel = document.createElement('iframe');
  panel.src = ORIGIN + '/panel.html#' + encodeURIComponent(SEQ || '');
  panel.style.cssText = 'position:fixed;top:0;right:0;width:340px;height:100%%;'
    + 'border:0;border-left:1px solid #999;z-index:2147483647;background:#fff';
  document.body.style.marginRight = '340px';
  document.body.appendChild(panel);

  window.__oeisFill = { rescan: report };
})();
"""


def bookmarklet():
    """Tiny and permanent: everything volatile is served from localhost."""
    js = ("javascript:(function(){var s=document.createElement('script');"
          "s.src='http://localhost:%d/fill.js?'+Date.now();"
          "document.head.appendChild(s)})()" % PORT)
    return js


PANEL_HTML = r"""<!doctype html>
<meta charset="utf-8"><title>OEIS submit</title>
<style>
 :root{--fg:#222;--dim:#777;--line:#ddd;--ok:#1a7f37;--warn:#9a6700;--err:#b32}
 body{font:13px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
      margin:0;color:var(--fg);background:#fff}
 header{padding:10px 12px;border-bottom:1px solid var(--line);background:#fafafa}
 h1{font-size:13px;margin:0 0 2px}
 .sub{color:var(--dim);font-size:11px}
 section{padding:10px 12px;border-bottom:1px solid var(--line)}
 h2{font-size:11px;text-transform:uppercase;letter-spacing:.06em;
    color:var(--dim);margin:0 0 8px}
 .row{display:flex;gap:6px;align-items:baseline;padding:3px 0;cursor:pointer}
 .row:hover{background:#f4f4f4}
 .n{color:var(--dim);width:18px;text-align:right;flex:none}
 .aid{font-family:ui-monospace,Menlo,monospace;flex:none}
 .what{color:var(--dim);font-size:11px;overflow:hidden;text-overflow:ellipsis;
       white-space:nowrap}
 .cur{background:#fffbe6}
 .st{margin-left:auto;flex:none;font-size:11px}
 .opt{font-size:10px;color:#777;border:1px solid #ccc;border-radius:3px;
      padding:0 4px}
 .done{color:var(--ok)} .part{color:var(--warn)} .err{color:var(--err)}
 .f{border:1px solid var(--line);border-radius:4px;padding:7px;margin:6px 0}
 .f b{font-family:ui-monospace,Menlo,monospace;font-size:12px}
 .f .code{color:var(--dim);font-weight:normal}
 pre{white-space:pre-wrap;word-break:break-word;font-size:11px;margin:5px 0 0;
     background:#f6f8fa;padding:5px;border-radius:3px;max-height:8em;overflow:auto}
 pre.was{color:var(--dim)}
 button{font:inherit;font-size:11px;padding:3px 9px;border:1px solid #bbb;
        border-radius:4px;background:#fff;cursor:pointer}
 button:hover{background:#f0f0f0}
 button.p{background:#0969da;color:#fff;border-color:#0969da}
 .bar{display:flex;gap:6px;padding:8px 12px}
 .note{color:var(--dim);font-size:11px;padding:0 12px 10px}
 .up{border:1px solid var(--line);border-radius:4px;padding:7px;margin:6px 0}
 .up .why,.f .why{color:var(--dim);font-size:11px;margin:3px 0 5px}
 .up a{font-size:11px;color:#0969da;margin-left:6px}
 .steps{margin:0;padding-left:18px;font-size:11px;color:var(--dim)}
 #track .why{color:var(--dim);font-size:11px;margin:0 0 6px;word-break:break-word}
 #credit{background:#fff0ee;border-bottom:2px solid var(--err)}
 #credit h2{color:var(--err)}
 #slots{background:#fff8e1;border-bottom:2px solid var(--warn)}
 #slots h2{color:var(--warn)}
 #slots .why{font-size:11px}
 .next{color:#0969da}
</style>
<header>
  <h1 id="title">OEIS submit</h1>
  <div class="sub" id="sub"></div>
</header>
<section id="credit" hidden><h2>b-file link missing its history</h2>
  <div id="creditbody"></div></section>
<section id="slots" hidden><h2>No free draft slot</h2>
  <div class="why" id="slotsbody"></div></section>
<div id="fields"></div>
<section id="uploads" hidden><h2>Uploads</h2><div id="uplist"></div></section>
<div class="bar">
  <button class="p" id="all">Fill all</button>
  <button id="re">Rescan</button>
</div>
<section id="track" hidden><h2>Tracker</h2>
  <div class="why" id="trackst">Save Changes records this draft in
   submissions.txt once it completes the draft.</div>
  <button id="rec">Record in tracker</button>
</section>
<section><h2>Batch</h2><div id="list"></div></section>
<div class="note" id="note"></div>
<script src="payload.js"></script>
<script>
var P = window.OEIS_SUBMIT, OEIS = 'https://oeis.org';
var SEQ = decodeURIComponent(location.hash.slice(1));
var draft = P.drafts.filter(function(d){return d.aid===SEQ})[0] || null;
var KEY = 'oeis-submit-progress';
function progress(){ try{ return JSON.parse(localStorage.getItem(KEY)||'{}') }
                     catch(e){ return {} } }
function remember(aid,st){ var p=progress(); p[aid]=st;
  try{ localStorage.setItem(KEY,JSON.stringify(p)) }catch(e){} }
function send(m){ parent.postMessage(m, OEIS) }

document.getElementById('title').textContent =
  draft ? draft.aid + ' — ' + draft.role : 'No draft for ' + (SEQ||'this page');
document.getElementById('sub').textContent =
  (draft ? draft.summary : P.drafts.length + ' drafts in this batch')
  + (P.draft_limit ? ' · open on OEIS ' + P.open_drafts.length + '/'
     + P.draft_limit : '');

// OEIS holds one user to P.draft_limit open drafts; a save past that is
// refused. Say so before the form is filled, not after.
(function(){
  if(!draft || draft.slot!=='waits') return;
  document.getElementById('slots').hidden = false;
  document.getElementById('slotsbody').textContent =
    'OEIS allows '+P.draft_limit+' open drafts and '
    + P.open_drafts.length+' are open ('+P.open_drafts.join(', ')+'). '
    + 'This one waits until an editor approves one of them; until then a '
    + 'save will be refused.';
})();

function renderList(states){
  var p = progress(), out = '';
  P.drafts.forEach(function(d,i){
    var st = d.aid===SEQ ? liveState(states) : (p[d.aid]||'');
    var mark = st==='recorded' ? '<span class="st done">✓ recorded</span>'
             : st==='saved' ? '<span class="st done">● saved</span>'
             : st==='filled' ? '<span class="st part">◐ filled</span>'
             : d.blocked_on ? '<span class="st err">⊘ blocked</span>'
             : d.slot==='next' ? '<span class="st next">▶ next</span>'
             : d.slot==='waits' ? '<span class="st" style="color:#aaa">'
                                  + '⧗ waits</span>'
             : '<span class="st" style="color:#aaa">○</span>';
    out += '<div class="row'+(d.aid===SEQ?' cur':'')+'" data-aid="'+d.aid+'">'
         + '<span class="n">'+(i+1)+'</span>'
         + '<span class="aid">'+d.aid+'</span>'
         + '<span class="what">'+d.what+'</span>'+mark+'</div>';
  });
  document.getElementById('list').innerHTML = out;
  [].forEach.call(document.querySelectorAll('.row'), function(r){
    r.onclick = function(){
      send({type:'NAVIGATE', url: OEIS+'/edit?seq='+r.dataset.aid}); };
  });
}
function liveState(states){
  // A draft is saved once its required edits are; optional ones don't count.
  var req = (states||[]).filter(function(s){return !s.optional});
  if(req.length) states = req;
  if(!states||!states.length) return '';
  if(states.every(function(s){return s.done})) return 'saved';
  if(states.some(function(s){return s.done})) return 'filled';
  return '';
}
function esc(s){ return (s==null?'':String(s))
  .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') }

function render(msg){
  var states = msg.states||[], out='';
  if(draft){
    states.forEach(function(s,i){
      out += '<section class="f"><b>'+s.field+'</b> '
           + '<span class="code">'+esc(s.code)+' · '+s.action+'</span>'
           + (s.optional ? ' <span class="opt">optional</span>' : '');
      if(s.err) out += '<div class="err">'+esc(s.err)+'</div>';
      else if(s.wait) out += '<div class="why">Waits: '+esc(s.wait)+'</div>';
      else if(s.done) out += '<span class="st done"> ✓ applied</span>';
      else out += ' <button data-i="'+i+'">Fill</button>'
               + '<pre class="was">'+esc((s.cur||'').slice(0,300))+'</pre>'
               + '<pre>'+esc((s.next||'').slice(0,400))+'</pre>';
      out += '</section>';
    });
  }
  document.getElementById('fields').innerHTML = out;
  renderCredit(msg.credit);
  [].forEach.call(document.querySelectorAll('#fields button[data-i]'),
    function(b){ b.onclick=function(){ send({type:'FILL',index:+b.dataset.i}) }});
  renderUploads(msg.uploads||[]);
  last = msg;
  if(draft && progress()[draft.aid]!=='recorded')
    remember(draft.aid, msg.saved ? 'saved' : liveState(states));
  renderList(states);
}

// The b-file %H line OEIS wrote on upload, still without the earlier terms'
// credit that https://oeis.org/SubmitB.html asks for.
function renderCredit(c){
  var box = document.getElementById('credit');
  box.hidden = !c;
  if(!c) return;
  var out = '<div class="why">OEIS rewrote the b-file %H line to credit only '
          + 'you. Editors require the earlier terms\' history after it: '
          + esc(c.want)+'</div>';
  if(c.fixed)
    out += '<pre class="was">'+esc(c.line)+'</pre><pre>'+esc(c.fixed)+'</pre>'
         + '<button class="p" id="creditfix">Fix %H line</button> '
         + '<span class="why">then Save Changes.</span>';
  else
    out += '<button class="p" id="creditedit">Open the edit form</button>';
  document.getElementById('creditbody').innerHTML = out;
  var f = document.getElementById('creditfix'),
      e = document.getElementById('creditedit');
  if(f) f.onclick = function(){ send({type:'CREDIT_FIX'}) };
  if(e) e.onclick = function(){
    send({type:'NAVIGATE', url: OEIS+'/edit?seq='+SEQ}) };
}

// One card per file: what it is for, which upload box holds it, and the file
// itself, so it can be checked or uploaded by hand if Attach cannot.
var attachErr = {};
function renderUploads(live){
  var ups = draft ? (draft.uploads||[]) : [], out = '';
  document.getElementById('uploads').hidden = !ups.length;
  if(!ups.length){ document.getElementById('note').textContent=''; return; }
  out += '<ol class="steps"><li>Attach '+(ups.length>1?'the first file not '
         + 'yet uploaded':'the file')+' (Fill all does this).</li>'
       + '<li>Check the form, then Save Changes.</li>'
       + (ups.length>1 ? '<li>The form takes one file per save: reopen the '
         + 'draft and Fill all again for the next.</li>' : '')
       + '</ol>';
  ups.forEach(function(u,i){
    var at = (live[i]||{}).slot, up = (live[i]||{}).uploaded;
    if(up) at = 0;
    var st = up ? '<span class="st done">✓ uploaded as '+esc(up)+'</span>'
      : at>=0 ? '<span class="st done">✓ in upload box '+(at+1)+'</span>'
      : '<span class="st" style="color:#aaa">not attached</span>';
    out += '<div class="up"><b>'+(i+1)+'. '+esc(u.kind)+'</b> '
         + '<span class="code">'+esc(u.name)+'</span> '+st
         + '<div class="why">'+esc(u.purpose||'')+'</div>'
         + (attachErr[i] ? '<div class="err">'+esc(attachErr[i])+'</div>' : '')
         + (at>=0 ? '' : '<button data-u="'+i+'">Attach</button>')
         + '<a href="'+encodeURIComponent(u.name)+'" target="_blank">view</a>'
         + '<a href="'+encodeURIComponent(u.name)+'" download>download</a>'
         + '</div>';
  });
  document.getElementById('uplist').innerHTML = out;
  [].forEach.call(document.querySelectorAll('#uplist button[data-u]'),
    function(b){ b.onclick=function(){ send({type:'ATTACH',index:+b.dataset.u}) }});
  document.getElementById('note').textContent =
    'Attach sets the file from the payload; no file picker needed. '
    + 'If it cannot, download the file and choose it in the form\'s upload box.';
}

window.addEventListener('message', function(ev){
  if(ev.origin!==OEIS) return;
  var m = ev.data||{};
  if(m.type==='STATE') render(m);
  if(m.type==='ATTACHED'){
    if(m.index==null) attachErr = {};
    else delete attachErr[m.index];
    for(var k in (m.errs||{})) attachErr[k] = m.errs[k];
  }
});
// The tracker: oeis/submissions.txt, written by the server that serves this
// panel. A draft's items go on one line -- they are one OEIS edit -- except
// a suggested cross-reference left out of the form, which stays open. Leaving
// one out also records the sequence's open draft, so the audit does not offer
// it as a second edit stacked on this one.
var last = null;
function syncIds(msg){
  var x = (msg&&msg.xref)||'';
  var ids = (draft.items||[]).filter(function(i){
    var m = /^xref:[^:]+:(A\d{6})$/.exec(i);
    return !m || new RegExp('\\b'+m[1]+'\\b').test(x);
  });
  if(ids.length < (draft.items||[]).length) ids.push('draft:'+draft.aid);
  return ids;
}
// This save completes the draft: every required edit is in the form and
// every file is uploaded or attached to go up with it.
function complete(msg){
  var req = (msg.states||[]).filter(function(s){return !s.optional});
  return req.every(function(s){return s.done})
      && (msg.uploads||[]).every(function(u){return u.uploaded || u.slot>=0});
}
function note(ids){
  var left = (draft.items||[]).filter(function(i){return ids.indexOf(i)<0});
  return draft.aid+' '+draft.what.split(', ').filter(function(w){
    return !left.some(function(i){return w.indexOf(i.split(':')[2])>=0}) })
    .join(', ').replace(/ \(optional\)/g, '');
}
function track(ids, wait, done){
  var st = document.getElementById('trackst');
  st.textContent = 'Recording '+ids.join(', ')+' …';
  fetch('/submissions', {method:'POST', keepalive:true,
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ids:ids, status:'submitted', aid:draft.aid,
                          note:note(ids), wait:wait})})
  .then(function(r){ return r.json() })
  .then(function(j){
    if(j.ok){ remember(draft.aid,'recorded');
              st.innerHTML = '<span class="done">✓ Recorded:</span> '
                + esc(j.line); renderList(last&&last.states) }
    else st.innerHTML = '<span class="err">'+esc(j.error)+'</span>';
  })
  .catch(function(e){ st.innerHTML = '<span class="err">Not recorded: '
    + esc(e)+' -- is make submit running?</span>' })
  .then(function(){ if(done) done() });
}
document.getElementById('track').hidden = !draft;
document.getElementById('rec').onclick=function(){
  var ids = syncIds(last);
  if(confirm('Record as submitted in submissions.txt?\n\n'+ids.join('\n')))
    track(ids, true);
};
window.addEventListener('message', function(ev){
  if(ev.origin!==OEIS || (ev.data||{}).type!=='SAVING') return;
  var go = function(){ send({type:'SAVE_GO'}) };
  if(draft && complete(ev.data)) track(syncIds(ev.data), false, go);
  else go();
});
document.getElementById('all').onclick=function(){ send({type:'FILL_ALL'}) };
document.getElementById('re').onclick =function(){ send({type:'RESCAN'}) };
renderList([]);
var credit = (P.credits||{})[SEQ];
send({type:'READY', draft: draft,
      credit: credit ? {name: P.meta.name, text: credit} : null});
</script>
"""


INDEX_HTML = r"""<!doctype html>
<meta charset="utf-8"><title>OEIS submissions</title>
<style>
 body{font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
      max-width:64em;margin:2em auto;padding:0 1.5em;color:#222}
 h1{font-size:20px;margin:0 0 .2em} h2{font-size:14px;margin:2em 0 .6em;
      text-transform:uppercase;letter-spacing:.06em;color:#777}
 .sub{color:#777;margin:0 0 1.5em}
 table{border-collapse:collapse;width:100%%}
 td,th{text-align:left;padding:6px 8px;border-bottom:1px solid #eee;
       vertical-align:top}
 th{font-size:11px;text-transform:uppercase;color:#777;letter-spacing:.06em}
 td.n{color:#999;width:2em;text-align:right}
 a{color:#0969da} code{font-family:ui-monospace,Menlo,monospace;font-size:12px}
 .what{color:#555;font-size:13px}
 .edit{display:inline-block;margin-left:6px;padding:0 8px;font-size:12px;
       border:1px solid #0969da;border-radius:10px;text-decoration:none;
       white-space:nowrap}
 .edit:hover{background:#0969da;color:#fff}
 .title{font-size:13px;max-width:22em}
 .name{color:#777;font-size:12px;white-space:nowrap}
 .bm{display:inline-block;padding:6px 14px;border:1px solid #0969da;
     border-radius:6px;color:#0969da;text-decoration:none;font-weight:600}
 .box{background:#f6f8fa;border:1px solid #e3e6ea;border-radius:6px;
      padding:12px 16px;margin:1.2em 0}
 .warn{color:#9a6700}
 .ok{color:#1a7f37;font-weight:600}
 .err{color:#cf222e;font-weight:600}
 tr.done td{color:#777}
 .track{margin-top:4px;white-space:nowrap}
 .track button{font:inherit;font-size:11px;padding:1px 8px;margin-right:4px;
      border:1px solid #bbb;border-radius:4px;background:#fff;cursor:pointer}
 .track button:hover{background:#f0f0f0}
 .next{color:#0969da;font-size:12px;white-space:nowrap}
</style>
<h1>OEIS submissions</h1>
<p class="sub">%(n)d drafts &middot; generated %(date)s from <code>%(run)s/</code>
 &middot; check_oeis.py: <strong>%(check)s</strong>%(slots)s</p>

<div class="box">
  <p style="margin:0 0 .6em"><strong>1.</strong> Drag this to your bookmarks bar
   (once), <strong>2.</strong> open a sequence below, <strong>3.</strong> click
   the bookmarklet.</p>
  <a class="bm" href="%(bm)s">OEIS Fill</a>
  <p style="margin:.8em 0 0;color:#777;font-size:12px">Needs this server
   running: <code>make submit</code> (serves this directory on
   localhost:%(port)d). The bookmarklet loads everything fresh, so
   regenerating the audit needs no re-drag. Save Changes on a draft the panel
   has completed, and the buttons below, record progress in
   <code>oeis/submissions.txt</code> and rerun the audit.</p>
</div>

<h2>Drafts</h2>
<table><tr><th>#</th><th>Sequence</th><th>Changes</th><th>Files</th>
 <th>Status</th></tr>
%(rows)s
</table>
%(extra)s
<script>
// Each button records its items on one line of oeis/submissions.txt, through
// the server that serves this page, which then reruns the audit.
document.addEventListener('click', function (ev) {
  var b = ev.target.closest('.track button');
  if (!b) return;
  var ids = b.dataset.ids.split(','), st = b.dataset.status;
  var note = prompt('Record ' + ids.join(', ') + ' as ' + st +
                    '.\nNote for submissions.txt (optional):', '');
  if (note === null) return;
  b.disabled = true;
  b.textContent = 'Recording…';
  fetch('/submissions', {method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ids: ids, status: st, aid: b.dataset.aid,
                          note: note})})
  .then(function (r) { return r.json(); })
  .then(function (j) {
    if (!j.ok) throw j.error;
    if (!j.audit_ok) alert('Recorded, but the audit failed:\n' + j.audit);
    location.reload();
  })
  .catch(function (e) {
    alert('Not recorded: ' + e + '\nIs make submit running?');
    b.disabled = false;
    b.textContent = st;
  });
});
</script>
<p style="color:#777;font-size:12px;margin-top:2em">Nothing here submits
 anything. The panel fills fields and attaches files; you review the form and
 click Save Changes. Saving makes a draft <code>editing</code> &mdash; it
 reaches editors only when you set it to <code>proposed</code>.</p>
"""


# The non-draft lists under the worklist: (key in `other`, heading, gloss).
SECTIONS = (
    ("blocked", "Needs data",
     "b-files short of their family that no scan can extend: their terms need "
     "pi(p), the prime's index, which takes a prime-counting program."),
    ("pending", "Low priority",
     "Nothing to upload yet: the entry's DATA already holds every term, or the "
     "scan has not reached the end of the published data."),
    ("review", "To review",
     "Related sequences found by the crawl that a person has not yet judged."),
)


def write_all(out_dir, drafts, new_seqs, other, meta, files, names=None,
              titles=None, bfiles=None):
    """Write every generated file, and return the manifest.

    `names` maps an A-number to the friendly name shown beside it, `titles`
    to its OEIS title, and `bfiles` to (terms, current) for its published
    b-file.
    """
    man = {}
    for name, text in sorted(files.items()):
        write(os.path.join(out_dir, name), text, man)
    # An upload from an earlier run that is no longer built -- its data is now
    # published -- would otherwise linger and look like work still to do.
    for name in os.listdir(out_dir):
        if re.fullmatch(r"[ab]\d{6}\.txt", name) and name not in files:
            os.remove(os.path.join(out_dir, name))

    # edits.yaml keeps `add` as a mapping, which reads better there. fill.js
    # wants ordered [aid, note] pairs -- it splices them into the Cf. line in
    # order -- so the payload carries pairs. test_fill.js asserts the shapes
    # still match; an object here would splice single characters.
    def for_js(edits):
        out = []
        for e in edits:
            e = dict(e)
            if isinstance(e.get("add"), dict):
                e["add"] = [[a, n] for a, n in sorted(e["add"].items())]
            if "terms" in e:
                e["terms"] = [t for t, _ in e["terms"]]
            out.append(e)
        return out

    def purpose(u, d):
        """What the file is for, in the words of the edit form."""
        name = os.path.basename(u["path"])
        if u["kind"] == "b-file":
            return (f"The b-file: {u['rows']} terms, uploaded with the b-file "
                    f"box ticked. OEIS then rewrites the b-file %H line to "
                    f"credit only you; once saved, the Link card puts the "
                    f"earlier contributors back.")
        if u.get("replaces"):
            return (f"The a-file update: {u['rows']} rows, replacing "
                    f"{u['replaces']}. Its link text fills the upload box, so "
                    f"OEIS writes the new %H line itself; the Link card drops "
                    f"the old one.")
        return (f"The a-file: {u['rows']} rows, each record with its "
                f"bounding primes and gaps. "
                + ("Its link text fills the upload box, so OEIS writes the "
                   "%H line itself, with the name it stores the file under."
                   if u.get("desc") else
                   "Replaces the file the existing %H line already links."))

    payload = {
        "meta": {**meta, "name": ATTRIB["name"]},
        "open_drafts": other.get("open_drafts") or [],
        "draft_limit": other.get("draft_limit"),
        "credits": other.get("credits") or {},
        "drafts": [{
            "aid": d["aid"], "role": d["role"], "what": d["what"],
            "items": d["items"],
            "summary": d["summary"],
            "blocked_on": d.get("blocked_on") or None,
            "slot": d.get("slot"),
            "edits": for_js(d["edits"]),
            "uploads": [{"kind": u["kind"],
                         "name": os.path.basename(u["path"]),
                         "replaces": u.get("replaces"),
                         "slot": i, "rows": u["rows"],
                         "published": bool(u.get("published")),
                         "purpose": purpose(u, d),
                         "desc": u.get("desc", ""),
                         "content": files[os.path.basename(u["path"])]}
                        for i, u in enumerate(d.get("uploads") or [])],
        } for d in drafts],
    }
    write(os.path.join(out_dir, "payload.js"),
          "window.OEIS_SUBMIT = " + json.dumps(payload, indent=1) + ";\n", man)
    write(os.path.join(out_dir, "fill.js"), FILL_JS % {"port": PORT}, man)
    write(os.path.join(out_dir, "panel.html"), PANEL_HTML, man)

    names, titles, bfiles = names or {}, titles or {}, bfiles or {}

    def published_bfile(aid):
        """A line for a row that uploads no b-file: the one OEIS has, and
        whether it already holds everything a scan could add."""
        if aid not in bfiles:
            return ""
        n, current = bfiles[aid]
        name = f"b{aid[1:]}.txt"
        return (f'<a href="https://oeis.org/{aid}/{name}" target="_blank">'
                f'<code>{name}</code></a> on OEIS, {n} terms'
                + (' &mdash; <span class="ok">up to date</span>' if current
                   else ""))

    def seq_cell(aid, edit_url=None, views=()):
        """The A-number, linked to its public page, with its OEIS title, its
        friendly name and, for a draft, the edit form. Both open in a new tab, so the worklist
        stays put; the bookmarklet runs in whichever tab it is clicked."""
        if not aid:
            return ""
        out = (f'<a href="https://oeis.org/{aid}" target="_blank">{aid}</a>')
        if edit_url:
            out += (f' <a class="edit" href="{edit_url}" target="_blank" '
                    f'title="Open the OEIS edit form">&#9998; Edit</a>')
        # Read-only pages for an edit already sent: the open draft with its
        # discussion, and the revision history. No form, so nothing to edit
        # by accident.
        for view in views:
            url, label, tip = {
                "draft": (f"https://oeis.org/draft/{aid}", "Draft",
                          "The open draft and its discussion"),
                "history": (f"https://oeis.org/history?seq={aid}", "History",
                            "The entry's revision history")}[view]
            out += (f' <a class="edit" href="{url}" target="_blank" '
                    f'title="{tip}">{label}</a>')
        if aid in titles:
            out += f'<div class="title">{linked(titles[aid])}</div>'
        if aid in names:
            out += f'<div class="name">{html.escape(names[aid])}</div>'
        return out

    def linked(text):
        """Plain text, escaped, with every A-number linked to its public page."""
        return re.sub(r"\bA\d{6}\b",
                      lambda m: f'<a href="https://oeis.org/{m[0]}" '
                                f'target="_blank">{m[0]}</a>',
                      html.escape(text or ""))

    def track_buttons(ids, aid, statuses):
        """Buttons that record `ids` in submissions.txt, one per status."""
        return '<div class="track">' + "".join(
            f'<button data-ids="{html.escape(",".join(ids))}" '
            f'data-aid="{aid or ""}" data-status="{st}">'
            f'{"Mark submitted" if st == "submitted" else st.title()}'
            f'</button>' for st in statuses) + '</div>'

    rows = []
    for i, d in enumerate(drafts, 1):
        f = "<br>".join(
            f'<a href="{os.path.basename(u["path"])}"><code>'
            f'{os.path.basename(u["path"])}</code></a> {u["kind"]}'
            for u in d.get("uploads") or [])
        if not any(u["kind"] == "b-file" for u in d.get("uploads") or []):
            f = "<br>".join(x for x in (f, published_bfile(d["aid"])) if x)
        st = d.get("status") or ("blocked" if d.get("blocked_on") else "")
        slot = {"next": '<div class="next">next: a draft slot is free</div>',
                "waits": '<div class="name">waits for a free draft slot'
                         '</div>'}.get(d.get("slot"), "")
        rows.append(
            f'<tr><td class="n">{i}</td>'
            f'<td>{seq_cell(d["aid"], d["url"])}</td>'
            f'<td class="what">{linked(d["what"])}</td>'
            f'<td>{f}</td>'
            f'<td class="warn">{st}{slot}'
            + ("" if st else track_buttons(d["items"], d["aid"],
                                           ("submitted",)))
            + '</td></tr>')
    # What has gone to OEIS: approved edits get a check, rejected ones a
    # cross, ones still with an editor an ellipsis. All sit under the open
    # drafts, numbered apart.
    looks = {"approved": ("ok", "&#10003;"), "rejected": ("err", "&#10007;"),
             "pending": ("warn", "&hellip;")}
    for r in other.get("done") or []:
        cls, mark = looks[r["state"]]
        views = (("draft", "history") if r["state"] == "pending"
                 else ("history",))
        done_files = "<br>".join(
            f'<a href="{html.escape(href)}"'
            + (' target="_blank"' if href.startswith("http") else "")
            + f'><code>{html.escape(label)}</code></a>'
            for label, href in r.get("files") or [])
        if not any(l.startswith("b") for l, _ in r.get("files") or []):
            done_files = "<br>".join(
                x for x in (done_files, published_bfile(r["aid"])) if x)
        rows.append(
            f'<tr class="done"><td class="n {cls}">{mark}</td>'
            f'<td>{seq_cell(r["aid"], views=views)}</td>'
            f'<td class="what"><code>{linked(r["id"])}</code> {linked(r["reason"])}</td>'
            f'<td>{done_files}</td>'
            f'<td class="{cls}">{r["state"]} {r["date"]}'
            + (track_buttons(r["id"].split(", "), r["aid"],
                             ("approved", "declined"))
               if r["state"] == "pending" else "")
            + '</td></tr>')
    extra = ""
    if new_seqs:
        extra += "<h2>New sequences</h2><table>" + "".join(
            f'<tr><td class="n">&mdash;</td>'
            f'<td><a class="edit" href="{n["url"]}" target="_blank" '
            f'title="Open the OEIS new-sequence form">&#9998; New</a></td>'
            f'<td class="what">{linked(n["role"])}</td><td></td>'
            f'<td class="warn">{n.get("status") or ""}</td></tr>'
            for n in new_seqs) + "</table>"
    for key, title, why in SECTIONS:
        if other.get(key):
            extra += (f"<h2>{title}</h2><p class=\"sub\">{why}</p><table>"
                      + "".join(
                f'<tr><td class="n">&mdash;</td><td><code>{linked(r["id"])}</code></td>'
                f'<td class="what" colspan=3>{linked(r["reason"])}</td></tr>'
                for r in other[key]) + "</table>")

    write(os.path.join(out_dir, "index.html"), INDEX_HTML % {
        "n": len(drafts), "date": meta["date"], "run": meta["run"],
        "check": "pass" if meta["check"] else "FAILING",
        "bm": bookmarklet().replace('"', "&quot;"),
        "port": PORT, "rows": "\n".join(rows), "extra": extra,
        "slots": (f' &middot; open on OEIS: <strong>'
                  f'{len(other.get("open_drafts") or [])}/'
                  f'{other["draft_limit"]}</strong>'
                  if other.get("draft_limit") else "")}, man)

    write(os.path.join(out_dir, "edits.yaml"),
          render_yaml(drafts, new_seqs, other, meta), man)
    write(os.path.join(out_dir, "MANIFEST.txt"),
          "# sha256 (first 16) of every generated file in this directory.\n"
          "# oeis_audit.py rewrites them all; edits here are lost.\n"
          + "".join(f"{v}  {k}\n" for k, v in sorted(man.items())
                    if k != "MANIFEST.txt"), {})
    return man
