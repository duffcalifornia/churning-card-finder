import unittest

from cardfinder.registry import CARDS, ISSUERS, LAST_KNOWN_FEES


class Registry(unittest.TestCase):
    def test_card_ids_are_unique(self):
        ids = [c.id for c in CARDS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_card_belongs_to_a_configured_issuer(self):
        for c in CARDS:
            self.assertIn(c.issuer, ISSUERS, c.id)

    def test_every_card_has_a_name(self):
        for c in CARDS:
            self.assertTrue(c.names and all(c.names), c.id)

    def test_expected_cards_have_a_known_url_to_start_from(self):
        for c in CARDS:
            if c.expected:
                self.assertTrue(c.urls, c.id)

    def test_cards_that_are_not_expected_say_why(self):
        for c in CARDS:
            if not c.expected:
                self.assertTrue(c.note, c.id)

    def test_amex_needs_rendering_and_chase_does_not(self):
        self.assertTrue(ISSUERS["amex"].render)
        self.assertFalse(ISSUERS["chase"].render)

    def test_known_discontinued_amex_cards_are_not_expected(self):
        by_id = {c.id: c for c in CARDS}
        for cid in ("amex-cash-magnet", "amex-everyday-preferred", "amex-amazon-business", "amex-amazon-business-prime"):
            self.assertFalse(by_id[cid].expected, cid)

    def test_last_known_fees_refer_to_real_cards_and_are_sane(self):
        ids = {c.id for c in CARDS}
        for cid, fee in LAST_KNOWN_FEES.items():
            self.assertIn(cid, ids)
            self.assertGreaterEqual(fee, 0)

    def test_cards_carry_their_last_known_fee(self):
        by_id = {c.id: c for c in CARDS}
        self.assertEqual(by_id["chase-sapphire-preferred"].expected_fee, 95.0)
        self.assertEqual(by_id["amex-platinum"].expected_fee, 895.0)

    def test_owner_provided_fees_are_recorded(self):
        by_id = {c.id: c for c in CARDS}
        for cid in ("amex-blue-cash-everyday", "amex-delta-blue", "amex-hilton-honors"):
            self.assertEqual((by_id[cid].known_fee, by_id[cid].known_fee_first_year_waived), (0.0, False), cid)
        self.assertEqual(by_id["usbank-business-altitude-power"].known_fee, 195.0)

    def test_business_cards_are_marked_business(self):
        for c in CARDS:
            if "business" in c.urls[0].lower() if c.urls else False:
                self.assertEqual(c.kind, "business", c.id)


if __name__ == "__main__":
    unittest.main()
