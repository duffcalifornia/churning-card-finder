import json
import os
import unittest

from cardfinder.registry import CARDS, CARD_CURRENCY, UNVALUED

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def load(*parts):
    return json.load(open(os.path.join(ROOT, *parts)))


CURRENCIES = load("data", "currencies.json")
PROGRAMS = load("data", "programs.json")
VALUATIONS = load("data", "valuations.json")
OFFERS = {r["cardId"]: r for r in load("data", "parsed-offers.json")}
CARD_IDS = {c.id for c in CARDS}


class CashOutQualifiers(unittest.TestCase):
    def test_amex_points_cash_out_well_only_with_a_schwab_platinum_or_a_business_platinum_and_checking(self):
        mr = next(c for c in CURRENCIES if c["id"] == "amex-membership-rewards")
        self.assertEqual(mr["cashBackRedemption"], "poor")
        self.assertEqual(mr["cashBackQualifiers"], [
            {"cards": ["schwab-platinum"]},
            {"cards": ["amex-business-platinum"], "account": "amexBusinessChecking"},
        ])

    def test_qualifier_cards_are_real_cards_and_only_poor_currencies_have_qualifiers(self):
        card_ids = {c["id"] for c in json.load(open(os.path.join(ROOT, "data", "cards.json")))}
        for cur in CURRENCIES:
            for q in cur.get("cashBackQualifiers", []):
                self.assertEqual(cur["cashBackRedemption"], "poor", cur["id"])
                for cid in q["cards"]:
                    self.assertIn(cid, card_ids)


class DataFiles(unittest.TestCase):
    def test_currencies_and_programs_match_their_schemas(self):
        import jsonschema
        cs, ps = load("data", "schema", "currency.schema.json"), load("data", "schema", "program.schema.json")
        for c in CURRENCIES:
            jsonschema.validate(c, cs)
        for p in PROGRAMS:
            jsonschema.validate(p, ps)

    def test_ids_are_unique(self):
        for items in (CURRENCIES, PROGRAMS):
            ids = [i["id"] for i in items]
            self.assertEqual(len(ids), len(set(ids)))

    def test_every_partner_is_a_known_program(self):
        known = {p["id"] for p in PROGRAMS}
        for c in CURRENCIES:
            for partner in c["partners"]:
                self.assertIn(partner, known, f"{c['id']} -> {partner}")

    def test_every_unlocker_is_a_tracked_card(self):
        for c in CURRENCIES:
            for card in c.get("unlockerCards", []):
                self.assertIn(card, CARD_IDS, f"{c['id']} -> {card}")

    def test_the_owners_transfer_rules(self):
        by = {c["id"]: c for c in CURRENCIES}
        self.assertTrue(by["ultimate-rewards"]["householdPooling"])
        self.assertTrue(by["capital-one-miles"]["householdPooling"])
        self.assertFalse(by["amex-membership-rewards"]["householdPooling"])
        self.assertFalse(by["citi-thankyou"]["householdPooling"])
        self.assertEqual(set(by["ultimate-rewards"]["unlockerCards"]),
                         {"chase-sapphire-preferred", "chase-sapphire-reserve", "chase-sapphire-reserve-business", "chase-ink-preferred"})
        self.assertEqual(set(by["citi-thankyou"]["unlockerCards"]), {"citi-strata-premier", "citi-strata-elite"})
        self.assertEqual(by["amex-membership-rewards"]["unlockerCards"], [])

    def test_jet_airways_is_gone_and_wells_fargo_has_virgin_atlantic(self):
        ids = {p["id"] for p in PROGRAMS}
        self.assertNotIn("jet-airways-intermiles", ids)
        wf = next(c for c in CURRENCIES if c["id"] == "wells-fargo-rewards")
        self.assertIn("virgin-atlantic-flying-club", wf["partners"])

    def test_avios_is_one_group_of_four_airlines(self):
        avios = [p for p in PROGRAMS if p.get("group") == "Avios"]
        self.assertEqual(len(avios), 1)      # one program id; the group is named so the exclusion question lists it once


class EveryCardWithPointsHasAValue(unittest.TestCase):
    def test_a_card_paying_points_or_a_named_program_has_a_currency_with_a_value(self):
        values = VALUATIONS["values"]
        for cid, rec in OFFERS.items():
            p = rec.get("parsed")
            if not p or not p.get("points"):
                continue
            if cid in UNVALUED:
                self.assertTrue(UNVALUED[cid], f"{cid} needs a reason")
                continue
            currency = p.get("currency") or CARD_CURRENCY.get(cid)
            self.assertIsNotNone(currency, f"{cid} pays points but has no currency")
            self.assertIn(currency, values, f"{cid} -> {currency} has no value")

    def test_mapped_currencies_that_are_transferable_exist_as_currencies(self):
        ids = {c["id"] for c in CURRENCIES}
        for cid, currency in CARD_CURRENCY.items():
            if currency in ("ultimate-rewards", "amex-membership-rewards", "citi-thankyou", "capital-one-miles", "wells-fargo-rewards"):
                self.assertIn(currency, ids)

    def test_every_mapped_card_is_tracked(self):
        for cid in list(CARD_CURRENCY) + list(UNVALUED):
            self.assertIn(cid, CARD_IDS)


if __name__ == "__main__":
    unittest.main()
