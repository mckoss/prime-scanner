
(function () {
  var PORT = 8017, ORIGIN = 'http://localhost:' + PORT;
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
  // A file an earlier save of this draft already uploaded. OEIS writes a %H
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

  // An extended b-file's %H line must credit whoever computed the earlier
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
  panel.style.cssText = 'position:fixed;top:0;right:0;width:340px;height:100%;'
    + 'border:0;border-left:1px solid #999;z-index:2147483647;background:#fff';
  document.body.style.marginRight = '340px';
  document.body.appendChild(panel);

  window.__oeisFill = { rescan: report };
})();
