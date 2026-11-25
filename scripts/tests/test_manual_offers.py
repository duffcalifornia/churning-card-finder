import datetime
import unittest

from cardfinder.cli import split_paused
from cardfinder.parse import parse_offer
from cardfinder.registry import CARDS, ISSUERS, MANUAL_OFFERS, apply_manual_offers

BY_ID = {c.id: c for c in CARDS}


class Overlay(unittest.TestCase):
    ENTRY = {"a": {"text": "new", "checkedOn": "2026-11-20", "fee": 95}}

    def test_a_hand_entry_replaces_an_older_offer_and_sets_the_fee(self):
        offers, fees = {"a": {"seen": "2026-11-04", "text": "old"}}, {}
        apply_manual_offers(offers, fees, self.ENTRY)
        self.assertEqual(offers["a"], {"seen": "2026-11-20", "text": "new"})
        self.assertEqual(fees, {"a": 95.0})

    def test_a_newer_read_beats_the_hand_entry(self):
        offers, fees = {"a": {"seen": "2026-11-21", "text": "read"}}, {"a": 0.0}
        apply_manual_offers(offers, fees, self.ENTRY)
        self.assertEqual((offers["a"]["text"], fees["a"]), ("read", 0.0))


class TheFile(unittest.TestCase):
    def test_every_entry_is_usable(self):
        # A typo here should fail with the card's name, not quietly drop its bonus from the site.
        for cid, entry in MANUAL_OFFERS.items():
            self.assertIn(cid, BY_ID, cid)
            self.assertTrue(ISSUERS[BY_ID[cid].issuer].paused, cid)
            self.assertNotIn(cid, ISSUERS[BY_ID[cid].issuer].still_read, cid)
            datetime.date.fromisoformat(entry["checkedOn"])
            self.assertNotEqual(parse_offer(entry["text"]).kind, "unparsed", cid)


class PartlyPausedIssuers(unittest.TestCase):
    def test_only_the_still_read_cards_of_a_paused_issuer_are_requested(self):
        for name, issuer in ISSUERS.items():
            if not issuer.paused:
                continue
            cards = [c for c in CARDS if c.issuer == name]
            active, _ = split_paused(cards, ISSUERS)
            self.assertEqual({c.id for c in active}, set(issuer.still_read), name)
            self.assertTrue(set(issuer.still_read) <= {c.id for c in cards}, name)


if __name__ == "__main__":
    unittest.main()
