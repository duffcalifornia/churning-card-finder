import json
import os
import unittest

from cardfinder.catalog import build_catalog
from cardfinder.registry import CARDS, LAST_KNOWN_FEES, UNVALUED, OWNER_FEES
from cardfinder.value import bonus_value

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def load(*parts):
    return json.load(open(os.path.join(ROOT, *parts)))


CATALOG = build_catalog()
BY_ID = {c["id"]: c for c in CATALOG}
VALUATIONS = load("data", "valuations.json")
CURRENCIES = load("data", "currencies.json")
MATRIX = load("data", "marriott-matrix.json")
OFFERS = {r["cardId"]: r for r in load("data", "parsed-offers.json")}


class Shape(unittest.TestCase):
    def test_every_card_matches_the_schema(self):
        import jsonschema
        schema = load("data", "schema", "card.schema.json")
        for c in CATALOG:
            jsonschema.validate(c, schema)

    def test_ids_are_unique(self):
        self.assertEqual(len(BY_ID), len(CATALOG))

    def test_the_file_on_disk_is_current(self):
        self.assertEqual(load("data", "cards.json"), json.loads(json.dumps(CATALOG)))

    def test_every_expected_registry_card_is_in_the_catalog(self):
        for c in CARDS:
            if c.expected:
                self.assertIn(c.id, BY_ID)

    def test_cards_with_an_offer_are_recommendable_and_the_rest_are_history_only(self):
        for c in CATALOG:
            offer = OFFERS.get(c["id"])
            has_offer = bool(offer and offer.get("hasWelcomeOffer"))
            self.assertEqual(c["recommendable"], has_offer, c["id"])

    def test_every_recommendable_card_has_a_fee_and_min_spend(self):
        for c in CATALOG:
            if c["recommendable"]:
                self.assertIn("annualFee", c, c["id"])
                parsed = OFFERS[c["id"]]["parsed"]
                if parsed["kind"] == "standard" and parsed["minSpend"]:
                    self.assertIn("typicalMinSpend", c, c["id"])

    def test_a_bonus_with_no_spend_requirement_has_no_min_spend(self):
        self.assertNotIn("typicalMinSpend", BY_ID["chase-amazon-prime"])

    def test_fees_come_from_the_recorded_fees(self):
        for cid, fee in LAST_KNOWN_FEES.items():
            if cid in BY_ID and BY_ID[cid]["recommendable"]:
                self.assertEqual(BY_ID[cid]["annualFee"], fee, cid)
        for cid, (fee, waived) in OWNER_FEES.items():
            self.assertEqual(BY_ID[cid]["annualFee"], fee)
            self.assertEqual(BY_ID[cid].get("firstYearFeeWaived", False), waived)


class Flags(unittest.TestCase):
    def test_reports_to_personal(self):
        for cid in ("chase-sapphire-preferred", "amex-gold", "capone-spark-cash", "capone-venture"):
            self.assertTrue(BY_ID[cid]["reportsToPersonal"], cid)
        for cid in ("chase-ink-cash", "amex-business-gold", "capone-spark-cash-plus", "capone-venture-x-business",
                    "usbank-business-leverage", "citi-aadvantage-business", "wellsfargo-signify-business"):
            self.assertFalse(BY_ID[cid]["reportsToPersonal"], cid)

    def test_first_year_fee_waived(self):
        self.assertTrue(BY_ID["amex-blue-cash-preferred"]["firstYearFeeWaived"])
        self.assertTrue(BY_ID["usbank-business-altitude-connect"]["firstYearFeeWaived"])
        self.assertFalse(BY_ID["amex-platinum"].get("firstYearFeeWaived", False))

    def test_charge_cards(self):
        for cid in ("amex-platinum", "amex-gold", "amex-business-platinum"):
            self.assertTrue(BY_ID[cid]["chargeCard"], cid)
        self.assertFalse(BY_ID["amex-hilton-aspire"].get("chargeCard", False))
        self.assertFalse(BY_ID["chase-freedom-flex"].get("chargeCard", False))

    def test_unlockers_match_the_currency_data(self):
        expected = {cid for cur in CURRENCIES for cid in cur["unlockerCards"]}
        actual = {c["id"] for c in CATALOG if c.get("unlocksTransfers")}
        self.assertEqual(actual, expected)

    def test_aa_cards_need_aa_access(self):
        aa = {c["id"] for c in CATALOG if c.get("requiresAAAccess")}
        self.assertEqual(aa, {cid for cid in BY_ID if cid.startswith("citi-aadvantage")})

    def test_currency_and_bonus_types(self):
        self.assertEqual(BY_ID["chase-ink-cash"]["currency"], "ultimate-rewards")
        self.assertIn("transferable", BY_ID["chase-sapphire-preferred"]["bonusTypes"])
        self.assertEqual(BY_ID["amex-delta-gold"]["coBrandedProgram"], "delta-skymiles")
        self.assertEqual(BY_ID["amex-delta-gold"]["bonusTypes"], ["airline"])
        self.assertEqual(BY_ID["amex-hilton-surpass"]["bonusTypes"], ["hotel"])
        self.assertEqual(BY_ID["amex-blue-business-cash"]["currency"], "cash")
        self.assertEqual(BY_ID["amex-blue-business-cash"]["bonusTypes"], ["cashback"])
        self.assertNotIn("coBrandedProgram", BY_ID["chase-sapphire-preferred"])


