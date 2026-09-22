import json
import os
import unittest

from cardfinder.value import bonus_value, net_value

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
VALUATIONS = json.load(open(os.path.join(ROOT, "data", "valuations.json")))
SCHEMA = json.load(open(os.path.join(ROOT, "data", "schema", "valuations.schema.json")))


def offer(points=None, cash=None, nights=0, tiers=()):
    return {"points": points, "cashBack": cash, "freeNightAwards": nights, "additionalTiers": list(tiers)}


V = {"values": {"cash": 1, "x": 1.5, "ur": {"withUnlocker": 1.5, "withoutUnlocker": 1.0}},
     "freeNightCertificates": {"marriott-50k": 274}}


class BonusValue(unittest.TestCase):
    def test_points_times_cents_per_point(self):
        self.assertAlmostEqual(bonus_value(offer(points=100000), "x", V), 1500.0)

    def test_cash_is_added_at_face_value(self):
        self.assertAlmostEqual(bonus_value(offer(points=50000, cash=150), "x", V), 900.0)

    def test_two_rate_currencies_depend_on_whether_the_household_can_transfer(self):
        self.assertAlmostEqual(bonus_value(offer(points=75000), "ur", V, unlocked=True), 1125.0)
        self.assertAlmostEqual(bonus_value(offer(points=75000), "ur", V, unlocked=False), 750.0)

    def test_free_night_awards_use_the_certificate_value_times_the_count(self):
        self.assertAlmostEqual(bonus_value(offer(nights=3), "x", V, certificate="marriott-50k"), 822.0)

    def test_free_nights_without_a_certificate_type_are_an_error_not_a_guess(self):
        with self.assertRaises(ValueError):
            bonus_value(offer(nights=1), "x", V)

    def test_a_second_tier_counts_only_when_asked(self):
        o = offer(points=75000, tiers=[{"points": 40000, "cashBack": None}])
        self.assertAlmostEqual(bonus_value(o, "x", V), 1125.0)
        self.assertAlmostEqual(bonus_value(o, "x", V, include_tiers=True), 1725.0)

    def test_an_unknown_currency_is_an_error(self):
        with self.assertRaises(KeyError):
            bonus_value(offer(points=1000), "nope", V)

    def test_net_value_subtracts_the_raw_annual_fee(self):
        self.assertAlmostEqual(net_value(offer(points=100000), "x", V, annual_fee=95), 1405.0)


class TheSiteValuations(unittest.TestCase):
    def test_the_file_matches_its_schema(self):
        import jsonschema
        jsonschema.validate(VALUATIONS, SCHEMA)

    def test_frequent_miler_values_are_the_site_values(self):
        v = VALUATIONS["values"]
        self.assertEqual(v["amex-membership-rewards"], 1.5)
        self.assertEqual(v["marriott-bonvoy"], 0.73)
        self.assertEqual(v["hilton-honors"], 0.35)
        self.assertEqual(v["atmos-rewards"], 1.5)
        self.assertEqual(v["delta-skymiles"], 1.1)

    def test_citi_and_capital_one_cash_out_at_one_cent(self):
        v = VALUATIONS["values"]
        self.assertEqual(v["citi-thankyou"], {"withUnlocker": 1.5, "withoutUnlocker": 1.0})
        self.assertEqual(v["capital-one-miles"], {"withUnlocker": 1.45, "withoutUnlocker": 1.0})
        self.assertEqual(v["ultimate-rewards"], {"withUnlocker": 1.5, "withoutUnlocker": 1.0})

    def test_free_night_certificates_use_frequent_millers_discounted_values(self):
        c = VALUATIONS["freeNightCertificates"]
        self.assertEqual((c["marriott-50k"], c["marriott-35k"], c["hilton"], c["hyatt-cat-1-4"], c["ihg-40k"]), (274, 192, 521, 240, 201))

    def test_the_transfer_matrix_currencies_all_have_a_value(self):
        for cid in ("ultimate-rewards", "amex-membership-rewards", "citi-thankyou", "capital-one-miles", "wells-fargo-rewards"):
            self.assertIn(cid, VALUATIONS["values"])


if __name__ == "__main__":
    unittest.main()
