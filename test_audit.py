#!/usr/bin/env python3
"""Offline regressions for transformed source attribution and checkpoints."""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

import check_oeis
import oeis_audit as audit
import oeis_sources as sources


class PublishedSourcesTests(unittest.TestCase):
    def test_frontier_readers_accept_plain_and_grouped_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "frontier.txt")
            for number in ("12345678901234567", "12,345,678,901,234,567"):
                with open(path, "w") as f:
                    f.write(f"gap {number}\nlonely 0\n")
                self.assertEqual(audit.read_frontier(directory)[0]["gap"], 12345678901234567)
                self.assertEqual(check_oeis.frontiers(directory)["gap"], 12345678901234567)

                with open(os.path.join(directory, "gap.txt"), "w") as f:
                    f.write("# records\n")
                with open(path, "w") as f:
                    f.write(number + "\n")
                self.assertEqual(audit.read_frontier(directory)[0]["gap"], 12345678901234567)
                self.assertEqual(check_oeis.frontiers(directory)["gap"], 12345678901234567)

    def test_balanced_table_transform_and_scan_agreement(self):
        triples = sources.balanced_triples()
        self.assertEqual(len(triples), 72)
        self.assertEqual(triples[5], (1, 3, 2, 7))
        self.assertEqual(triples[53], (2, 47, 6, 59))
        rows = audit.load_rows("fresh", "equidistant")
        matches = sources.balanced_matches(rows)
        self.assertEqual(matches[31],
                         (72, 2422627449333671, 426, 2422627449334523))
        self.assertNotIn(32, matches)
        bad = list(rows[30])
        bad[6] += 2
        with self.assertRaisesRegex(ValueError, "disagrees"):
            sources.balanced_matches([bad])

    def test_first_occurrence_table_preserves_finders_and_unknowns(self):
        rows = {gap: (p, finder) for gap, p, finder in sources.first_gaps()}
        self.assertEqual(rows[1098], (25016149672697549, "other: B. Nyman"))
        self.assertNotIn(1422, rows)  # '?' in this source, not a prime.

    def test_future_witnesses_are_verified_and_follow_current_state(self):
        hits = sources.aloof_checkpoints(8350862685317899, 1152)
        self.assertEqual([(h["prime"], h["below"], h["above"]) for h in hits], [
            (25016149672698647, 1098, 60),
            (28269785077312447, 1038, 142),
            (29835422457878441, 160, 1106)])
        # Once scanned, the first witness is no longer a future checkpoint.
        later = sources.aloof_checkpoints(hits[0]["prime"], 1158, limit=1)
        self.assertEqual(later[0]["prime"], hits[1]["prime"])
        # A stronger intervening record can supersede both earlier witnesses.
        stronger = sources.aloof_checkpoints(8350862685317899, 1200, limit=1)
        self.assertEqual(stronger[0]["prime"], hits[2]["prime"])
        with self.assertRaisesRegex(ValueError, "not consecutive"):
            sources.verify_triple(3, 7, 13)

    def test_submission_credits_prior_triple_without_promoting_witnesses(self):
        rows = audit.load_rows("fresh", "equidistant")[:34]
        families = {"equidistant": {
            "info": audit.FAMILIES["equidistant"], "rows": rows,
            "seqs": [{"aid": "A058867",
                      "m": audit.FAMILIES["equidistant"]["members"]["A058867"]}]}}
        items = [audit.item("terms", "terms:equidistant", "Extend A058867")]
        with patch.object(audit, "bfile_terms_list", return_value=[r[1] for r in rows[:30]]):
            drafts, _, _, files, _, _ = audit.submission(
                items, families, "fresh", False, (True, []))
        draft = drafts[0]
        # A058867's DATA is already past the length editors accept, so the
        # new terms travel in the b-file alone.
        self.assertFalse(any(e["field"] == "Data" for e in draft["edits"]))
        body = [l.split() for l in files["b058867.txt"].splitlines()
                if l and not l.startswith("#")]
        self.assertEqual([int(v) for _, v in body[30:]], [r[1] for r in rows[30:]])
        extensions = [e["text"] for e in draft["edits"] if e["field"] == "Ext"]
        self.assertIn("A052187(72) + 426", extensions[0])
        self.assertIn("Lagrou", extensions[0])
        self.assertFalse(any("a(31)-a(34) from" in e for e in extensions))
        self.assertIn("already tabulated", draft["to_editors"])
        self.assertIn("A052187(72) + 426", files["a058867.txt"])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            audit.published_sources_report(families, "fresh")
        self.assertIn("a(31) = A052187(72) + 426", output.getvalue())


