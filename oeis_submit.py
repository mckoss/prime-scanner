#!/usr/bin/env python3
"""Turn the audit's contributions into a reviewable submission script.

oeis_audit.py decides WHAT can be contributed. This turns that into the
things you actually hand to OEIS:

    oeis/submit/edits.yaml     one entry per draft, ordered by A-number
    oeis/submit/b*.txt         b-files, ready to upload
    oeis/submit/a*.txt         a-files, ready to upload
    oeis/submit/index.html     the numbered worklist, with the bookmarklet
    oeis/submit/panel.html     the status panel, shown beside the edit form
    oeis/submit/fill.js        the shim the bookmarklet injects
    oeis/submit/payload.js     the drafts and the file contents, as JS

A draft is per SEQUENCE, not per contribution: every change to A096265 --
its b-file, its bound comment, its two cross-references -- is one OEIS
submission, so they are grouped that way here.

Nothing in this module talks to oeis.org. The generated files are read by a
browser you drive yourself; the tool fills forms and never submits one.
"""

import hashlib
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
        "cols": [("n", "index", "A000027", lambda r: r[0]),
                 ("p", "the lonely prime", "A023186", lambda r: r[1]),
                 ("d", "min(p-pp, np-p), the record", "A023187",
                  lambda r: r[2]),
                 ("pp", "previous prime", "", lambda r: r[5]),
                 ("np", "next prime", "", lambda r: r[6])],
    },
    "aloof": {
        "aid": "A096265",
        "title": "aloof prime records with bounding primes",
        "cols": [("n", "index", "A000027", lambda r: r[0]),
                 ("p", "the aloof prime", "A096265", lambda r: r[1]),
                 ("span", "np - pp, the record", "A031132", lambda r: r[2]),
                 ("pp", "previous prime", "A031133", lambda r: r[5]),
                 ("np", "next prime", "A031134", lambda r: r[6])],
    },
    "equidistant": {
        "aid": "A058867",
        "title": "equidistant prime records with bounding primes",
        "cols": [("n", "index", "A000027", lambda r: r[0]),
                 ("p", "the balanced prime", "A058867", lambda r: r[1]),
                 ("d", "p - pp = np - p, the record", "A058868",
                  lambda r: r[2]),
                 ("pp", "previous prime", "", lambda r: r[5]),
                 ("np", "next prime", "", lambda r: r[6])],
    },
    "pairwise": {
        "aid": "A087770",
        "title": "pairwise lonely prime records with bounding primes",
        # Both gaps carry the record here -- each beats the previous term's --
        # so neither alone is the value, and both are named outright.
        "cols": [("n", "index", "A000027", lambda r: r[0]),
                 ("p", "the pairwise lonely prime", "A087770",
                  lambda r: r[1]),
                 ("gb", "p - pp", "", lambda r: r[3]),
                 ("ga", "np - p", "", lambda r: r[4]),
                 ("pp", "previous prime", "", lambda r: r[5]),
                 ("np", "next prime", "", lambda r: r[6])],
    },
}


