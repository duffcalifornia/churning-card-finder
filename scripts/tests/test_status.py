import json
import os
import shutil
import tempfile
import unittest

from cardfinder.status import discontinue, ignore, parse_command, parse_options, track, validate_proposal

NAMES = {"usbank-split": "Split Card World Mastercard", "usbank-other": "Other Card"}


class ParseCommand(unittest.TestCase):
    def test_the_four_commands(self):
        self.assertEqual(parse_command("/discontinued"), "discontinued")
        self.assertEqual(parse_command("/still-active"), "still-active")
        self.assertEqual(parse_command("/track"), "track")
        self.assertEqual(parse_command("/ignore"), "ignore")

    def test_case_and_trailing_text_are_fine(self):
        self.assertEqual(parse_command("/Discontinued thanks, checked the site"), "discontinued")
        self.assertEqual(parse_command("  /still-active\nit is on the app page"), "still-active")

    def test_a_command_that_is_not_the_first_word_does_not_count(self):
        self.assertIsNone(parse_command("I think /discontinued"))

    def test_other_comments_and_empty_input_are_ignored(self):
        for text in ("looks fine", "/discontinue", "", None, "/removed", "/tracked", "/ignored"):
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


class ParseOptions(unittest.TestCase):
    def test_reads_key_value_pairs_after_the_command(self):
        self.assertEqual(parse_options('/track kind=business currency=ultimate-rewards'),
                         {"kind": "business", "currency": "ultimate-rewards"})

    def test_quoted_names_keep_their_spaces(self):
        self.assertEqual(parse_options('/track name="Business Essentials Visa Card"'), {"name": "Business Essentials Visa Card"})

    def test_unknown_keys_and_empty_values_are_ignored(self):
        self.assertEqual(parse_options("/track url=https://evil.example id=hacked kind="), {})

    def test_only_the_first_line_counts_and_unbalanced_quotes_do_not_crash(self):
        self.assertEqual(parse_options("/track kind=business\ncurrency=cash"), {"kind": "business"})
        self.assertEqual(parse_options('/track name="oops kind=business'), {"kind": "business"})   # the half-quoted name is dropped
        self.assertEqual(parse_options(None), {})


HOSTS = {"usbank": {"www.usbank.com"}, "chase": {"creditcards.chase.com"}}
PROPOSAL = {"id": "usbank-business-new", "name": "Business New Visa Card", "issuer": "usbank", "kind": "business",
            "url": "https://www.usbank.com/business-banking/business-credit-cards/business-new-credit-card.html/",
            "offer": {"text": "Earn $200 after $500", "full_text": "Earn $200 after $500. More."},
            "fee": {"amount": 95.0, "firstYearWaived": True},
            "reads_as": {"points": None, "cashBack": 200.0}}
CURRENCIES = {"cash", "ultimate-rewards"}


class ValidateProposal(unittest.TestCase):
    def test_a_good_proposal_passes(self):
        self.assertEqual(validate_proposal(PROPOSAL, HOSTS), PROPOSAL)

    def test_each_bad_field_is_refused(self):
        for change in ({"id": "Bad Id"}, {"id": "x" * 90}, {"name": "x"}, {"name": "line\nbreak"}, {"issuer": "nobody"},
                       {"kind": "corporate"}, {"url": "http://www.usbank.com/x.html"}, {"url": "https://evil.example/x.html"},
                       {"url": "https://creditcards.chase.com/x"}):   # a Chase page cannot be proposed for U.S. Bank
            with self.assertRaises(ValueError, msg=str(change)):
                validate_proposal({**PROPOSAL, **change}, HOSTS)

    def test_missing_fields_are_refused(self):
        for bad in ({}, None, {"id": "usbank-x"}):
            with self.assertRaises(ValueError):
                validate_proposal(bad, HOSTS)


