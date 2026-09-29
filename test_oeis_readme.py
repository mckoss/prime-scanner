"""The README generator must reflect the scan and reject bad scan data."""

from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import oeis_readme


class ReadmeGenerationTests(unittest.TestCase):
    def test_progress_follows_current_records_and_frontier(self):
        directory = oeis_readme.ROOT / "fresh"
        frontiers, rows = oeis_readme.scan(directory)
        text = oeis_readme.progress(directory, frontiers, rows)
        self.assertIn(f"{frontiers['aloof']:,}", text)
        self.assertIn(f"latest aloof({rows['aloof'][-1][0]})", text)
        self.assertIn(f"| {len(rows['aloof'])} | "
                      f"{len(oeis_readme.published('aloof-lower')) + 1} | "
                      f"{frontiers['aloof']:,} |", text)

    def test_bad_scan_leaves_readme_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "scan"
            results.mkdir()
            for path in (oeis_readme.ROOT / "fresh").glob("*.txt"):
                if path.name in {"frontier.txt", "gap.txt", "lonely.txt",
                                 "aloof.txt", "equidistant.txt", "pairwise.txt",
                                 "balanced.txt"}:
                    shutil.copyfile(path, results / path.name)
            aloof = results / "aloof.txt"
            lines = aloof.read_text().splitlines(keepends=True)
            aloof.write_text("".join(lines[:2] + lines[3:]))
            readme = Path(tmp) / "README.md"
            readme.write_text("original\n")
            with patch.object(oeis_readme, "README", readme), \
                 patch.object(sys, "argv", ["oeis_readme.py", "--results", str(results)]):
                with self.assertRaisesRegex(ValueError, "check_oeis.py failed"):
                    oeis_readme.main()
            self.assertEqual(readme.read_text(), "original\n")


if __name__ == "__main__":
    unittest.main(warnings="ignore")
