// Tests oeis/submit/fill.js against a stub of the OEIS edit form.
//
// The form submits each field's innerHTML, not its text (its copyone() does
// `v.value = text(el)` where text() returns innerHTML), so the shim reads a
// field by unescaping innerHTML and writes it by setting textContent. That
// round-trip, the Cf. splice and the DATA anchor check are the parts most
// able to corrupt a real submission, so they are exercised here rather than
// discovered on oeis.org.
//
//   node test_fill.js
'use strict';
const fs = require('fs');
const path = require('path');

const DIR = path.join(__dirname, 'oeis', 'submit');
let fails = 0, passes = 0;

function eq(got, want, what) {
  if (got === want) { passes++; return; }
  fails++;
  console.log(`  FAIL ${what}\n    got:  ${JSON.stringify(got)}\n` +
              `    want: ${JSON.stringify(want)}`);
}
function ok(cond, what) { eq(!!cond, true, what); }

// --- a stub of just enough of the edit page ------------------------------
function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
                  .replace(/>/g, '&gt;');
}
function unesc(s) {
  return String(s).replace(/&lt;/g, '<').replace(/&gt;/g, '>')
                  .replace(/&amp;/g, '&');
}

function makePage(fields, opts) {
  opts = opts || {};
  const els = {};
  for (const k in fields) {
    els['edit_' + k] = { _t: fields[k],
      get innerHTML() { return esc(this._t); },
      set innerHTML(v) { this._t = unesc(v); },
      set textContent(v) { this._t = v; },
      get textContent() { return this._t; } };
  }
  const uploads = {};
  if (opts.upload) {
    uploads['upload_file0'] = { name: 'upload_file0', files: null,
                                dispatchEvent() { this.dispatched = true; } };
    els['upload_bfile0'] = { checked: false,
                             click() { this.checked = true; } };
    els['edit_upload_0'] = { _t: '',
      get innerHTML() { return esc(this._t); },
      set textContent(v) { this._t = v; }, get textContent() { return this._t; } };
  }
  const sent = [];
  const page = {
    els, uploads, sent, handler: null, navigated: null,
    field(f) { return els['edit_' + f] ? els['edit_' + f]._t : null; },
  };
  const iframe = { style: {}, contentWindow: {
    postMessage(m) { sent.push(m); } } };
  const doc = {
    body: { style: {}, appendChild() {} },
    head: { appendChild() {} },
    getElementById(id) { return els[id] || null; },
    querySelector(sel) {
      const m = /input\[name=(\w+)\]/.exec(sel);
      if (!m) return null;
      if (m[1] === 'seq') return { value: opts.seq || 'A000000' };
      return uploads[m[1]] || null;
    },
    createElement(tag) {
      if (tag === 'iframe') return iframe;
      // read() round-trips through a textarea to decode entities, exactly as
      // a browser would; the stub has to honour that or it tests nothing.
      if (tag === 'textarea') {
        return { _v: '', set innerHTML(v) { this._v = unesc(v); },
                 get value() { return this._v; } };
      }
      return { style: {} };
    },
  };
  const win = {
    addEventListener(t, fn) { if (t === 'message') page.handler = fn; },
    get location() { return { pathname: opts.pathname || '/edit',
                              set href(u) { page.navigated = u; } }; },
  };
  // location is read for pathname and written for navigation
  const loc = { pathname: opts.pathname || '/edit', href: '' };
  Object.defineProperty(loc, 'href', {
    get() { return ''; }, set(u) { page.navigated = u; } });
  page.run = function (src) {
    const fn = new Function('document', 'window', 'location',
                            'DataTransfer', 'File', 'Event', src);
    fn(doc, win, loc,
       function () { this.items = { add: (f) => { this._f = f; } };
                     Object.defineProperty(this, 'files',
                       { get: () => [this._f] }); },
       function (parts, name) { this.parts = parts; this.name = name; },
       function (t) { this.type = t; });
  };
  page.post = function (msg) {
    page.handler({ origin: 'http://localhost:8017', data: msg });
  };
  page.last = function () { return sent[sent.length - 1]; };
  return page;
}

const SRC = fs.readFileSync(path.join(DIR, 'fill.js'), 'utf8');

