import os
import tempfile
import unittest

from cardfinder.changelog import (
    currency_label, format_list, offer_change_entry, prepend_changelog_entry, valuation_change_entry,
)


class FormatListTests(unittest.TestCase):
    def test_one(self):
        self.assertEqual(format_list(["Chase Sapphire Preferred"]), "Chase Sapphire Preferred")

    def test_two(self):
        self.assertEqual(format_list(["A", "B"]), "A and B")

    def test_three_uses_oxford_comma(self):
        self.assertEqual(format_list(["A", "B", "C"]), "A, B, and C")

    def test_empty(self):
        self.assertEqual(format_list([]), "")


class OfferChangeEntryTests(unittest.TestCase):
    NAMES = {"chase-sapphire-preferred": "Chase Sapphire Preferred", "amex-gold": "American Express Gold Card"}

    def test_no_change_is_none(self):
        old = {"chase-sapphire-preferred": {"text": "75,000 points"}}
        new = {"chase-sapphire-preferred": {"text": "75,000 points"}}
        self.assertIsNone(offer_change_entry(old, new, self.NAMES))

    def test_one_card_changed(self):
        old = {"chase-sapphire-preferred": {"text": "60,000 points"}}
        new = {"chase-sapphire-preferred": {"text": "75,000 points"}}
        self.assertEqual(
            offer_change_entry(old, new, self.NAMES),
            "Updated the bonus offer for the following card(s): Chase Sapphire Preferred.",
        )

    def test_multiple_cards_changed_join_with_oxford_comma(self):
        old = {"chase-sapphire-preferred": {"text": "60,000"}, "amex-gold": {"text": "60,000"}}
        new = {"chase-sapphire-preferred": {"text": "75,000"}, "amex-gold": {"text": "100,000"}}
        result = offer_change_entry(old, new, self.NAMES)
        self.assertEqual(result, "Updated the bonus offer for the following card(s): American Express Gold Card and Chase Sapphire Preferred.")

    def test_a_brand_new_offer_where_none_existed_counts_as_changed(self):
        old = {}
        new = {"amex-gold": {"text": "100,000 points"}}
        self.assertEqual(offer_change_entry(old, new, self.NAMES), "Updated the bonus offer for the following card(s): American Express Gold Card.")

    def test_unmapped_card_id_falls_back_to_the_id_itself(self):
        old = {"some-new-card": {"text": "old"}}
        new = {"some-new-card": {"text": "new"}}
        self.assertEqual(offer_change_entry(old, new, {}), "Updated the bonus offer for the following card(s): some-new-card.")

    def test_only_reports_ids_present_in_new_offers(self):
        # A card dropped from the cache entirely (should not happen in practice) is not reported as "changed".
        old = {"amex-gold": {"text": "100,000"}}
        new = {}
        self.assertIsNone(offer_change_entry(old, new, self.NAMES))


class CurrencyLabelTests(unittest.TestCase):
    def test_known_currency_uses_its_real_name(self):
        self.assertEqual(currency_label("ultimate-rewards"), "Chase Ultimate Rewards")
        self.assertEqual(currency_label("hilton-honors"), "Hilton Honors")

    def test_unmapped_currency_falls_back_to_title_casing_the_id(self):
        self.assertEqual(currency_label("some-new-program"), "Some New Program")


class ValuationChangeEntryTests(unittest.TestCase):
    def test_no_change_is_none(self):
        old = {"cash": 1, "avios": 1.1}
        new = {"cash": 1, "avios": 1.1}
        self.assertIsNone(valuation_change_entry(old, new))

    def test_one_program_changed(self):
        old = {"avios": 1.1}
        new = {"avios": 1.2}
        self.assertEqual(
            valuation_change_entry(old, new),
            "Updated the rankings to reflect changes to the value of Avios.",
        )

    def test_nested_with_unlocker_shape_is_compared_too(self):
        old = {"ultimate-rewards": {"withUnlocker": 1.5, "withoutUnlocker": 1.0}}
        new = {"ultimate-rewards": {"withUnlocker": 1.5, "withoutUnlocker": 1.1}}
        self.assertEqual(
            valuation_change_entry(old, new),
            "Updated the rankings to reflect changes to the value of Chase Ultimate Rewards.",
        )

    def test_multiple_programs_changed(self):
        old = {"avios": 1.1, "hilton-honors": 0.5}
        new = {"avios": 1.2, "hilton-honors": 0.6}
        self.assertEqual(
            valuation_change_entry(old, new),
            "Updated the rankings to reflect changes to the value of Avios and Hilton Honors.",
        )

    def test_a_brand_new_program_counts_as_changed(self):
        old = {}
        new = {"avios": 1.1}
        self.assertEqual(valuation_change_entry(old, new), "Updated the rankings to reflect changes to the value of Avios.")


class PrependChangelogEntryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
        self.tmp.write("What changed. Newest first.\n\n## 2026-09-20\n- An older entry.\n")
        self.tmp.close()
        self.addCleanup(os.unlink, self.tmp.name)

    def test_creates_a_new_dated_section_at_the_top(self):
        prepend_changelog_entry(self.tmp.name, "2026-09-22", "A new automated entry.")
        content = open(self.tmp.name).read()
        self.assertEqual(
            content,
            "What changed. Newest first.\n\n## 2026-09-22\n- A new automated entry.\n\n## 2026-09-20\n- An older entry.\n",
        )

    def test_adds_a_bullet_to_an_existing_section_for_the_same_date(self):
        prepend_changelog_entry(self.tmp.name, "2026-09-22", "First entry today.")
        prepend_changelog_entry(self.tmp.name, "2026-09-22", "Second entry today.")
        content = open(self.tmp.name).read()
        self.assertEqual(
            content,
            "What changed. Newest first.\n\n## 2026-09-22\n- First entry today.\n- Second entry today.\n\n## 2026-09-20\n- An older entry.\n",
        )


if __name__ == "__main__":
    unittest.main()
