#!/usr/bin/env python3
"""Serve oeis/submit/ for the bookmarklet, and keep oeis/submissions.txt.

`make submit` runs this in place of a plain static server. Everything under
oeis/submit/ is served as before; the one addition is

    POST /submissions   {"ids": [...], "status": "...", "note": "...",
                         "aid": "A000000"}

which records those items on one line of oeis/submissions.txt -- the items
one OEIS edit settled together -- dated today, then reruns the audit so the
worklist, edits.yaml and the panel's payload drop what is now settled. The
panel posts here when Save Changes completes a draft, or on its Record
button; the worklist posts here to mark a draft submitted, approved or
declined.

It listens on localhost only and takes writes only from its own pages: a
request from any other origin is refused, and a JSON body cannot be sent
cross-origin without a preflight this server never grants.
"""

import argparse
import datetime
import functools
import http.server
import json
import os
import re
import socket
import subprocess
import sys
import threading

import oeis_audit as audit
import oeis_submit

ROOT = os.path.dirname(os.path.abspath(__file__))
SERVE = os.path.join(ROOT, "oeis", "submit")
ID = re.compile(r"[a-z-]+:[A-Za-z0-9:-]+")
LOCK = threading.Lock()


def update_submissions(path, ids, status, date, note=""):
    """Record `ids` on one line of submissions.txt, and return that line.

    An id already on another line is taken off it -- the line is dropped
    once it names nothing -- so each item has exactly one status, the
    newest. Comments and every other line are kept as they are.
    """
    ids = list(dict.fromkeys(ids))
    gone = set(ids)
    lines = []
    if os.path.exists(path):
        with open(path) as f:
            lines = f.read().splitlines()
    out = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            out.append(line)
            continue
        first, rest = (s.split(None, 1) + [""])[:2]
        keep = [i for i in first.split(",") if i and i not in gone]
        if not keep:
            continue
        if len(keep) == len(first.split(",")):
            out.append(line)
        else:
            out.append(f"{','.join(keep)}  {rest}")
    new = f"{','.join(ids)}  {status}  {date}  {note}".rstrip()
    while out and not out[-1].strip():
        out.pop()
    out.append(new)
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")
    return new


def open_draft_ids(path, aid):
    """[`draft:<aid>`] if submissions.txt holds that line, else []."""
    if not aid or not os.path.exists(path):
        return []
    want = f"draft:{aid}"
    with open(path) as f:
        for line in f:
            s = line.strip()
            if (s and not s.startswith("#")
                    and want in s.split(None, 1)[0].split(",")):
                return [want]
    return []


def record(body, path=None, today=None):
    """Validate a POST body and record it; return (status code, reply)."""
    path = path or audit.SUBMISSIONS
    ids = body.get("ids")
    status = body.get("status")
    note = " ".join(str(body.get("note") or "").split())
    aid = body.get("aid") or ""
    if (not isinstance(ids, list) or not ids
            or not all(isinstance(i, str) and ID.fullmatch(i) for i in ids)):
        return 400, {"error": "ids must be a list of item ids"}
    if status not in audit.STATUSES:
        return 400, {"error": f"status must be one of {', '.join(audit.STATUSES)}"}
    if aid and not re.fullmatch(r"A\d{6}", aid):
        return 400, {"error": "aid must be an A-number"}
    # A review that has ended closes the sequence's open draft with it.
    if status in audit.CLOSED_STATUSES:
        ids = ids + [i for i in open_draft_ids(path, aid) if i not in ids]
    date = today or datetime.date.today().isoformat()
    line = update_submissions(path, ids, status, date, note)
    return 200, {"ok": True, "line": line}


def rerun_audit():
    """`make audit`, as `make submit` ran it at startup; (ok, output tail)."""
    p = subprocess.run(["make", "-s", "audit"], cwd=ROOT, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode == 0, "\n".join(p.stdout.splitlines()[-5:])


def audit_in_background():
    with LOCK:
        ok, tail = rerun_audit()
    if not ok:
        print(f"  ! audit failed after recording:\n{tail}", flush=True)


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # The panel and payload change with every audit; never serve stale.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def reply(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/submissions":
            return self.reply(404, {"error": "no such endpoint"})
        port = self.server.server_address[1]
        if self.headers.get("Origin") not in (f"http://localhost:{port}",
                                              f"http://127.0.0.1:{port}"):
            return self.reply(403, {"error": "writes come from this server's "
                                             "own pages only"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self.reply(400, {"error": "body must be JSON"})
        if not isinstance(body, dict):
            return self.reply(400, {"error": "body must be a JSON object"})
        with LOCK:
            code, out = record(body)
            if code == 200:
                print(f"  recorded: {out['line']}", flush=True)
                # A save from the panel does not wait: the OEIS page is
                # navigating away and nothing will read the new audit.
                if body.get("wait", True):
                    out["audit_ok"], out["audit"] = rerun_audit()
                else:
                    threading.Thread(target=audit_in_background).start()
        self.reply(code, out)


def serve(port):
    """Listen on 127.0.0.1 and, where the machine has it, ::1 -- browsers
    resolve localhost to either -- and never on an outside interface."""
    handler = functools.partial(Handler, directory=SERVE)
    servers = [http.server.HTTPServer(("127.0.0.1", port), handler)]
    try:
        class V6(http.server.HTTPServer):
            address_family = socket.AF_INET6
        servers.append(V6(("::1", port), handler))
    except OSError:
        pass
    for s in servers[1:]:
        threading.Thread(target=s.serve_forever, daemon=True).start()
    print(f"  open http://localhost:{port}/", flush=True)
    try:
        servers[0].serve_forever()
    except KeyboardInterrupt:
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=oeis_submit.PORT)
    serve(ap.parse_args().port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
