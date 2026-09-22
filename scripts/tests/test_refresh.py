import json
import sys
import unittest

from cardfinder.check import CardResult
from cardfinder.extract import Fee, Offer
from cardfinder.refresh import merge_last_known


def found(card_id, offer=None, fee=None, via_fallback=False):
    return CardResult(card_id, card_id, "found_via_fallback" if via_fallback else "found", offer=offer, fee=fee)


def not_found(card_id):
    return CardResult(card_id, card_id, "not_found")


def skipped(card_id):
    return CardResult(card_id, card_id, "skipped", note="discontinued")


TODAY = "2026-09-22"


class MergeLastKnown(unittest.TestCase):
    def test_a_found_offer_is_recorded_with_todays_date(self):
        offer = Offer(text="Earn 50,000 points", method="after_amount")
        offers, fees, waived = merge_last_known([found("a", offer=offer)], {}, {}, set(), TODAY)
        self.assertEqual(offers["a"], {"seen": TODAY, "text": "Earn 50,000 points"})

    def test_full_text_is_kept_only_when_it_differs_from_the_short_text(self):
        same = Offer(text="Earn 50,000 points", method="after_amount", full_text="Earn 50,000 points")
        offers, _, _ = merge_last_known([found("a", offer=same)], {}, {}, set(), TODAY)
        self.assertNotIn("full_text", offers["a"])

        longer = Offer(text="Earn 50,000 points", method="after_amount", full_text="Earn 50,000 points. Plus, 10,000 more.")
        offers, _, _ = merge_last_known([found("b", offer=longer)], {}, {}, set(), TODAY)
        self.assertEqual(offers["b"]["full_text"], "Earn 50,000 points. Plus, 10,000 more.")

    def test_a_found_fee_is_recorded(self):
        _, fees, _ = merge_last_known([found("a", fee=Fee(text="$95", amount=95.0))], {}, {}, set(), TODAY)
        self.assertEqual(fees["a"], 95.0)

    def test_a_waived_first_year_fee_is_added_to_the_waived_set(self):
        r = found("a", fee=Fee(text="$0 first year", amount=150.0, first_year_waived=True))
        _, _, waived = merge_last_known([r], {}, {}, set(), TODAY)
        self.assertIn("a", waived)

    def test_a_fee_read_without_waiver_never_removes_an_existing_waived_flag(self):
        r = found("a", fee=Fee(text="$95", amount=95.0, first_year_waived=False))
        _, _, waived = merge_last_known([r], {}, {}, {"a"}, TODAY)
        self.assertIn("a", waived)  # not observing "waived" this run is not evidence it stopped being waived

    def test_found_via_fallback_still_updates_the_cache(self):
        offer = Offer(text="Earn 10,000 points", method="after_amount")
        offers, _, _ = merge_last_known([found("a", offer=offer, via_fallback=True)], {}, {}, set(), TODAY)
        self.assertEqual(offers["a"]["text"], "Earn 10,000 points")

    def test_not_found_or_skipped_cards_keep_their_old_entry_untouched(self):
        old_offers = {"a": {"seen": "2026-01-01", "text": "old offer"}}
        old_fees = {"a": 50.0}
        offers, fees, _ = merge_last_known([not_found("a")], old_offers, old_fees, set(), TODAY)
        self.assertEqual(offers, old_offers)
        self.assertEqual(fees, old_fees)
        offers, fees, _ = merge_last_known([skipped("a")], old_offers, old_fees, set(), TODAY)
        self.assertEqual(offers, old_offers)
        self.assertEqual(fees, old_fees)

    def test_a_found_card_with_no_fee_this_run_keeps_its_old_fee(self):
        offer = Offer(text="Earn 10,000 points", method="after_amount")
        offers, fees, _ = merge_last_known([found("a", offer=offer, fee=None)], {}, {"a": 95.0}, set(), TODAY)
        self.assertEqual(fees["a"], 95.0)
        self.assertEqual(offers["a"]["text"], "Earn 10,000 points")

    def test_a_found_card_with_no_offer_this_run_keeps_its_old_offer(self):
        old_offers = {"a": {"seen": "2026-01-01", "text": "old offer"}}
        offers, fees, _ = merge_last_known([found("a", fee=Fee(text="$0", amount=0.0))], old_offers, {}, set(), TODAY)
        self.assertEqual(offers["a"], old_offers["a"])
        self.assertEqual(fees["a"], 0.0)

    def test_does_not_change_its_inputs(self):
        old_offers = {"a": {"seen": "2026-01-01", "text": "old offer"}}
        old_fees = {"a": 50.0}
        old_waived = {"a"}
        before = (dict(old_offers), dict(old_fees), set(old_waived))
        merge_last_known([found("b", offer=Offer(text="x", method="y"))], old_offers, old_fees, old_waived, TODAY)
        self.assertEqual((old_offers, old_fees, old_waived), before)

    def test_several_results_update_independently(self):
        results = [
            found("a", offer=Offer(text="offer a", method="m")),
            not_found("b"),
            found("c", fee=Fee(text="$0", amount=0.0)),
        ]
        offers, fees, _ = merge_last_known(results, {"b": {"seen": "2026-01-01", "text": "old b"}}, {}, set(), TODAY)
        self.assertEqual(offers["a"]["text"], "offer a")
        self.assertEqual(offers["b"]["text"], "old b")
        self.assertNotIn("c", offers)
        self.assertEqual(fees["c"], 0.0)