class Families(unittest.TestCase):
    def test_amex_delta_tiers_run_low_to_high(self):
        tiers = [BY_ID[c]["family"]["tier"] for c in
                 ("amex-delta-blue", "amex-delta-options", "amex-delta-gold", "amex-delta-platinum", "amex-delta-reserve")]
        self.assertEqual(tiers, [1, 2, 3, 4, 5])
        self.assertEqual({BY_ID[c]["family"]["id"] for c in ("amex-delta-blue", "amex-delta-reserve")}, {"delta-personal"})

    def test_business_delta_is_its_own_family(self):
        self.assertEqual(BY_ID["amex-delta-gold-business"]["family"], {"id": "delta-business", "tier": 1})

    def test_same_tier_cards_share_a_tier(self):
        self.assertEqual(BY_ID["amex-platinum"]["family"], BY_ID["schwab-platinum"]["family"])
        self.assertEqual(BY_ID["amex-blue-cash-preferred"]["family"], BY_ID["morganstanley-blue-cash-preferred"]["family"])

    def test_hilton_only_surpass_and_ascend_are_in_a_family(self):
        self.assertEqual(BY_ID["amex-hilton-surpass"]["family"]["tier"], 1)
        self.assertEqual(BY_ID["amex-hilton-ascend"]["family"]["tier"], 2)
        self.assertNotIn("family", BY_ID["amex-hilton-aspire"])
        self.assertNotIn("family", BY_ID["amex-hilton-honors"])

    def test_venture_family_orders_by_annual_fee(self):
        t = [BY_ID[c]["family"]["tier"] for c in ("capone-ventureone", "capone-venture", "capone-venture-x")]
        self.assertEqual(t, [1, 2, 3])
        self.assertNotIn("family", BY_ID["capone-venture-x-business"])
        self.assertNotIn("family", BY_ID["capone-savor"])

    def test_family_order_matches_annual_fee_order_for_venture(self):
        fees = [BY_ID[c]["annualFee"] for c in ("capone-ventureone", "capone-venture", "capone-venture-x")]
        self.assertEqual(fees, sorted(fees))