// --- Xref: splice into the existing Cf. line -----------------------------
{
  const cur = 'Cf. A031132 (record distances corresponding to a(2) onward), ' +
              'A023186 (lonely primes), A087770 (lonely primes, another ' +
              'definition).';
  const p = makePage({ Xref: cur }, { seq: 'A096265' });
  p.run(SRC);
  p.post({ type: 'READY', draft: { aid: 'A096265', edits: [
    { field: 'Xref', action: 'add',
      add: [['A031133', 'lower neighbor'], ['A031134', 'upper neighbor']] }] } });
  p.post({ type: 'FILL', index: 0 });
  eq(p.field('Xref'),
     'Cf. A031132 (record distances corresponding to a(2) onward), ' +
     'A023186 (lonely primes), A087770 (lonely primes, another definition), ' +
     'A031133 (lower neighbor), A031134 (upper neighbor).',
     'Xref splices before the trailing period');

  // second application must be a no-op, not a duplicate
  p.post({ type: 'FILL', index: 0 });
  ok(!/A031133.*A031133/s.test(p.field('Xref')), 'Xref fill is idempotent');
  ok(p.last().states[0].done, 'Xref reports done once applied');
}

// --- Xref: no Cf. line yet ----------------------------------------------
{
  const p = makePage({ Xref: '' }, { seq: 'A031132' });
  p.run(SRC);
  p.post({ type: 'READY', draft: { aid: 'A031132', edits: [
    { field: 'Xref', action: 'add', add: [['A096265', 'the aloof prime']] }] } });
  p.post({ type: 'FILL', index: 0 });
  eq(p.field('Xref'), 'Cf. A096265 (the aloof prime).', 'Xref creates a Cf. line');
}

// --- Data: append only when the anchor matches --------------------------
{
  const cur = '2, 3, 7, 23, 89, 9551, 9587, 15683, 155921, 360653, 370261, ' +
              '9156364643509';
  const p = makePage({ Data: cur }, { seq: 'A087770' });
  p.run(SRC);
  const edit = { field: 'Data', action: 'append', after_n: 12,
                 after_n_term: 9156364643509,
                 terms: [26459479056379, 64293760159177] };
  p.post({ type: 'READY', draft: { aid: 'A087770', edits: [edit] } });
  p.post({ type: 'FILL', index: 0 });
  eq(p.field('Data'), cur + ', 26459479056379, 64293760159177',
     'Data appends past the anchor');
  p.post({ type: 'RESCAN' });
  ok(p.last().states[0].done, 'Data reports done once appended');
}
{
  // published data moved under us: refuse, do not guess
  const p = makePage({ Data: '2, 3, 7, 999999' }, { seq: 'A087770' });
  p.run(SRC);
  p.post({ type: 'READY', draft: { aid: 'A087770', edits: [
    { field: 'Data', action: 'append', after_n: 12,
      after_n_term: 9156364643509, terms: [26459479056379] }] } });
  const st = p.last().states[0];
  ok(/DATA ends at 999999/.test(st.err || ''), 'Data refuses a moved anchor');
  p.post({ type: 'FILL', index: 0 });
  eq(p.field('Data'), '2, 3, 7, 999999', 'refused Data is left untouched');
}

