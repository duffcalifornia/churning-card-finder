import unittest

from cardfinder.matching import normalize_tokens, match_score, page_matches_card, link_score, distinguishing_tokens


class Card:
    """Minimal stand-in for a registry card."""

    def __init__(self, names, kind="personal"):
        self.names = names
        self.kind = kind


SAPPHIRE_RESERVE = Card(["Chase Sapphire Reserve", "Sapphire Reserve"])
SAPPHIRE_RESERVE_BIZ = Card(["Sapphire Reserve for Business", "Chase Sapphire Reserve Business"], kind="business")
DISNEY_VISA = Card(["Disney Visa Card"])
HILTON_HONORS = Card(["Hilton Honors American Express Card", "Hilton Honors Card"])
AMAZON_BIZ = Card(["Amazon Business American Express Card", "Amazon Business Card"], kind="business")


UNITED_EXPLORER = Card(["United Explorer Card", "United Explorer"])
UNITED_BIZ = Card(["United Business Card", "United Business"], kind="business")


class RealWorldTitles(unittest.TestCase):
    """Title and heading quirks seen on live issuer pages."""

    def page(self, title, h1=""):
        return f"<html><head><title>{title}</title></head><body><h1>{h1}</h1></body></html>"

    def test_ignores_a_site_suffix_after_a_pipe(self):
        self.assertTrue(page_matches_card(UNITED_EXPLORER, self.page("United Explorer Credit Card | Chase.com")))

    def test_ignores_a_tagline_after_a_colon(self):
        self.assertTrue(page_matches_card(UNITED_BIZ, self.page("United Business Credit Card: Airline Rewards | Chase")))

    def test_ignores_service_mark_text_in_headings(self):
        self.assertTrue(page_matches_card(UNITED_EXPLORER, self.page("Apply now", "United SM  Explorer Card")))

    def test_accepts_a_card_named_in_a_later_title_segment(self):
        """Discover: 'Travel Credit Card | Discover it Miles Credit Card'."""
        miles = Card(["Discover it Miles Credit Card", "Discover it Miles"])
        self.assertTrue(page_matches_card(miles, self.page("Travel Credit Card | Discover it Miles Credit Card", "Travel Credit Card")))

    def test_a_generic_title_with_only_the_issuers_name_still_fails(self):
        self.assertFalse(page_matches_card(AMAZON_BIZ, self.page("Business Credit Cards | American Express", "Business Credit Cards")))

    def test_business_word_may_be_in_another_title_segment(self):
        """Capital One: 'Spark Cash | Cash Back Business Credit Card'."""
        spark = Card(["Spark Cash Select", "Spark Cash"], kind="business")
        self.assertTrue(page_matches_card(spark, self.page("Spark Cash | Cash Back Business Credit Card", "Spark Cash")))

    def test_a_business_card_still_needs_business_somewhere_on_the_page(self):
        spark = Card(["Spark Cash"], kind="business")
        self.assertFalse(page_matches_card(spark, self.page("Spark Cash | Cash Back Credit Card", "Spark Cash")))

    def test_a_personal_card_is_still_not_matched_to_a_business_titled_page(self):
        delta = Card(["Delta SkyMiles Gold"], kind="personal")
        self.assertFalse(page_matches_card(delta, self.page("Delta SkyMiles Gold Business American Express Card | American Express")))

    def test_us_bank_names_match_despite_the_u_s_prefix(self):
        leverage = Card(["U.S. Bank Business Leverage Visa Signature Card", "Business Leverage"], kind="business")
        self.assertTrue(page_matches_card(leverage, self.page("Business Leverage Visa Signature Rewards Credit Card | U.S. Bank",
                                                               "Business Leverage\u00ae Visa Signature\u00ae Card")))

    def test_still_rejects_a_sibling_with_the_same_prefix(self):
        self.assertFalse(page_matches_card(UNITED_EXPLORER, self.page("United Quest Credit Card | Chase.com")))


AEROPLAN = Card(["Air Canada Aeroplan Card", "Aeroplan Credit Card", "Air Canada Aeroplan"])
DISNEY = Card(["Disney Visa Card"])


class LinkScore(unittest.TestCase):
    """Looser than match_score: used to shortlist links, which are then checked against the page itself."""

    def test_finds_a_card_whose_slug_has_a_section_prefix_and_merged_words(self):
        self.assertGreaterEqual(link_score(AEROPLAN, "/travel-credit-cards/aircanada/aeroplan"), 0.5)

    def test_shortlists_the_disney_pages_even_though_slugs_never_say_visa(self):
        self.assertGreaterEqual(link_score(DISNEY, "/rewards-credit-cards/disney/rewards"), 0.4)

    def test_a_tighter_slug_outranks_a_longer_one(self):
        tight = link_score(SAPPHIRE_RESERVE, "/rewards/sapphire/reserve")
        loose = link_score(SAPPHIRE_RESERVE, "/rewards/sapphire/reserve/benefits/travel/lounges")
        self.assertGreater(tight, loose)

    def test_still_separates_business_from_personal(self):
        self.assertGreater(link_score(SAPPHIRE_RESERVE, "/rewards-credit-cards/sapphire/reserve"),
                           link_score(SAPPHIRE_RESERVE, "/business-credit-cards/sapphire/reserve"))

    def test_unrelated_links_score_low(self):
        self.assertLess(link_score(SAPPHIRE_RESERVE, "/cash-back-credit-cards/freedom/unlimited"), 0.3)


