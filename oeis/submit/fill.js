
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
  panel.style.cssText = 'position:fixed;top:0;right:0;width:340px;height:100%;'
    + 'border:0;border-left:1px solid #999;z-index:2147483647;background:#fff';
  document.body.style.marginRight = '340px';
  document.body.appendChild(panel);

  window.__oeisFill = { rescan: report };
})();
