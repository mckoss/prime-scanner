
(function () {
  var PORT = 8017, ORIGIN = 'http://localhost:' + PORT;
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
  // A b-file an earlier save of this draft already uploaded: OEIS points the
  // b-file link at the stored copy, renamed b<nnnnnn>_<k>.txt when the name
  // is taken. Only a link the published entry did not have counts.
  function uploadedAs(u) {
    if (u.kind !== 'b-file') return null;
    var stem = u.name.replace(/\.txt$/, ''), re = new RegExp(
      '/' + SEQ + '/(' + stem + '(_\\d+)?\\.txt)', 'g'), m;
    var cur = read('Link') || '';
    while ((m = re.exec(cur)))
      if (m[2] || !u.published) return m[1];
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

  var draft = null, panel = null;

  function states() {
    if (!draft) return [];
    return draft.edits.map(function (e) {
      var p = plan(e);
      return { field: e.field, code: e.code, action: e.action,
               done: !!p.done, err: p.err || null, wait: p.wait || null,
               cur: read(e.field), next: p.val || null };
    });
  }

  function post(msg) {
    if (panel && panel.contentWindow)
      panel.contentWindow.postMessage(msg, ORIGIN);
  }
  function report() {
    post({ type: 'STATE', seq: SEQ, states: states(),
           uploads: draft ? (draft.uploads || []).map(function (u) {
             return { name: u.name, slot: holder(u.name),
                      uploaded: uploadedAs(u) }; }) : [],
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
      var errs = {};
      (draft.uploads || []).forEach(function (u, i) {
        var r = attach(u);
        if (r.err) errs[i] = r.err;
      });
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
    } else if (m.type === 'WIDTH') {
      panel.style.width = m.px + 'px';
      document.body.style.marginRight = m.px + 'px';
    }
  });

  panel = document.createElement('iframe');
  panel.src = ORIGIN + '/panel.html#' + encodeURIComponent(SEQ || '');
  panel.style.cssText = 'position:fixed;top:0;right:0;width:340px;height:100%;'
    + 'border:0;border-left:1px solid #999;z-index:2147483647;background:#fff';
  document.body.style.marginRight = '340px';
  document.body.appendChild(panel);

  window.__oeisFill = { rescan: report };
})();