class ExtensionTests(unittest.TestCase):
    def test_data_append_only_while_data_is_complete_and_short(self):
        short = {"data": "2,3,5,7"}
        self.assertTrue(audit.data_append_fits(short, 4, [11, 13]))
        self.assertFalse(audit.data_append_fits(short, 6, [17]),
                         "DATA that stops before the b-file cannot be appended to")
        full = {"data": ",".join(["123456789"] * 25)}  # 249 characters
        self.assertFalse(audit.data_append_fits(full, 25, [1234567890123]))

    def test_prior_credit_keeps_the_existing_b_file_author(self):
        link = ('Dmitry Petukhov, <a href="/A023186/b023186.txt">Table of n, '
                'a(n) for n = 1..56</a> (first 40 terms from Ken Takusagawa)')
        with patch.object(audit, "entry", return_value={"link": [link]}):
            self.assertEqual(
                audit.prior_credit("A023186", 56, False),
                "terms 1..56 from Dmitry Petukhov "
                "(first 40 terms from Ken Takusagawa)")
        with patch.object(audit, "entry", return_value={"link": []}):
            self.assertEqual(audit.prior_credit("A058867", 30, False),
                             "terms 1..30 as previously published")

    def test_extension_gets_a_b_file_instead_of_an_oversized_data_append(self):
        rows = audit.load_rows("fresh", "lonely")[:61]
        families = {"lonely": {
            "info": audit.FAMILIES["lonely"], "rows": rows,
            "seqs": [{"aid": "A023186",
                      "m": audit.FAMILIES["lonely"]["members"]["A023186"]}]}}
        items = [audit.item("terms", "terms:lonely", "Extend A023186"),
                 audit.item("afile", "a-file:lonely", "a-file")]
        rec = {"data": ",".join(str(r[1]) for r in rows[:38]),
               "link": ['Dmitry Petukhov, <a href="/A023186/b023186.txt">'
                        'Table of n, a(n) for n = 1..56</a>']}
        with patch.object(audit, "bfile_terms_list",
                          return_value=[r[1] for r in rows[:56]]), \
             patch.object(audit, "entry", return_value=rec):
            drafts, _, _, files, _, _ = audit.submission(
                items, families, "fresh", False, (True, []))
        d = drafts[0]
        self.assertFalse(any(e["field"] == "Data" for e in d["edits"]))
        self.assertEqual([(u["kind"], u["rows"]) for u in d["uploads"]],
                         [("b-file", 61), ("a-file", 60)])
        # OEIS rewrites the b-file link itself on upload; the draft does not.
        self.assertFalse(any(e["field"] == "Link" and "b023186" in e.get("text", "")
                             for e in d["edits"]))
        self.assertTrue(d["uploads"][0]["published"])
        self.assertIn("Terms 1..56 from Dmitry Petukhov", files["b023186.txt"])
        body = [l for l in files["b023186.txt"].splitlines()
                if not l.startswith("#")]
        self.assertEqual(body[-1], f"61 {rows[60][1]}")
        self.assertIn("Terms 57..61 are new.", files["b023186.txt"])


class MarkdownTests(unittest.TestCase):
    def test_report_becomes_headings_prose_and_fenced_tables(self):
        text = "\n".join([
            "", "COVERAGE  --  where terms are", "=============================",
            "", "A family is one set", "of records.", "",
            "gap -- maximal prime gaps", "-------------------------",
            "  sequence   DATA", "  A002386      31", "! A005669      36",
            "-------------------------", "  deepest member: 85 terms.", "",
            "  wrote 13 files", ""])
        self.assertEqual(audit.to_markdown(text).split("\n")[4:], [
            "## COVERAGE  --  where terms are", "",
            "A family is one set", "of records.", "",
            "### gap -- maximal prime gaps", "",
            "```", "  sequence   DATA", "  A002386      31", "! A005669      36",
            "-------------------------", "  deepest member: 85 terms.", "```", "",
            "```", "  wrote 13 files", "```", ""])

    def test_markdown_option_writes_what_was_printed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "audit.md")
            with patch.object(sys, "argv", ["oeis_audit.py", "--markdown", path]), \
                 patch.object(audit, "run_audit",
                              side_effect=lambda args: print("HEAD\n====\n\n  row") or 0), \
                 contextlib.redirect_stdout(io.StringIO()) as shown:
                self.assertEqual(audit.main(), 0)
            self.assertEqual(shown.getvalue(), "HEAD\n====\n\n  row\n")
            with open(path) as f:
                self.assertIn("## HEAD\n\n```\n  row\n```\n", f.read())


if __name__ == "__main__":
    unittest.main(warnings="ignore")
