import json
import os
import tempfile
import unittest

from detect_changes import detect_changes, detect_renumberings, is_minor_change


class TestMinorChangeDetection(unittest.TestCase):
    def test_typo_correction_is_minor(self):
        self.assertTrue(is_minor_change("Sprachliche Klarstellung in Absatz 2 (Tippfehler-Korrektur)"))

    def test_substantive_change_is_not_minor(self):
        self.assertFalse(is_minor_change("Schwellenwert gesenkt"))

    def test_empty_comment_is_not_minor(self):
        self.assertFalse(is_minor_change(""))
        self.assertFalse(is_minor_change(None))


class TestRenumberingDetection(unittest.TestCase):
    def test_same_hash_detects_renumbering(self):
        removed = [{"gesetz": "ABC", "paragraph": "§1", "titel": "Foo", "text_hash": "h1"}]
        added = [{"gesetz": "ABC", "paragraph": "§1a", "titel": "Foo", "text_hash": "h1"}]
        renumberings, rem_r, rem_a = detect_renumberings(removed, added)
        self.assertEqual(len(renumberings), 1)
        self.assertEqual(len(rem_r), 0)
        self.assertEqual(len(rem_a), 0)

    def test_similar_title_detects_renumbering(self):
        removed = [{"gesetz": "ABC", "paragraph": "§15", "titel": "Anzeige bei Änderungen", "text_hash": "h1"}]
        added = [{"gesetz": "ABC", "paragraph": "§15a", "titel": "Anzeige bei Änderungen", "text_hash": "h2"}]
        renumberings, rem_r, rem_a = detect_renumberings(removed, added)
        self.assertEqual(len(renumberings), 1)

    def test_different_laws_not_matched(self):
        removed = [{"gesetz": "ABC", "paragraph": "§1", "titel": "Foo", "text_hash": "h1"}]
        added = [{"gesetz": "XYZ", "paragraph": "§2", "titel": "Foo", "text_hash": "h1"}]
        renumberings, rem_r, rem_a = detect_renumberings(removed, added)
        self.assertEqual(len(renumberings), 0)


class TestFullDiff(unittest.TestCase):
    def _write_csv(self, path, rows):
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("gesetz;paragraph;titel;text_hash;status;gueltig_ab;kommentar\n")
            for r in rows:
                f.write(";".join(r) + "\n")

    def test_detects_all_change_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_p = os.path.join(tmp, "old.csv")
            new_p = os.path.join(tmp, "new.csv")

            self._write_csv(old_p, [
                ["X", "§1", "Same", "h1", "in_force", "2020-01-01", ""],
                ["X", "§2", "Modified", "h2", "in_force", "2020-01-01", ""],
                ["X", "§3", "Repealed", "h3", "in_force", "2020-01-01", ""],
                ["X", "§4", "Renumbered", "h4", "in_force", "2020-01-01", ""],
            ])

            self._write_csv(new_p, [
                ["X", "§1", "Same", "h1", "in_force", "2020-01-01", ""],
                ["X", "§2", "Modified", "h2_new", "in_force", "2025-01-01", "Schwellenwert angepasst"],
                ["X", "§3", "Repealed", "h3", "aufgehoben", "2020-01-01", "Aufgehoben"],
                ["X", "§4a", "Renumbered", "h4", "in_force", "2025-01-01", "Umnummeriert"],
                ["X", "§5", "Brand new", "h5", "in_force", "2025-01-01", "Neuer Paragraph"],
            ])

            changes = detect_changes(old_p, new_p)
            types = {c["type"] for c in changes}
            self.assertIn("MODIFIED", types)
            self.assertIn("REPEALED", types)
            self.assertIn("RENUMBERED", types)
            self.assertIn("NEW", types)

            all_refs = [c.get("paragraph") for c in changes] + [c.get("old_paragraph") for c in changes]
            self.assertNotIn("§1", all_refs)

    def test_substantive_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_p = os.path.join(tmp, "old.csv")
            new_p = os.path.join(tmp, "new.csv")

            self._write_csv(old_p, [
                ["X", "§1", "A", "h1", "in_force", "2020-01-01", ""],
                ["X", "§2", "B", "h2", "in_force", "2020-01-01", ""],
            ])

            self._write_csv(new_p, [
                ["X", "§1", "A", "h1_new", "in_force", "2025-01-01", "Tippfehler korrigiert"],
                ["X", "§2", "B", "h2_new", "in_force", "2025-01-01", "Schwellenwert gesenkt"],
            ])

            changes = detect_changes(old_p, new_p)
            sub = [c for c in changes if c.get("substantive")]
            minor = [c for c in changes if not c.get("substantive", True)]
            self.assertEqual(len(sub), 1)
            self.assertEqual(len(minor), 1)


if __name__ == "__main__":
    unittest.main()