class TrackAndIgnore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.paths = {k: os.path.join(self.dir, v) for k, v in {"tracked": "t.json", "ignored": "i.json", "offers": "o.json", "fees": "f.json",
                                                                  "waived": "w.json", "changelog": "c.md"}.items()}
        for key, value in (("tracked", {}), ("ignored", {}), ("offers", {"a": {"seen": "2026-01-01", "text": "x"}}), ("fees", {"a": 0.0}), ("waived", ["a"])):
            with open(self.paths[key], "w") as f:
                json.dump(value, f)
        with open(self.paths["changelog"], "w") as f:
            f.write("What changed.\n\n## 2026-09-20\n- Older.\n")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def read(self, key):
        with open(self.paths[key]) as f:
            return json.load(f)

    def do_track(self, options=None, known=frozenset({"a"})):
        return track(PROPOSAL, options or {}, "2026-09-29", 7, self.paths, known, HOSTS, CURRENCIES)

    def test_tracking_records_the_card_seeds_its_offer_and_fee_and_logs_it(self):
        self.assertEqual(self.do_track(), ("tracked", "Business New Visa Card"))
        entry = self.read("tracked")["usbank-business-new"]
        self.assertEqual((entry["issuer"], entry["kind"], entry["added"]), ("usbank", "business", "2026-09-29"))
        self.assertEqual(entry["url"], "https://www.usbank.com/business-banking/business-credit-cards/business-new-credit-card.html")
        self.assertEqual(self.read("offers")["usbank-business-new"], {"seen": "2026-09-29", "text": "Earn $200 after $500", "full_text": "Earn $200 after $500. More."})
        self.assertEqual(self.read("fees")["usbank-business-new"], 95.0)
        self.assertEqual(self.read("waived"), ["a", "usbank-business-new"])
        self.assertIn("## 2026-09-29\n- Added the following card(s): Business New Visa Card.", open(self.paths["changelog"]).read())
        self.assertIn("## 2026-09-20\n- Older.", open(self.paths["changelog"]).read())

    def test_options_override_the_proposal(self):
        self.do_track({"kind": "personal", "name": "Exact Name", "currency": "ultimate-rewards"})
        entry = self.read("tracked")["usbank-business-new"]
        self.assertEqual((entry["kind"], entry["name"], entry["currency"]), ("personal", "Exact Name", "ultimate-rewards"))

    def test_a_card_paid_in_points_must_be_given_a_currency(self):
        points = {**PROPOSAL, "reads_as": {"points": 30000.0, "cashBack": None}}
        with self.assertRaises(ValueError) as ctx:
            track(points, {}, "2026-09-29", 7, self.paths, {"a"}, HOSTS, CURRENCIES)
        self.assertIn("currency", str(ctx.exception))
        self.assertEqual(self.read("tracked"), {})
        track(points, {"currency": "ultimate-rewards"}, "2026-09-29", 7, self.paths, {"a"}, HOSTS, CURRENCIES)
        self.assertEqual(self.read("tracked")["usbank-business-new"]["currency"], "ultimate-rewards")

    def test_a_card_paying_free_nights_cannot_be_tracked_from_a_reply(self):
        nights = {**PROPOSAL, "reads_as": {"points": None, "freeNightAwards": 2}}
        with self.assertRaises(ValueError) as ctx:
            track(nights, {"currency": "cash"}, "2026-09-29", 7, self.paths, {"a"}, HOSTS, CURRENCIES)
        self.assertIn("free night", str(ctx.exception))

    def test_a_currency_the_site_cannot_value_is_refused_and_nothing_is_written(self):
        with self.assertRaises(ValueError):
            self.do_track({"currency": "made-up-points"})
        self.assertEqual(self.read("tracked"), {})
        self.assertEqual(list(self.read("offers")), ["a"])

    def test_a_bad_kind_override_is_refused(self):
        with self.assertRaises(ValueError):
            self.do_track({"kind": "corporate"})

    def test_a_card_id_the_site_already_knows_is_refused(self):
        with self.assertRaises(ValueError):
            self.do_track(known={"usbank-business-new"})

    def test_tracking_twice_changes_nothing_but_a_currency_on_the_second_reply_sets_it(self):
        self.do_track()
        self.assertEqual(self.do_track(), ("unchanged", "Business New Visa Card"))
        self.assertEqual(self.do_track({"currency": "ultimate-rewards"}), ("updated", "Business New Visa Card"))
        self.assertEqual(self.read("tracked")["usbank-business-new"]["currency"], "ultimate-rewards")
        self.assertEqual(open(self.paths["changelog"]).read().count("Added the following card(s)"), 1)

    def test_a_card_with_no_offer_or_fee_read_still_tracks_without_seeding(self):
        bare = {**PROPOSAL, "offer": None, "fee": None}
        track(bare, {}, "2026-09-29", 7, self.paths, {"a"}, HOSTS, CURRENCIES)
        self.assertEqual(list(self.read("offers")), ["a"])
        self.assertEqual(self.read("fees"), {"a": 0.0})

    def test_ignoring_remembers_the_normalised_page_and_never_touches_anything_else(self):
        self.assertEqual(ignore(PROPOSAL, "2026-09-29", self.paths, HOSTS), "Business New Visa Card")
        self.assertEqual(self.read("ignored"),
                         {"https://www.usbank.com/business-banking/business-credit-cards/business-new-credit-card.html":
                          {"name": "Business New Visa Card", "date": "2026-09-29"}})
        self.assertEqual(self.read("tracked"), {})
        self.assertNotIn("Added", open(self.paths["changelog"]).read())


if __name__ == "__main__":
    unittest.main()
