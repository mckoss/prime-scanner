#!/usr/bin/env python3
"""Offline regressions for transformed source attribution and checkpoints."""
import contextlib
import io
import unittest
from unittest.mock import patch

import oeis_audit as audit
import oeis_sources as sources


class PublishedSourcesTests(unittest.TestCase):
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
        data = next(e for e in draft["edits"] if e["field"] == "Data")
        self.assertEqual([r[0] for r in data["terms"]], [r[1] for r in rows[30:]])
        extensions = [e["text"] for e in draft["edits"] if e["field"] == "Ext"]
        self.assertIn("A052187(72) + 426", extensions[0])
        self.assertIn("Lagrou", extensions[0])
        self.assertFalse(any("a(31)-a(34) from" in e for e in extensions))
        self.assertIn("already tabulated", draft["to_editors"])
        self.assertIn("A052187(72) + 426", files["a058867.txt"])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            audit.published_sources_report(families, "fresh")
        self.assertIn("a(31) = A052187(72) + 426", output.getvalue())


if __name__ == "__main__":
    unittest.main(warnings="ignore")