class BonusRules(unittest.TestCase):
    def rules(self, cid):
        return BY_ID[cid].get("bonusRules", {})

    def test_lifetime_cards(self):
        for cid in ("chase-sapphire-preferred", "chase-sapphire-reserve", "chase-sapphire-reserve-business",
                    "chase-ink-cash", "chase-ink-preferred", "citi-strata-elite", "amex-platinum", "amex-delta-blue"):
            self.assertTrue(self.rules(cid).get("onceInLifetime"), cid)

    def test_strata_families(self):
        self.assertEqual(self.rules("citi-strata")["lifetimeAlsoBlockedBy"], ["citi-strata-student"])
        self.assertEqual(self.rules("citi-strata-premier")["lifetimeAlsoBlockedBy"], ["citi-premier"])
        self.assertNotIn("lifetimeAlsoBlockedBy", self.rules("citi-strata-elite"))

    def test_other_citi_cards_use_48_months(self):
        r = self.rules("citi-double-cash")
        self.assertEqual((r["cooldownMonths"], r["cooldownBasis"]), (48, "bonus"))

    def test_southwest_personal_cards_share_one_family_clock(self):
        for cid in ("chase-southwest-plus", "chase-southwest-premier", "chase-southwest-priority"):
            r = self.rules(cid)
            self.assertEqual((r["cooldownMonths"], r["cooldownFamily"], r["blockedWhileHeld"]), (24, "southwest-personal", True))
        self.assertNotIn("cooldownFamily", self.rules("chase-southwest-premier-business"))

    def test_ihg_personal_cards_share_a_family_clock(self):
        self.assertEqual(self.rules("chase-ihg-premier")["cooldownFamily"], "ihg-personal")
        self.assertEqual(self.rules("chase-ihg-traveler")["cooldownFamily"], "ihg-personal")

    def test_boa_personal_cards_are_held_based_and_business_cards_have_no_rule(self):
        r = self.rules("boa-unlimited-cash")
        self.assertEqual((r["cooldownMonths"], r["cooldownBasis"]), (24, "held"))
        self.assertEqual(self.rules("boa-business-unlimited-cash"), {})

    def test_marriott_cards_point_at_the_matrix(self):
        wanted = [c["id"] for c in MATRIX["cards"] if c["canBeWanted"]]
        for cid in wanted:
            self.assertEqual(self.rules(cid).get("marriottMatrixKey"), cid)

    def test_amex_marriott_cards_carry_lifetime_language_and_chase_ones_do_not(self):
        # all Amex cards have lifetime language by default; the matrix applies on top of it (owner, 2026-09-21)
        for cid in ("amex-marriott-business", "amex-marriott-brilliant", "amex-marriott-bevy"):
            self.assertTrue(self.rules(cid).get("onceInLifetime"), cid)
        for cid in ("chase-marriott-bold", "chase-marriott-boundless", "chase-marriott-bountiful"):
            self.assertNotIn("onceInLifetime", self.rules(cid))
            self.assertNotIn("cooldownMonths", self.rules(cid))

    def test_every_min_spend_window_is_3_to_6_months(self):
        # the engine's spend capacity is defined for 3 to 6 months (spendCapacity)
        for c in CATALOG:
            if "typicalMinSpend" in c:
                self.assertTrue(3 <= c["typicalMinSpend"]["months"] <= 6, c["id"])

    def test_every_cooldown_is_24_or_48_months(self):
        # the engine reads windows from four count buckets, so only these two lengths can be decided
        for c in CATALOG:
            months = c.get("bonusRules", {}).get("cooldownMonths")
            self.assertIn(months, (None, 24, 48), c["id"])

    def test_capital_one_personal_cards_use_48_months(self):
        self.assertEqual(self.rules("capone-quicksilver")["cooldownMonths"], 48)
        self.assertEqual(self.rules("capone-spark-cash"), {})

    def test_us_bank_cards_have_no_exact_card_rule(self):
        # the "no bonus while the exact card is open" rule is outdated or YMMV (owner, 2026-09-21)
        for cid in ("usbank-triple-cash", "usbank-business-leverage", "usbank-altitude-connect"):
            self.assertEqual(self.rules(cid), {}, cid)

    def test_barclays_cards_cannot_be_held_twice(self):
        self.assertTrue(self.rules("barclays-jetblue").get("blockedWhileHeld"))

    def test_other_chase_cards_use_24_months(self):
        r = self.rules("chase-freedom-unlimited")
        self.assertEqual((r["cooldownMonths"], r["cooldownBasis"], r["blockedWhileHeld"]), (24, "bonus", True))