class WriteCacheFilesPreservesOrder(unittest.TestCase):
    """A daily automated run must not turn a one-card change into a file-wide diff by silently reordering
    every other card's fields. sort_keys=True on json.dump did exactly that once (caught by hand, not by a
    test, before this class existed): it alphabetized every entry's own keys (seen/text/full_text) on every
    write, so a single real change produced a 100+ line diff. This locks that in."""

    def setUp(self):
        import importlib
        import os
        import tempfile

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        import refresh_offers
        importlib.reload(refresh_offers)
        self.mod = refresh_offers
        self.tmp = {}
        for attr in ("OFFERS_PATH", "FEES_PATH", "WAIVED_PATH"):
            f = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
            f.close()
            self.tmp[attr] = (getattr(refresh_offers, attr), f.name)
            setattr(refresh_offers, attr, f.name)

    def tearDown(self):
        import os

        for attr, (orig, tmp_path) in self.tmp.items():
            setattr(self.mod, attr, orig)
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_an_untouched_entrys_own_key_order_is_not_rewritten(self):
        # "seen" before "text" before "full_text", same as the real cache file's established order.
        offers = {
            "a": {"seen": "2026-01-01", "text": "old a", "full_text": "old a in full"},
            "b": {"seen": "2026-01-01", "text": "old b"},
        }
        self.mod._write_cache_files(offers, {"a": 95.0}, {"a"})
        raw = open(self.mod.OFFERS_PATH).read()
        # The literal key order in the file, not just dict equality (which ignores order): "seen" first.
        self.assertLess(raw.index('"seen"'), raw.index('"text"'))
        self.assertLess(raw.index('"text"'), raw.index('"full_text"'))

    def test_top_level_card_order_is_not_alphabetized_either(self):
        offers = {"zzz-later-card": {"seen": "2026-01-01", "text": "z"}, "a-first-card": {"seen": "2026-01-01", "text": "a"}}
        self.mod._write_cache_files(offers, {}, set())
        raw = open(self.mod.OFFERS_PATH).read()
        self.assertLess(raw.index("zzz-later-card"), raw.index("a-first-card"))

    def test_round_trips_through_json_correctly(self):
        offers, fees, waived = {"a": {"seen": "2026-01-01", "text": "x"}}, {"a": 0.0}, {"a"}
        self.mod._write_cache_files(offers, fees, waived)
        self.assertEqual(json.load(open(self.mod.OFFERS_PATH)), offers)
        self.assertEqual(json.load(open(self.mod.FEES_PATH)), fees)
        self.assertEqual(json.load(open(self.mod.WAIVED_PATH)), sorted(waived))