class DistinguishingTokens(unittest.TestCase):
    def test_collects_the_extra_words_of_sibling_cards_that_contain_this_cards_name(self):
        base = Card(["Hilton Honors American Express Card", "Hilton Honors Card"])
        surpass = Card(["Hilton Honors American Express Surpass Card"])
        aspire = Card(["Hilton Honors American Express Aspire Card"])
        other = Card(["Marriott Bonvoy Bevy Card"])
        self.assertEqual(distinguishing_tokens(base, [base, surpass, aspire, other]), {"surpass", "aspire"})

    def test_a_card_with_no_such_siblings_has_none(self):
        self.assertEqual(distinguishing_tokens(SAPPHIRE_RESERVE, [SAPPHIRE_RESERVE, Card(["Freedom Unlimited"])]), set())

    def test_business_and_personal_versions_are_not_siblings(self):
        personal = Card(["Delta SkyMiles Gold"], kind="personal")
        business = Card(["Delta SkyMiles Gold Business"], kind="business")
        self.assertEqual(distinguishing_tokens(personal, [personal, business]), set())


class NormalizeTokens(unittest.TestCase):
    def test_strips_trademark_symbols_and_filler_words(self):
        self.assertEqual(normalize_tokens("The Platinum Card® from American Express"), {"platinum"})

    def test_splits_url_slugs(self):
        self.assertEqual(normalize_tokens("/rewards-credit-cards/sapphire/reserve"), {"rewards", "sapphire", "reserve"})

    def test_is_case_and_punctuation_insensitive(self):
        self.assertEqual(normalize_tokens("Ink Business Cash®"), normalize_tokens("ink-business-cash"))


class MatchScore(unittest.TestCase):
    def test_exact_name_scores_full(self):
        self.assertEqual(match_score(SAPPHIRE_RESERVE, "Chase Sapphire Reserve"), 1.0)

    def test_matches_a_url_slug_of_the_right_card(self):
        self.assertGreaterEqual(match_score(SAPPHIRE_RESERVE, "/rewards-credit-cards/sapphire/reserve"), 0.6)

    def test_unrelated_card_scores_low(self):
        self.assertLess(match_score(SAPPHIRE_RESERVE, "/cash-back-credit-cards/freedom/unlimited"), 0.3)

    def test_personal_card_prefers_personal_url_over_business_url(self):
        personal = match_score(SAPPHIRE_RESERVE, "/rewards-credit-cards/sapphire/reserve")
        business = match_score(SAPPHIRE_RESERVE, "/business-credit-cards/sapphire/reserve")
        self.assertGreater(personal, business)

    def test_business_card_prefers_business_url_over_personal_url(self):
        personal = match_score(SAPPHIRE_RESERVE_BIZ, "/rewards-credit-cards/sapphire/reserve")
        business = match_score(SAPPHIRE_RESERVE_BIZ, "/business-credit-cards/sapphire/reserve")
        self.assertGreater(business, personal)

    def test_best_alias_wins(self):
        self.assertEqual(match_score(SAPPHIRE_RESERVE, "Sapphire Reserve"), 1.0)


class PageMatchesCard(unittest.TestCase):
    def test_accepts_page_whose_title_names_the_card(self):
        html = "<html><head><title>Chase Sapphire Reserve® Credit Card</title></head><body><h1>Chase Sapphire Reserve</h1></body></html>"
        self.assertTrue(page_matches_card(SAPPHIRE_RESERVE, html))

    def test_rejects_generic_index_page_a_redirect_landed_on(self):
        html = "<html><head><title>Business Credit Cards from American Express</title></head><body><h1>Business Credit Cards</h1></body></html>"
        self.assertFalse(page_matches_card(AMAZON_BIZ, html))

    def test_rejects_wrong_card_with_overlapping_words(self):
        html = "<html><head><title>Chase Sapphire Preferred® Credit Card</title></head><body><h1>Sapphire Preferred</h1></body></html>"
        self.assertFalse(page_matches_card(SAPPHIRE_RESERVE, html))

    def test_rejects_a_sibling_card_that_only_adds_one_word(self):
        premier = "<html><head><title>Disney\u00ae Premier Visa\u00ae Card</title></head><body></body></html>"
        base = "<html><head><title>Disney\u00ae Visa\u00ae Card</title></head><body></body></html>"
        self.assertFalse(page_matches_card(DISNEY_VISA, premier))
        self.assertTrue(page_matches_card(DISNEY_VISA, base))

    def test_base_hilton_card_is_not_confused_with_its_upgrades(self):
        surpass = "<html><head><title>Hilton Honors American Express Surpass\u00ae Card</title></head></html>"
        self.assertFalse(page_matches_card(HILTON_HONORS, surpass))

    def test_falls_back_to_h1_when_title_is_useless(self):
        html = "<html><head><title>Apply now</title></head><body><h1>Chase Sapphire Reserve</h1></body></html>"
        self.assertTrue(page_matches_card(SAPPHIRE_RESERVE, html))


if __name__ == "__main__":
    unittest.main()
