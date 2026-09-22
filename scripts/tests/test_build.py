import json
import os
import unittest

from cardfinder.build import build_parsed_offers
from cardfinder.models import Card
from cardfinder.registry import CARDS

SCHEMA = os.path.join(os.path.dirname(__file__), "..", "..", "data", "schema", "parsed-offer.schema.json")


def card(cid, expected=True, kind="personal"):
    return Card(id=cid, issuer="x", names=[cid.upper()], kind=kind, urls=["https://x"], expected=expected)


OFFERS = {
    "a": {"text": "Earn 75,000 points after you spend $5,000 in purchases in the first 3 months", "seen": "2026-09-20"},
    "tier": {"text": "Earn 75,000 bonus points after you spend $4,000 in the first 3 months. ",
             "full_text": "Earn 75,000 bonus points after you spend $4,000 in the first 3 months. Plus, 40,000 bonus points after you spend $20,000 in the first 12 months.",
             "seen": "2026-09-20"},
    "cash": {"text": "Earn $750 cash back after you spend $6,000 on purchases in the first 3 months", "seen": "2026-09-20"},
    "struck": {"text": "Earn 60,000 90,000 Bonus Miles after you spend $6,000 in your first 6 months", "seen": "2026-09-20"},
}


class BuildParsedOffers(unittest.TestCase):
    def by_id(self, cards, confirmed_none=("none",), **kw):
        return {e["cardId"]: e for e in build_parsed_offers(cards, OFFERS, confirmed_none=set(confirmed_none), **kw)}

    def test_a_card_with_an_offer_gets_structured_fields(self):
        e = self.by_id([card("a")])["a"]
        self.assertTrue(e["hasWelcomeOffer"])
        self.assertEqual((e["parsed"]["points"], e["parsed"]["minSpend"], e["parsed"]["windowMonths"]), (75000, 5000, 3))
        self.assertEqual(e["seenOn"], "2026-09-20")
        self.assertIn("75,000", e["sourceText"])

    def test_the_fuller_text_is_used_so_a_second_tier_is_kept(self):
        tiers = self.by_id([card("tier")])["tier"]["parsed"]["additionalTiers"]
        self.assertEqual([(t["points"], t["minSpend"], t["windowMonths"]) for t in tiers], [(40000, 20000, 12)])

    def test_a_card_without_an_offer_is_recorded_as_having_none(self):
        e = self.by_id([card("none")])["none"]
        self.assertFalse(e["hasWelcomeOffer"])
        self.assertNotIn("parsed", e)

    def test_a_card_with_no_offer_that_nobody_confirmed_is_unknown_not_none(self):
        e = self.by_id([card("mystery")])["mystery"]
        self.assertIsNone(e["hasWelcomeOffer"])
        self.assertTrue(e["needsReview"])

    def test_cards_that_are_not_tracked_are_left_out(self):
        self.assertEqual(self.by_id([card("a", expected=False)]), {})

    def test_uncertain_rows_are_marked_for_review(self):
        self.assertTrue(self.by_id([card("struck")])["struck"]["needsReview"])
        self.assertFalse(self.by_id([card("a")])["a"]["needsReview"])


class OwnerFacts(unittest.TestCase):
    def build(self, cards, **kw):
        return {e["cardId"]: e for e in build_parsed_offers(cards, OFFERS, confirmed_none=set(), **kw)}

    def test_a_row_the_owner_reviewed_no_longer_needs_review(self):
        e = self.build([card("struck")], reviewed={"struck"})["struck"]
        self.assertFalse(e["needsReview"])
        self.assertTrue(e["reviewedByOwner"])

    def test_cash_advertised_but_paid_as_points_is_recorded_as_points(self):
        e = self.build([card("cash")], cash_paid_as_points={"cash": ("ultimate-rewards", 100)})["cash"]["parsed"]
        self.assertEqual((e["points"], e["currency"], e["displayedAsCash"], e["cashBack"]), (75000, "ultimate-rewards", 750, None))
        self.assertTrue(any("paid as" in n for n in e["notes"]))

    def test_other_cash_offers_are_left_alone(self):
        e = self.build([card("cash")])["cash"]["parsed"]
        self.assertEqual((e["cashBack"], e["points"], e["displayedAsCash"]), (750, None, None))

    def test_offers_from_a_paused_issuer_are_marked_stale(self):
        c = Card(id="a", issuer="amex", names=["A"], urls=["https://x"])
        e = self.build([c], stale_issuers={"amex": "Amex paused"})["a"]
        self.assertTrue(e["stale"])
        self.assertEqual(e["staleReason"], "Amex paused")

    def test_a_paused_issuers_offer_read_since_the_stale_date_is_not_stale(self):
        c = Card(id="a", issuer="amex", names=["A"], urls=["https://x"])
        offers = {"a": {"seen": "2026-09-21", "text": "Earn 50,000 points after you spend $3,000 in the first 3 months"}}
        e = build_parsed_offers([c], offers, stale_issuers={"amex": "Amex paused"}, stale_since="2026-09-21")[0]
        self.assertNotIn("stale", e)
        older = {"a": {**offers["a"], "seen": "2026-09-20"}}
        e = build_parsed_offers([c], older, stale_issuers={"amex": "Amex paused"}, stale_since="2026-09-21")[0]
        self.assertTrue(e["stale"])

    def test_a_fresh_offer_is_not_marked_stale(self):
        self.assertNotIn("stale", self.build([card("a")])["a"])


class RealDataMatchesTheSchema(unittest.TestCase):
    def test_every_entry_built_from_the_recorded_offers_validates(self):
        import jsonschema
        from cardfinder.registry import LAST_KNOWN_OFFERS
        schema = json.load(open(SCHEMA))
        from cardfinder.registry import NO_OFFER_CONFIRMED, REVIEWED_OK, CASH_PAID_AS_POINTS, ISSUERS
        stale = {k: v.paused for k, v in ISSUERS.items() if v.paused}
        entries = build_parsed_offers(CARDS, LAST_KNOWN_OFFERS, confirmed_none=NO_OFFER_CONFIRMED, reviewed=REVIEWED_OK,
                                      cash_paid_as_points=CASH_PAID_AS_POINTS, stale_issuers=stale)
        self.assertGreater(len(entries), 100)
        for e in entries:
            jsonschema.validate(e, schema)


if __name__ == "__main__":
    unittest.main()
