import json
import os
import shutil
import tempfile
import unittest

from cardfinder.status import discontinue, parse_command

NAMES = {"usbank-split": "Split Card World Mastercard", "usbank-other": "Other Card"}


class ParseCommand(unittest.TestCase):
    def test_the_two_commands(self):
        self.assertEqual(parse_command("/discontinued"), "discontinued")
        self.assertEqual(parse_command("/still-active"), "still-active")

    def test_case_and_trailing_text_are_fine(self):
        self.assertEqual(parse_command("/Discontinued thanks, checked the site"), "discontinued")
        self.assertEqual(parse_command("  /still-active\nit is on the app page"), "still-active")

    def test_a_command_that_is_not_the_first_word_does_not_count(self):
        self.assertIsNone(parse_command("I think /discontinued"))

    def test_other_comments_and_empty_input_are_ignored(self):
        for text in ("looks fine", "/discontinue", "", None, "/removed"):
            self.assertIsNone(parse_command(text), text)


class Discontinue(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.paths = {k: os.path.join(self.dir, v) for k, v in
                      {"discontinued": "d.json", "offers": "o.json", "fees": "f.json", "waived": "w.json", "changelog": "c.md"}.items()}
        self._write("discontinued", {})
        self._write("offers", {"usbank-split": {"seen": "2026-09-01", "text": "x"}, "usbank-other": {"seen": "2026-09-01", "text": "y"}})
        self._write("fees", {"usbank-split": 0.0, "usbank-other": 95.0})
        self._write("waived", ["usbank-other", "usbank-split"])
        with open(self.paths["changelog"], "w") as f:
            f.write("What changed.\n\n## 2026-09-20\n- Older.\n")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def _write(self, key, value):
        with open(self.paths[key], "w") as f:
            json.dump(value, f)

    def _read(self, key):
        with open(self.paths[key]) as f:
            return json.load(f)

    def test_records_the_card_and_removes_only_its_cached_data(self):
        self.assertEqual(discontinue("usbank-split", NAMES, "2026-09-29", 12, self.paths), "Split Card World Mastercard")
        entry = self._read("discontinued")["usbank-split"]
        self.assertEqual(entry["date"], "2026-09-29")
        self.assertIn("#12", entry["note"])
        self.assertEqual(list(self._read("offers")), ["usbank-other"])
        self.assertEqual(self._read("fees"), {"usbank-other": 95.0})
        self.assertEqual(self._read("waived"), ["usbank-other"])

    def test_adds_the_standard_changelog_line_under_the_dated_heading(self):
        discontinue("usbank-split", NAMES, "2026-09-29", 12, self.paths)
        text = open(self.paths["changelog"]).read()
        self.assertIn("## 2026-09-29\n- Removed the following card(s) because they can no longer be applied for: Split Card World Mastercard.", text)
        self.assertIn("## 2026-09-20\n- Older.", text)

    def test_a_second_answer_for_the_same_card_changes_nothing(self):
        discontinue("usbank-split", NAMES, "2026-09-29", 12, self.paths)
        before = {k: open(p).read() for k, p in self.paths.items()}
        self.assertIsNone(discontinue("usbank-split", NAMES, "2026-09-30", 13, self.paths))
        self.assertEqual(before, {k: open(p).read() for k, p in self.paths.items()})

    def test_an_unknown_card_id_is_refused_not_guessed(self):
        with self.assertRaises(ValueError):
            discontinue("not-a-card", NAMES, "2026-09-29", 12, self.paths)
        self.assertEqual(self._read("discontinued"), {})


if __name__ == "__main__":
    unittest.main()