// --- Link: replace only the b-file line ---------------------------------
{
  const cur = 'Hugo Pfoertner, <a href="/A096265/b096265.txt">Table of n, ' +
              'a(n) for n = 1..55</a>, terms 1..50 from Ken Takusagawa.\n' +
              'Eric Weisstein, <a href="http://example.com">Aloof Prime</a>';
  const p = makePage({ Link: cur }, { seq: 'A096265' });
  p.run(SRC);
  const text = 'Mike Koss, <a href="/A096265/b096265.txt">Table of n, a(n) ' +
               'for n = 1..68</a>, terms 1..50 from Ken Takusagawa.';
  p.post({ type: 'READY', draft: { aid: 'A096265', edits: [
    { field: 'Link', action: 'replace_bfile_link',
      needle: 'b096265.txt', text: text }] } });
  p.post({ type: 'FILL', index: 0 });
  const lines = p.field('Link').split('\n');
  eq(lines[0], text, 'b-file link line replaced');
  eq(lines[1], 'Eric Weisstein, <a href="http://example.com">Aloof Prime</a>',
     'other link lines untouched');
  ok(/<a href="\/A096265\/b096265\.txt">/.test(p.els.edit_Link.innerHTML
       .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&')),
     'angle brackets survive the innerHTML round-trip');
}

// --- Comment: add, and do not re-add ------------------------------------
{
  const p = makePage({ Comment: 'Erdos and Suranyi call these reclusive ' +
                                'primes. - _T. D. Noe_, Jul 21 2006' },
                     { seq: 'A023186' });
  p.run(SRC);
  const text = 'There is no further term below 2.1*10^15: an exhaustive ' +
               'scan from 0 to 2174619685091850 finds none. - ~~~~';
  p.post({ type: 'READY', draft: { aid: 'A023186', edits: [
    { field: 'Comment', action: 'add', text: text }] } });
  p.post({ type: 'FILL', index: 0 });
  ok(p.field('Comment').endsWith(text), 'comment appended on its own line');
  ok(/Erdos and Suranyi/.test(p.field('Comment')), 'existing comment kept');
  p.post({ type: 'FILL', index: 0 });
  eq(p.field('Comment').split('There is no further').length, 2,
     'comment is not added twice');
}

// --- uploads -------------------------------------------------------------
{
  const p = makePage({ Link: '' }, { seq: 'A096265', upload: true });
  p.run(SRC);
  p.post({ type: 'READY', draft: { aid: 'A096265', edits: [], upload: {
    kind: 'b-file', name: 'b096265.txt', slot: 0,
    content: '1 2\n2 3\n', desc: 'Table of n, a(n) for n = 1..68' } } });
  p.post({ type: 'ATTACH' });
  const inp = p.uploads.upload_file0;
  ok(inp.files && inp.files[0].name === 'b096265.txt', 'file attached to slot 0');
  ok(inp.dispatched, 'change event dispatched');
  ok(p.els.upload_bfile0.checked, 'b-file checkbox ticked');
  eq(p.els.edit_upload_0.textContent, 'Table of n, a(n) for n = 1..68',
     'upload description filled');
}

// --- navigation goes through the shim, never the iframe ------------------
{
  const p = makePage({ Xref: '' }, { seq: 'A000101' });
  p.run(SRC);
  p.post({ type: 'READY', draft: { aid: 'A000101', edits: [] } });
  p.post({ type: 'NAVIGATE', url: 'https://oeis.org/edit?seq=A002386' });
  eq(p.navigated, 'https://oeis.org/edit?seq=A002386', 'NAVIGATE sets location');
}

// --- a message from anywhere else is ignored -----------------------------
{
  const p = makePage({ Xref: 'Cf. A000040.' }, { seq: 'A000101' });
  p.run(SRC);
  p.post({ type: 'READY', draft: { aid: 'A000101', edits: [
    { field: 'Xref', action: 'add', add: [['A053695', '']] }] } });
  p.handler({ origin: 'https://evil.example',
              data: { type: 'FILL', index: 0 } });
  eq(p.field('Xref'), 'Cf. A000040.', 'cross-origin message ignored');
}


// --- the generated payload must match the shapes fill.js expects ---------
// The YAML keeps Xref adds as a mapping and DATA terms as [value, why] pairs
// because that reads better; fill.js wants ordered pairs and bare values.
// Python converts on the way into payload.js. If that ever stops happening,
// a Cf. splice would insert single characters and a DATA append would insert
// "[object Object]", both silently -- so check it here.
{
  const src = fs.readFileSync(path.join(DIR, 'payload.js'), 'utf8');
  const P = new Function(
    'window', src + '; return window.OEIS_SUBMIT;')({});
  let xrefs = 0, datas = 0, uploads = 0;
  for (const d of P.drafts) {
    for (const e of d.edits) {
      if (e.field === 'Xref') {
        xrefs++;
        ok(Array.isArray(e.add), `${d.aid} Xref.add is an array`);
        ok(e.add.every(a => Array.isArray(a) && a.length === 2 &&
                            /^A\d{6}$/.test(a[0])),
           `${d.aid} Xref.add holds [A-number, note] pairs`);
      }
      if (e.field === 'Data') {
        datas++;
        ok(e.terms.every(t => typeof t === 'number'),
           `${d.aid} Data.terms are bare numbers`);
        ok(typeof e.after_n_term === 'number',
           `${d.aid} Data has a numeric anchor term`);
      }
      if (e.action === 'replace_bfile_link')
        ok(typeof e.needle === 'string' && e.needle.endsWith('.txt'),
           `${d.aid} b-file link edit names the file to replace`);
    }
    if (d.upload) {
      uploads++;
      ok(typeof d.upload.content === 'string' && d.upload.content.length > 0,
         `${d.aid} upload carries its file contents`);
      ok(/^[ -~\n]*$/.test(d.upload.content),
         `${d.aid} upload is plain ASCII, as the b-file spec requires`);
    }
  }
  ok(xrefs > 0 && datas > 0 && uploads > 0,
     `payload exercised: ${xrefs} Xref, ${datas} Data, ${uploads} uploads`);
}

console.log(`${passes} passed, ${fails} failed`);
process.exit(fails ? 1 : 0);