def afile(fam, rows, byline, bound, checked):
    spec = AFILE[fam]
    cols = spec["cols"]
    # A record with no lower neighbour (p = 2) cannot state its span or its
    # lower gap, so it is left out rather than published with a zero.
    rows = [r for r in rows if r[5]]
    key = [f"{c[0]:<5}{c[1]}" + (f" ({c[2]})" if c[2] else "") for c in cols]
    head = [f"a{spec['aid'][1:]}.txt -- {spec['title']}", ""] + key + [""]
    head += attribution_lines(byline, bound, checked) + [""]
    body = [[str(c[3](r)) for c in cols] for r in rows]
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
        if d.get("blocked_on"):
            o.append("  blocked_on:")
            o += [f"  - {q(b)}" for b in d["blocked_on"]]
        if d.get("notes"):
            o.append("  notes: true")
        o.append(f"  summary: {block(d['summary'], 4)}")
        if d.get("to_editors"):
            o.append(f"  to_editors: {block(d['to_editors'], 4)}")
        if d.get("upload"):
            u = d["upload"]
            o += ["  upload:",
                  f"    kind: {u['kind']}",
                  f"    path: {u['path']}",
                  f"    rows: {u['rows']}",
                  f"    from: {q(u['from'])}"]
        if d["edits"]:
            o.append("  edits:")
        for e in d["edits"]:
            o.append(f"  - field:  {e['field']}"
                     + (f"            # {e['code']}" if e["code"] else ""))
            o.append(f"    action: {e['action']}")
            if "add" in e:
                o.append("    add:")
                for aid, note in e["add"].items():
                    o.append(f"      {aid}: {q(note)}")
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

  function read(f) {
    var d = document.getElementById('edit_' + f);
    if (!d) return null;
    var t = document.createElement('textarea');
    t.innerHTML = d.innerHTML;
    return t.value;
  }
  function write(f, v) {
    var d = document.getElementById('edit_' + f);
    if (!d) return false;
    d.textContent = v;
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

  function replaceLine(cur, needle, text) {
    var lines = (cur || '').split('\n');
    for (var i = 0; i < lines.length; i++) {
      if (lines[i].indexOf(needle) >= 0) {
        if (lines[i].trim() === text.trim()) return null;
        lines[i] = text;
        return lines.join('\n');
      }
    }
    return (cur && cur.trim() ? cur.trim() + '\n' : '') + text;
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
      else if (e.action === 'replace_bfile_link')
        v = replaceLine(cur, e.needle, e.text);
      else if (e.action === 'add')
        v = addLine(cur, e.text);
      return v === null ? { done: true } : { val: v };
    } catch (msg) { return { err: String(msg) }; }
  }

  function attach(u) {
    var inp = document.querySelector('input[name=upload_file' + u.slot + ']');
    if (!inp) return { err: 'no upload slot ' + u.slot };
    try {
      var dt = new DataTransfer();
      dt.items.add(new File([u.content], u.name, { type: 'text/plain' }));
      inp.files = dt.files;
      inp.dispatchEvent(new Event('change', { bubbles: true }));
    } catch (err) { return { err: 'attach failed: ' + err }; }
    var cb = document.getElementById('upload_bfile' + u.slot);
    if (u.kind === 'b-file' && cb && !cb.checked) cb.click();
    if (u.desc) write('upload_' + u.slot, u.desc);
    return { ok: true };
  }

  var draft = null, panel = null;

  function states() {
    if (!draft) return [];
    return draft.edits.map(function (e) {
      var p = plan(e);
      return { field: e.field, code: e.code, action: e.action,
               done: !!p.done, err: p.err || null,
               cur: read(e.field), next: p.val || null };
    });
  }

  function post(msg) {
    if (panel && panel.contentWindow)
      panel.contentWindow.postMessage(msg, ORIGIN);
  }
  function report() {
    post({ type: 'STATE', seq: SEQ, states: states(),
           upload: draft && draft.upload ? draft.upload.name : null,
           saved: /\/draft\//.test(location.pathname) });
  }

  window.addEventListener('message', function (ev) {
    if (ev.origin !== ORIGIN) return;
    var m = ev.data || {};
    if (m.type === 'READY') {
      draft = m.draft || null;
      report();
    } else if (m.type === 'FILL') {
      var e = draft.edits[m.index], p = plan(e);
      if (p.val) write(e.field, p.val);
      report();
    } else if (m.type === 'FILL_ALL') {
      draft.edits.forEach(function (e) {
        var p = plan(e);
        if (p.val) write(e.field, p.val);
      });
      if (draft.upload) attach(draft.upload);
      report();
    } else if (m.type === 'ATTACH') {
      post({ type: 'ATTACHED', r: attach(draft.upload) });
      report();
    } else if (m.type === 'NAVIGATE') {
      location.href = m.url;
    } else if (m.type === 'RESCAN') {
      report();
    } else if (m.type === 'WIDTH') {
      panel.style.width = m.px + 'px';
      document.body.style.marginRight = m.px + 'px';
    }
  });

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
</style>
<header>
  <h1 id="title">OEIS submit</h1>
  <div class="sub" id="sub"></div>
</header>
<div id="fields"></div>
<div class="bar">
  <button class="p" id="all">Fill all</button>
  <button id="re">Rescan</button>
</div>
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
  draft ? draft.summary : P.drafts.length + ' drafts in this batch';

function renderList(states){
  var p = progress(), out = '';
  P.drafts.forEach(function(d,i){
    var st = d.aid===SEQ ? liveState(states) : (p[d.aid]||'');
    var mark = st==='saved' ? '<span class="st done">● saved</span>'
             : st==='filled' ? '<span class="st part">◐ filled</span>'
             : d.blocked_on ? '<span class="st err">⊘ blocked</span>'
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
           + '<span class="code">'+esc(s.code)+' · '+s.action+'</span>';
      if(s.err) out += '<div class="err">'+esc(s.err)+'</div>';
      else if(s.done) out += '<span class="st done"> ✓ applied</span>';
      else out += ' <button data-i="'+i+'">Fill</button>'
               + '<pre class="was">'+esc((s.cur||'').slice(0,300))+'</pre>'
               + '<pre>'+esc((s.next||'').slice(0,400))+'</pre>';
      out += '</section>';
    });
    if(draft.upload)
      out += '<section class="f"><b>'+draft.upload.kind+'</b> '
           + '<span class="code">'+esc(draft.upload.name)+'</span>'
           + ' <button id="att">Attach</button></section>';
  }
  document.getElementById('fields').innerHTML = out;
  [].forEach.call(document.querySelectorAll('#fields button[data-i]'),
    function(b){ b.onclick=function(){ send({type:'FILL',index:+b.dataset.i}) }});
  var a=document.getElementById('att');
  if(a) a.onclick=function(){ send({type:'ATTACH'}) };
  if(draft) remember(draft.aid, msg.saved ? 'saved' : liveState(states));
  renderList(states);
  document.getElementById('note').textContent = draft && draft.upload
    ? 'Attach sets the file from the payload; no file picker needed.'
    : '';
}

window.addEventListener('message', function(ev){
  if(ev.origin!==OEIS) return;
  if((ev.data||{}).type==='STATE') render(ev.data);
});
document.getElementById('all').onclick=function(){ send({type:'FILL_ALL'}) };
document.getElementById('re').onclick =function(){ send({type:'RESCAN'}) };
renderList([]);
send({type:'READY', draft: draft});
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
 .bm{display:inline-block;padding:6px 14px;border:1px solid #0969da;
     border-radius:6px;color:#0969da;text-decoration:none;font-weight:600}
 .box{background:#f6f8fa;border:1px solid #e3e6ea;border-radius:6px;
      padding:12px 16px;margin:1.2em 0}
 .warn{color:#9a6700}
</style>
<h1>OEIS submissions</h1>
<p class="sub">%(n)d drafts &middot; generated %(date)s from <code>%(run)s/</code>
 &middot; check_oeis.py: <strong>%(check)s</strong></p>

<div class="box">
  <p style="margin:0 0 .6em"><strong>1.</strong> Drag this to your bookmarks bar
   (once), <strong>2.</strong> open a sequence below, <strong>3.</strong> click
   the bookmarklet.</p>
  <a class="bm" href="%(bm)s">OEIS Fill</a>
  <p style="margin:.8em 0 0;color:#777;font-size:12px">Needs this server
   running: <code>make submit</code> (serves this directory on
   localhost:%(port)d). The bookmarklet loads everything fresh, so
   regenerating the audit needs no re-drag.</p>
</div>

<h2>Drafts</h2>
<table><tr><th>#</th><th>Sequence</th><th>Changes</th><th>Files</th>
 <th>Status</th></tr>
%(rows)s
</table>
%(extra)s
<p style="color:#777;font-size:12px;margin-top:2em">Nothing here submits
 anything. The panel fills fields and attaches files; you review the form and
 click Save Changes. Saving makes a draft <code>editing</code> &mdash; it
 reaches editors only when you set it to <code>proposed</code>.</p>
"""


def write_all(out_dir, drafts, new_seqs, other, meta, files):
    """Write every generated file, and return the manifest."""
    man = {}
    for name, text in sorted(files.items()):
        write(os.path.join(out_dir, name), text, man)

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

    payload = {
        "meta": meta,
        "drafts": [{
            "aid": d["aid"], "role": d["role"], "what": d["what"],
            "summary": d["summary"],
            "blocked_on": d.get("blocked_on") or None,
            "edits": for_js(d["edits"]),
            "upload": ({"kind": d["upload"]["kind"],
                        "name": os.path.basename(d["upload"]["path"]),
                        "slot": 0,
                        "desc": d["upload"].get("desc", ""),
                        "content": files[os.path.basename(d["upload"]["path"])]}
                       if d.get("upload") else None),
        } for d in drafts],
    }
    write(os.path.join(out_dir, "payload.js"),
          "window.OEIS_SUBMIT = " + json.dumps(payload, indent=1) + ";\n", man)
    write(os.path.join(out_dir, "fill.js"), FILL_JS % {"port": PORT}, man)
    write(os.path.join(out_dir, "panel.html"), PANEL_HTML, man)

    rows = []
    for i, d in enumerate(drafts, 1):
        f = os.path.basename(d["upload"]["path"]) if d.get("upload") else ""
        st = d.get("status") or ("blocked" if d.get("blocked_on") else "")
        rows.append(
            f'<tr><td class="n">{i}</td>'
            f'<td><a href="{d["url"]}">{d["aid"]}</a></td>'
            f'<td class="what">{d["what"]}</td>'
            f'<td><code>{f}</code></td>'
            f'<td class="warn">{st}</td></tr>')
    extra = ""
    if new_seqs:
        extra += "<h2>New sequences</h2><table>" + "".join(
            f'<tr><td class="n">&mdash;</td>'
            f'<td><a href="{n["url"]}">new</a></td>'
            f'<td class="what">{n["role"]}</td><td></td>'
            f'<td class="warn">{n.get("status") or ""}</td></tr>'
            for n in new_seqs) + "</table>"
    for key in ("blocked", "pending", "review"):
        if other.get(key):
            extra += f"<h2>{key}</h2><table>" + "".join(
                f'<tr><td class="n">&mdash;</td><td><code>{r["id"]}</code></td>'
                f'<td class="what" colspan=3>{r["reason"]}</td></tr>'
                for r in other[key]) + "</table>"

    write(os.path.join(out_dir, "index.html"), INDEX_HTML % {
        "n": len(drafts), "date": meta["date"], "run": meta["run"],
        "check": "pass" if meta["check"] else "FAILING",
        "bm": bookmarklet().replace('"', "&quot;"),
        "port": PORT, "rows": "\n".join(rows), "extra": extra}, man)

    write(os.path.join(out_dir, "edits.yaml"),
          render_yaml(drafts, new_seqs, other, meta), man)
    write(os.path.join(out_dir, "MANIFEST.txt"),
          "# sha256 (first 16) of every generated file in this directory.\n"
          "# oeis_audit.py rewrites them all; edits here are lost.\n"
          + "".join(f"{v}  {k}\n" for k, v in sorted(man.items())
                    if k != "MANIFEST.txt"), {})
    return man
