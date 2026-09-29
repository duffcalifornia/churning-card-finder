import os
import tempfile
import unittest

from cardfinder.changelog import (
    currency_label, fee_change_entry, format_list, offer_change_entry, prepend_changelog_entry, removed_cards_entry,
    valuation_change_entry,
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


class RemovedCardsEntryTests(unittest.TestCase):
    def test_one_card(self):
        self.assertEqual(removed_cards_entry(["Split Card World Mastercard"]),
                         "Removed the following card(s) because they can no longer be applied for: Split Card World Mastercard.")

    def test_two_cards_are_sorted_and_joined(self):
        self.assertEqual(removed_cards_entry(["Business Leverage", "Business Altitude Power"]),
                         "Removed the following card(s) because they can no longer be applied for: Business Altitude Power and Business Leverage.")


class OfferChangeEntryTests(unittest.TestCase):
    """old_records/new_records are keyed by card id, each value shaped like one of
    cardfinder.build.build_parsed_offers' records: {"hasWelcomeOffer": bool, "parsed": {...}}."""

    NAMES = {"chase-sapphire-preferred": "Chase Sapphire Preferred", "amex-gold": "American Express Gold Card"}

    @staticmethod
    def _offer(points, **extra):
        parsed = {"kind": "standard", "points": points, "cashBack": None, "freeNightAwards": 0, "minSpend": 4000.0,
                  "windowMonths": 3, "additionalTiers": [], "ceiling": False, "displayedAsCash": None, **extra}
        return {"hasWelcomeOffer": True, "parsed": parsed}

    def test_no_change_is_none(self):
        old = {"chase-sapphire-preferred": self._offer(75000.0)}
        new = {"chase-sapphire-preferred": self._offer(75000.0)}
        self.assertIsNone(offer_change_entry(old, new, self.NAMES))

    def test_cosmetic_page_text_differences_are_not_a_change(self):
        # The actual bug this guards against: the scraped page text can reformat (an en dash swapped for a
        # hyphen, marketing copy trimmed) between reads with the parsed offer identical either way - only the
        # parsed value fields are compared, never raw text, so this must not be reported as a change.
        old = {"amex-gold": self._offer(60000.0)}
        new = {"amex-gold": self._offer(60000.0)}  # same parsed value, as if only the raw page text had changed
        self.assertIsNone(offer_change_entry(old, new, self.NAMES))

    def test_one_card_changed(self):
        old = {"chase-sapphire-preferred": self._offer(60000.0)}
        new = {"chase-sapphire-preferred": self._offer(75000.0)}
        self.assertEqual(
            offer_change_entry(old, new, self.NAMES),
            "Updated the bonus offer for the following card(s): Chase Sapphire Preferred.",
        )

    def test_a_change_to_a_non_points_field_still_counts(self):
        # Minimum spend moving (with points unchanged) is just as real a value change as points moving.
        old = {"amex-gold": self._offer(60000.0, minSpend=4000.0)}
        new = {"amex-gold": self._offer(60000.0, minSpend=6000.0)}
        self.assertEqual(offer_change_entry(old, new, self.NAMES), "Updated the bonus offer for the following card(s): American Express Gold Card.")

    def test_notes_changing_alone_is_not_a_change(self):
        # `notes` is scraper commentary, not a value - deliberately excluded from the comparison.
        old = {"amex-gold": {**self._offer(60000.0), "notes": ["needs review"]}}
        new = {"amex-gold": {**self._offer(60000.0), "notes": []}}
        self.assertIsNone(offer_change_entry(old, new, self.NAMES))

    def test_multiple_cards_changed_join_with_oxford_comma(self):
        old = {"chase-sapphire-preferred": self._offer(60000.0), "amex-gold": self._offer(60000.0)}
        new = {"chase-sapphire-preferred": self._offer(75000.0), "amex-gold": self._offer(100000.0)}
        result = offer_change_entry(old, new, self.NAMES)
        self.assertEqual(result, "Updated the bonus offer for the following card(s): American Express Gold Card and Chase Sapphire Preferred.")

    def test_a_brand_new_offer_where_none_existed_counts_as_changed(self):
        old = {}
        new = {"amex-gold": self._offer(100000.0)}
        self.assertEqual(offer_change_entry(old, new, self.NAMES), "Updated the bonus offer for the following card(s): American Express Gold Card.")

    def test_losing_a_recorded_offer_counts_as_changed(self):
        old = {"amex-gold": self._offer(100000.0)}
        new = {"amex-gold": {"hasWelcomeOffer": False, "parsed": None}}
        self.assertEqual(offer_change_entry(old, new, self.NAMES), "Updated the bonus offer for the following card(s): American Express Gold Card.")

    def test_unmapped_card_id_falls_back_to_the_id_itself(self):
        old = {"some-new-card": self._offer(50000.0)}
        new = {"some-new-card": self._offer(60000.0)}
        self.assertEqual(offer_change_entry(old, new, {}), "Updated the bonus offer for the following card(s): some-new-card.")

    def test_only_reports_ids_present_in_new_offers(self):
        # A card dropped from the cache entirely (should not happen in practice) is not reported as "changed".
        old = {"amex-gold": self._offer(100000.0)}
        new = {}
        self.assertIsNone(offer_change_entry(old, new, self.NAMES))


class FeeChangeEntryTests(unittest.TestCase):
    """Owner's rule (2026-09-22): a fee-only change (the offer text itself did not move) gets its own line,
    deliberately keeping "card" singular in the template even when more than one card changed, since the owner
    expects this to be rare enough that singular reads fine either way."""

    NAMES = {"chase-sapphire-preferred": "Chase Sapphire Preferred", "amex-gold": "American Express Gold Card"}

    def test_no_change_is_none(self):
        entry = fee_change_entry({"amex-gold": 250.0}, {"amex-gold": 250.0}, set(), set(), self.NAMES)
        self.assertIsNone(entry)

    def test_one_cards_fee_amount_changed(self):
        entry = fee_change_entry({"amex-gold": 250.0}, {"amex-gold": 325.0}, set(), set(), self.NAMES)
        self.assertEqual(entry, "Updated the net value rankings to reflect changes to the annual fee on the following card: American Express Gold Card.")

    def test_newly_waived_first_year_counts_as_a_change(self):
        entry = fee_change_entry({"amex-gold": 250.0}, {"amex-gold": 250.0}, set(), {"amex-gold"}, self.NAMES)
        self.assertEqual(entry, "Updated the net value rankings to reflect changes to the annual fee on the following card: American Express Gold Card.")

    def test_multiple_cards_still_use_the_singular_card_template(self):
        old_fees = {"chase-sapphire-preferred": 95.0, "amex-gold": 250.0}
        new_fees = {"chase-sapphire-preferred": 100.0, "amex-gold": 325.0}
        entry = fee_change_entry(old_fees, new_fees, set(), set(), self.NAMES)
        self.assertEqual(
            entry,
            "Updated the net value rankings to reflect changes to the annual fee on the following card: American Express Gold Card and Chase Sapphire Preferred.",
        )

    def test_a_brand_new_fee_where_none_was_known_counts_as_changed(self):
        entry = fee_change_entry({}, {"amex-gold": 250.0}, set(), set(), self.NAMES)
        self.assertEqual(entry, "Updated the net value rankings to reflect changes to the annual fee on the following card: American Express Gold Card.")

    def test_unmapped_card_id_falls_back_to_the_id_itself(self):
        entry = fee_change_entry({"some-new-card": 0.0}, {"some-new-card": 95.0}, set(), set(), {})
        self.assertEqual(entry, "Updated the net value rankings to reflect changes to the annual fee on the following card: some-new-card.")


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