class MainWritesTheChangelogTests(unittest.TestCase):
    """A full run of main() (with the network call itself stubbed out) writes one changelog line for whichever
    cards' offer text actually changed — the owner's rule (2026-09-22) for consistent, automated entries."""

    def setUp(self):
        import importlib
        import os
        import tempfile

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        import refresh_offers
        importlib.reload(refresh_offers)
        self.mod = refresh_offers
        self.tmp = {}
        for attr in ("OFFERS_PATH", "FEES_PATH", "WAIVED_PATH"):
            f = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
            f.write(b"{}")
            f.close()
            self.tmp[attr] = (getattr(refresh_offers, attr), f.name)
            setattr(refresh_offers, attr, f.name)
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
        f.write("What changed. Newest first.\n\n## 2026-09-20\n- An older entry.\n")
        f.close()
        self.tmp["CHANGELOG_PATH"] = (refresh_offers.CHANGELOG_PATH, f.name)
        refresh_offers.CHANGELOG_PATH = f.name

        # LAST_KNOWN_OFFERS is read at import time from the real cache file; override it directly so the diff
        # has a known "before" to compare the stubbed run's "after" against.
        self._orig_last_known = refresh_offers.LAST_KNOWN_OFFERS
        refresh_offers.LAST_KNOWN_OFFERS = {"chase-sapphire-preferred": {"seen": "2026-01-01", "text": "60,000 points"}}

        # Real card ids so select_cards()/CARDS lookups still work; only chase-sapphire-preferred's offer will
        # actually change, so it is the only one that should appear in the changelog line.
        offer = Offer(text="75,000 points", method="after_amount")
        stub_result = found("chase-sapphire-preferred", offer=offer)
        self._orig_run = refresh_offers.run
        refresh_offers.run = lambda *a, **k: [stub_result]
        self._orig_subprocess = refresh_offers.subprocess.run
        refresh_offers.subprocess.run = lambda *a, **k: None  # skip the real parse_offers.py/build_cards.py rebuild

    def tearDown(self):
        import os

        for attr, (orig, tmp_path) in self.tmp.items():
            setattr(self.mod, attr, orig)
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        self.mod.LAST_KNOWN_OFFERS = self._orig_last_known
        self.mod.run = self._orig_run
        self.mod.subprocess.run = self._orig_subprocess

    def test_the_one_card_whose_offer_changed_is_named_in_a_new_changelog_entry(self):
        import datetime

        exit_code = self.mod.main(["--card", "chase-sapphire-preferred", "--no-render"])
        self.assertEqual(exit_code, 0)

        changelog = open(self.mod.CHANGELOG_PATH).read()
        today = datetime.date.today().isoformat()
        self.assertIn(f"## {today}", changelog)
        self.assertIn("Updated the bonus offer for the following card(s): Chase Sapphire Preferred.", changelog)
        self.assertIn("## 2026-09-20\n- An older entry.", changelog)  # the old section survives untouched

    def test_a_fee_only_change_gets_its_own_entry_with_the_offer_text_unchanged(self):
        # Same offer text as LAST_KNOWN_OFFERS (no bonus-offer entry expected), but a different fee.
        self.mod.LAST_KNOWN_OFFERS = {"chase-sapphire-preferred": {"seen": "2026-01-01", "text": "75,000 points"}}
        self.mod.LAST_KNOWN_FEES = {"chase-sapphire-preferred": 95.0}
        offer = Offer(text="75,000 points", method="after_amount")
        fee = Fee(text="$100", amount=100.0)
        self.mod.run = lambda *a, **k: [found("chase-sapphire-preferred", offer=offer, fee=fee)]

        exit_code = self.mod.main(["--card", "chase-sapphire-preferred", "--no-render"])
        self.assertEqual(exit_code, 0)

        changelog = open(self.mod.CHANGELOG_PATH).read()
        self.assertNotIn("Updated the bonus offer", changelog)
        self.assertIn(
            "Updated the net value rankings to reflect changes to the annual fee on the following card: Chase Sapphire Preferred.",
            changelog,
        )


if __name__ == "__main__":
    unittest.main()
