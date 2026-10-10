#!/usr/bin/env python3
"""Offline tests for oeis_serve.py: how it rewrites oeis/submissions.txt."""
import os
import tempfile
import unittest

import oeis_serve as serve

HEADER = "# Progress on the drafts.\n#\n#   <item id>  <status>  [date]  [note]\n\n"


class SubmissionsFileTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "submissions.txt")

    def tearDown(self):
        self.dir.cleanup()

    def write(self, text):
        with open(self.path, "w") as f:
            f.write(text)

    def read(self):
        with open(self.path) as f:
            return f.read()

    def test_appends_one_line_for_the_whole_edit(self):
        self.write(HEADER + "a-file:A005250  declined  2026-09-30  no\n")
        line = serve.update_submissions(self.path, ["terms:x", "b-file:A000001"],
                                        "submitted", "2026-10-10", "one edit")
        self.assertEqual(line, "terms:x,b-file:A000001  submitted  2026-10-10  one edit")
        self.assertEqual(self.read(), HEADER + "a-file:A005250  declined  2026-09-30  no\n"
                         + line + "\n")

    def test_a_new_status_replaces_the_old_one(self):
        self.write(HEADER + "terms:x,a-file:x  submitted  2026-10-10  saved\n"
                   "bound:x  skip  2026-10-10\n")
        serve.update_submissions(self.path, ["terms:x", "a-file:x"], "approved",
                                 "2026-10-20")
        self.assertEqual(self.read(), HEADER + "bound:x  skip  2026-10-10\n"
                         "terms:x,a-file:x  approved  2026-10-20\n")

    def test_an_id_moving_off_a_shared_line_leaves_the_rest(self):
        self.write(HEADER + "terms:x,a-file:x  submitted  2026-10-10  saved\n")
        serve.update_submissions(self.path, ["a-file:x"], "declined", "2026-10-20")
        self.assertEqual(self.read(), HEADER + "terms:x  submitted  2026-10-10  saved\n"
                         "a-file:x  declined  2026-10-20\n")

    def test_record_validates_and_closes_the_open_draft(self):
        self.write(HEADER + "terms:x  submitted  2026-10-10\n"
                   "draft:A000001  submitted  2026-10-10\n")
        code, out = serve.record({"ids": ["terms:x"], "status": "approved",
                                  "aid": "A000001", "note": "rev 9\nok"},
                                 self.path, "2026-10-20")
        self.assertEqual(code, 200)
        self.assertEqual(out["line"], "terms:x,draft:A000001  approved  2026-10-20  rev 9 ok")
        self.assertNotIn("draft:A000001  submitted", self.read())

    def test_record_leaves_the_draft_open_while_in_review(self):
        self.write(HEADER + "draft:A000001  submitted  2026-10-10\n")
        _, out = serve.record({"ids": ["terms:x"], "status": "submitted",
                               "aid": "A000001"}, self.path, "2026-10-20")
        self.assertEqual(out["line"], "terms:x  submitted  2026-10-20")
        self.assertIn("draft:A000001  submitted  2026-10-10", self.read())

    def test_record_refuses_malformed_bodies(self):
        self.write(HEADER)
        for body in ({"ids": [], "status": "submitted"},
                     {"ids": ["terms:x y"], "status": "submitted"},
                     {"ids": ["a,b:c"], "status": "submitted"},
                     {"ids": ["terms:x"], "status": "done"},
                     {"ids": ["terms:x"], "status": "submitted", "aid": "x"},
                     {"ids": "terms:x", "status": "submitted"}):
            self.assertEqual(serve.record(body, self.path)[0], 400, body)
        self.assertEqual(self.read(), HEADER)


if __name__ == "__main__":
    unittest.main()