class ReferencesResolve(unittest.TestCase):
    def test_cards_named_by_the_matrix_exist(self):
        for c in MATRIX["cards"]:
            self.assertIn(c["id"], BY_ID)

    def test_cards_named_by_rules_exist(self):
        for c in CATALOG:
            for other in c.get("bonusRules", {}).get("lifetimeAlsoBlockedBy", []):
                self.assertIn(other, BY_ID)

    def test_history_only_cards_are_not_recommendable(self):
        for cid in ("chase-ritz-carlton", "citi-premier", "citi-strata-student", "amex-delta-options", "amex-hilton-ascend"):
            self.assertFalse(BY_ID[cid]["recommendable"], cid)
            self.assertNotIn("welcomeBonus", BY_ID[cid])


class WelcomeBonuses(unittest.TestCase):
    def test_the_six_unvalued_cards_are_unranked(self):
        for cid in UNVALUED:
            self.assertIn("unrankedReason", BY_ID[cid], cid)
            self.assertNotIn("currency", BY_ID[cid], cid)

    def test_discover_match_offers_are_unranked(self):
        self.assertIn("unrankedReason", BY_ID["discover-it-cash-back"])

    def test_every_ranked_card_has_a_currency_the_valuations_know(self):
        for c in CATALOG:
            if c["recommendable"] and "unrankedReason" not in c:
                self.assertIn(c["currency"], list(VALUATIONS["values"]) + ["cash"], c["id"])

    def test_cash_paid_as_points_keep_the_displayed_figure(self):
        b = BY_ID["chase-ink-cash"]["welcomeBonus"]
        self.assertEqual((b["points"], b["displayedAsCash"]), (75000, 750))
        self.assertNotIn("cashBack", b)

    def test_stored_bonus_reproduces_the_value_module(self):
        for c in CATALOG:
            b = c.get("welcomeBonus")
            if not b or c.get("currency") in (None, "cash"):
                continue
            parsed = OFFERS[c["id"]]["parsed"]
            cert = None
            if parsed["freeNightAwards"]:
                from cardfinder.registry import FREE_NIGHT_CERTIFICATE
                cert = FREE_NIGHT_CERTIFICATE[c["id"]]
            expected = bonus_value(parsed, c["currency"], VALUATIONS, unlocked=True, certificate=cert)
            cpp = VALUATIONS["values"][c["currency"]]
            cpp = cpp["withUnlocker"] if isinstance(cpp, dict) else cpp
            actual = (b.get("points") or 0) * cpp / 100 + (b.get("cashBack") or 0) + (b.get("otherValue") or 0)
            self.assertAlmostEqual(actual, expected, places=6, msg=c["id"])

    def test_free_night_certificates_are_stored_as_other_value(self):
        b = BY_ID["amex-hilton-surpass"]["welcomeBonus"]
        self.assertEqual(b["otherValue"], VALUATIONS["freeNightCertificates"]["hilton"])

    def test_the_number_of_free_nights_is_kept_for_display(self):
        self.assertEqual(BY_ID["amex-hilton-surpass"]["welcomeBonus"]["freeNights"], 1)
        self.assertEqual(BY_ID["chase-marriott-boundless"]["welcomeBonus"]["freeNights"], 3)  # "Earn 3 Free Night Awards"
        self.assertNotIn("freeNights", BY_ID["amex-platinum"]["welcomeBonus"])
        for c in CATALOG:
            b = c.get("welcomeBonus", {})
            self.assertEqual("freeNights" in b, "otherValue" in b, c["id"])

    def test_extra_tiers_are_kept_for_the_engine(self):
        self.assertTrue(BY_ID["chase-aeroplan"]["welcomeBonus"]["additionalTiers"])

    def test_spot_checks(self):
        self.assertEqual(BY_ID["chase-world-of-hyatt"]["welcomeBonus"]["points"], 30000)
        self.assertEqual(BY_ID["amex-delta-gold-business"]["welcomeBonus"]["points"], 90000)
        self.assertEqual(BY_ID["amex-delta-gold-business"]["typicalMinSpend"], {"amount": 6000, "months": 6})


if __name__ == "__main__":
    unittest.main()
