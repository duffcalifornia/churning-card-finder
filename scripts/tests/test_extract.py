import unittest

from cardfinder.extract import page_text, extract_offer, extract_fee, main_heading, from_main_heading, looks_like_error_page, links


class PageText(unittest.TestCase):
    def test_strips_scripts_styles_and_tags(self):
        html = "<style>.a{}</style><script>var x=1</script><p>Earn <b>75,000</b> points</p>"
        self.assertEqual(page_text(html), "Earn 75,000 points")

    def test_unescapes_entities(self):
        self.assertEqual(page_text("<p>Fees &amp; terms</p>"), "Fees & terms")


class ExtractOffer(unittest.TestCase):
    def test_chase_style_offer(self):
        text = "Apply now. Earn 75,000 points after you spend $5,000 in purchases in the first 3 months from account opening. Other text."
        offer = extract_offer(text)
        self.assertIn("Earn 75,000 points after you spend $5,000", offer.text)
        self.assertFalse(offer.ceiling)
        self.assertFalse(offer.struck_through)

    def test_cash_bonus_offer(self):
        offer = extract_offer("Earn a $200 bonus after you spend $500 on purchases in the first 3 months from account opening")
        self.assertIn("$200 bonus", offer.text)

    def test_gift_card_on_approval_offer(self):
        offer = extract_offer("Get a $150 Amazon Gift Card instantly loaded into your account on approval of your credit card application.")
        self.assertIn("$150 Amazon Gift Card", offer.text)

    def test_amex_as_high_as_is_marked_as_a_ceiling(self):
        text = ("APPLY AND FIND OUT YOUR WELCOME OFFER AS HIGH AS 175,000 after you spend $12,000 in purchases "
                "on your new Card within the first 6 months of Card Membership. Welcome offers vary and you may not be eligible for an offer.")
        offer = extract_offer(text)
        self.assertTrue(offer.ceiling)
        self.assertIn("175,000", offer.text)
        self.assertIn("$12,000", offer.text)

    def test_strike_through_wording_is_flagged(self):
        offer = extract_offer("Earn 150,000 strike through 200,000 points after you spend $30,000 on purchases in your first 6 months from account opening")
        self.assertTrue(offer.struck_through)

    def test_two_adjacent_bonus_numbers_are_flagged(self):
        offer = extract_offer("Earn 60,000 90,000 Bonus Miles after you spend $6,000 in purchases on your new Card in your first 6 months of Card Membership.")
        self.assertTrue(offer.struck_through)

    def test_hidden_offer_returns_none(self):
        self.assertIsNone(extract_offer("Welcome Offer & Key Details Apply and find out your welcome offer"))

    def test_earn_rates_are_not_a_welcome_offer(self):
        self.assertIsNone(extract_offer("Earn 5x total points on Lyft rides through 9/30/27. Earn 3x on dining."))

    def test_records_which_pattern_found_it(self):
        self.assertEqual(extract_offer("Earn a $200 bonus after you spend $500 on purchases in the first 3 months").method, "after_spend")
        self.assertEqual(extract_offer("Get a $50 Instacart credit automatically upon approval").method, "on_approval")


class OfferTextIsClean(unittest.TestCase):
    """Live pages surround the offer with bullets, repeated headings and footnotes."""

    def test_starts_at_the_earn_closest_to_the_spend_requirement(self):
        text = ("Earn 140,000 Bonus Points * Opens offer details overlay up to 26X at IHG * Opens offer details overlay "
                "NEW CARDMEMBER OFFER Earn 140,000 Bonus Points after you spend $3,000 on purchases in the first 3 months from account opening")
        offer = extract_offer(text)
        self.assertTrue(offer.text.startswith("Earn 140,000 Bonus Points after you spend $3,000"), offer.text)

    def test_collapses_a_repeated_heading(self):
        offer = extract_offer("Earn a $200 bonus Earn a $200 bonus after you spend $500 on purchases in the first 3 months from account opening")
        self.assertEqual(offer.text.count("Earn a $200 bonus"), 1)

    def test_cuts_footnote_asterisks(self):
        offer = extract_offer("Earn 100,000 points after you spend $6,000 in purchases in the first 3 months from account opening * $2,000 value of 100,000 points for select flights")
        self.assertNotIn("*", offer.text)
        self.assertNotIn("$2,000 value", offer.text)

    def test_cuts_a_trailing_bullet_after_an_approval_offer(self):
        offer = extract_offer("Get a $50 Instacart credit automatically upon approval * AT A GLANCE Turn everyday shopping into rewards")
        self.assertEqual(offer.text, "Get a $50 Instacart credit automatically upon approval")

    def test_keeps_the_two_part_hyatt_offer_but_drops_its_footnote(self):
        offer = extract_offer("Earn up to 60,000 Bonus Points 30,000 Bonus Points after you spend $3,000 on purchases in your first 3 months of account opening * and up to 30,000 more Bonus Points")
        self.assertIn("after you spend $3,000", offer.text)
        self.assertNotIn("*", offer.text)


class OfferWithAbbreviationPeriods(unittest.TestCase):
    def test_finds_an_offer_whose_text_contains_us_periods(self):
        text = ("Earn two round-trip Delta Comfort Flight Certificates valid for travel to the U.S. 48, Puerto Rico, or the U.S. Virgin Islands, "
                "along with 50,000 Bonus Miles after you spend $10,000 in purchases on your new Card in the first 6 months. A 21+ day advance purchase is required.")
        offer = extract_offer(text)
        self.assertIn("50,000 Bonus Miles after you spend $10,000", offer.text)
        self.assertEqual(offer.method, "amount_after_spend")


class FeeChoosesTheRightMatch(unittest.TestCase):
    def test_skips_employee_card_fees(self):
        text = ("Business Gold Card Reward Your Growth Annual Fee: $375 \u00a4 more text ... FAQ The Annual Fee for the Employee Business Gold Card "
                "is $95 for the first five Cards and then $95 for each Card after that")
        self.assertEqual(extract_fee(text).amount, 375.0)

    def test_an_employee_fee_alone_is_not_the_cards_fee(self):
        self.assertIsNone(extract_fee("Annual Fee for the Employee Graphite Business Cash Unlimited Card is $95 for the first five Cards"))

    def test_skips_additional_card_fees(self):
        self.assertIsNone(extract_fee("The annual fee for each Additional Platinum Card is $195."))

    def test_takes_the_earliest_match_not_the_first_pattern_tried(self):
        text = "Annual Fee: $150 \u00a4 ... The annual fee for the Delta SkyMiles Gold Card is $99 for something else"
        self.assertEqual(extract_fee(text).amount, 150.0)

    def test_ignores_navigation_fees_before_the_cards_own_heading(self):
        text = "Menu Blue Cash Everyday Annual Fee: $0 \u00a4 More Cards Business Green Rewards Card Annual Fee: $95 \u00a4 Welcome Offer"
        self.assertEqual(extract_fee(text, after="Business Green Rewards Card").amount, 95.0)

    def test_without_a_heading_the_earliest_fee_wins(self):
        text = "Menu Blue Cash Everyday Annual Fee: $0 \u00a4 Business Green Rewards Card Annual Fee: $95"
        self.assertEqual(extract_fee(text).amount, 0.0)

    def test_the_waived_pattern_still_wins_over_the_label_it_contains(self):
        fee = extract_fee("Annual Fee: $0 intro annual fee for the first year, then $95 \u00a4")
        self.assertEqual((fee.amount, fee.first_year_waived), (95.0, True))


class FeeMustBelongToThisCard(unittest.TestCase):
    """On Amex pages other cards' fees appear right after the page's own content."""

    def test_skips_a_neighbouring_cards_fee_and_finds_none_when_this_card_states_no_fee(self):
        text = "Blue Cash Everyday Card Welcome Offer ... Compare Blue Cash Preferred\u00ae Card Annual Fee: $95 \u00a4"
        self.assertIsNone(extract_fee(text, near=["Blue Cash Everyday Card"], others=["Blue Cash Preferred Card"]))

    def test_takes_this_cards_own_fee_over_an_earlier_neighbours(self):
        text = "Blue Cash Preferred\u00ae Card Annual Fee: $95 \u00a4 ... Blue Cash Everyday\u00ae Card Annual Fee: $0 \u00a4"
        self.assertEqual(extract_fee(text, near=["Blue Cash Everyday Card"], others=["Blue Cash Preferred Card"]).amount, 0.0)

    def test_does_not_take_an_upgrade_siblings_fee(self):
        text = "Hilton Honors American Express Surpass\u00ae Card Annual Fee: $150 ... Hilton Honors American Express Card Annual Fee: $0"
        fee = extract_fee(text, near=["Hilton Honors American Express Card"], others=["Hilton Honors American Express Surpass Card"])
        self.assertEqual(fee.amount, 0.0)

    def test_a_faq_sentence_naming_the_card_counts(self):
        text = "Where to look. The annual fee for the American Express Gold Card is $325 for a Basic Card."
        self.assertEqual(extract_fee(text, near=["American Express Gold Card"]).amount, 325.0)


class OtherIssuerOfferWording(unittest.TestCase):
    """Wording seen on Barclays, US Bank and Discover pages (2026-09-20)."""

    def test_barclays_offer(self):
        offer = extract_offer("Rewards Earn 10,000 bonus points after spending $1,000 on purchases in the first 90 days 2 3X points on eligible JetBlue purchases")
        self.assertTrue(offer.text.startswith("Earn 10,000 bonus points after spending $1,000"), offer.text)

    def test_barclays_two_part_offer_keeps_both_parts(self):
        offer = extract_offer("LIMITED-TIME OFFER: Earn up to 100,000 bonus points Earn 45,000 bonus points after spending $1,000 on qualifying purchases in the first 90 days "
                              "and also earn 55,000 bonus points after spending $500 at Hotels by Wyndham in the first 90 days")
        self.assertIn("45,000", offer.text)
        self.assertIn("55,000", offer.text)

    def test_us_bank_just_spend_offer(self):
        offer = extract_offer("U.S. Bank Altitude Connect Visa Signature Card Earn 20,000 bonus points. 1 Just spend $1,000 in Net Purchases in the first 90 days")
        self.assertIn("20,000 bonus points", offer.text)
        self.assertIn("$1,000", offer.text)

    def test_us_bank_reward_bonus_offer(self):
        offer = extract_offer("For a limited time, earn a $200 rewards bonus after you spend $1,000 in eligible purchases within the first 90 days of account opening")
        self.assertIn("$200 rewards bonus after you spend $1,000", offer.text)

    def test_cash_back_match_is_recorded_as_an_offer_without_a_fixed_amount(self):
        offer = extract_offer("Cashback Match: Discover will match all the cash back you earn at the end of your first year after you open your new Discover it Cash Back Card")
        self.assertEqual(offer.method, "first_year_match")

    def test_a_plain_mention_of_cash_back_is_not_a_match_offer(self):
        self.assertIsNone(extract_offer("Earn 1% cash back on all purchases"))


class OtherIssuerFeeWording(unittest.TestCase):
    def test_annual_fee_is(self):
        self.assertEqual(extract_fee("Fee Summary Annual fee $0 Balance transfer fee ... Annual Fee is $0").amount, 0.0)

    def test_annual_fee_with_a_dash(self):
        self.assertEqual(extract_fee("Minimum interest charge - $ 0.50 . Annual fee - $95 Late fee").amount, 95.0)

    def test_annual_fee_followed_by_a_word_not_a_colon(self):
        self.assertEqual(extract_fee("designed to take you further Annual Fee $395 Purchase Rate 19").amount, 395.0)

    def test_states_no_fee_in_words(self):
        self.assertEqual(extract_fee("The Citi Double Cash Card does not charge an annual fee").amount, 0.0)
        self.assertEqual(extract_fee("No, there is no annual fee for the Discover it Card").amount, 0.0)
        self.assertEqual(extract_fee("Enjoy all the benefits with no annual fee plus a 0% intro APR").amount, 0.0)

    def test_navigation_text_is_not_a_fee(self):
        self.assertIsNone(extract_fee("Credit Cards with No Annual Fee Low Intro APR Balance Transfer Credit Cards"))
        self.assertIsNone(extract_fee("Rewards Cards (12) No Annual Fee Cards (19) Cash Back Cards (3)"))


class MoreOfferWording(unittest.TestCase):
    """Wells Fargo, U.S. Bank business and Discover Miles wording (2026-09-20)."""

    def test_when_you_spend_offer(self):
        offer = extract_offer("Active Cash Credit Card Earn a $100 cash rewards bonus when you spend $500 in purchases in the first 3 months 1 Plus, enjoy unlimited 2% cash rewards")
        self.assertIn("$100 cash rewards bonus when you spend $500", offer.text)

    def test_once_you_spend_offer(self):
        offer = extract_offer("Earn 75,000 bonus miles once you spend $4,000 on purchases within 3 months from account opening")
        self.assertIn("once you spend $4,000", offer.text)

    def test_spending_words_without_an_amount_are_not_an_offer(self):
        self.assertIsNone(extract_offer("Earn 5% cash back when you spend at restaurants and gas stations"))

    def test_us_bank_footnote_offer(self):
        offer = extract_offer("New Credit Card Enrollment Bonus: One-time $750 cash back will be awarded if eligible Net Purchases totaling $6,000 or more "
                              "are made to the Account Owner's Card within 180 days of account opening")
        self.assertEqual(offer.method, "one_time_bonus")
        self.assertIn("$750", offer.text)
        self.assertIn("$6,000", offer.text)

    def test_miles_match_is_a_first_year_match_offer(self):
        offer = extract_offer("Unlimited bonus We'll automatically match all the miles you've earned at the end of your first year")
        self.assertEqual(offer.method, "first_year_match")

    def test_cash_back_match_uses_the_same_method(self):
        offer = extract_offer("Discover will match all the cash back you earn at the end of your first year")
        self.assertEqual(offer.method, "first_year_match")


class CitiWording(unittest.TestCase):
    """Rendered Citi pages (2026-09-20)."""

    def test_normalises_dollar_signs_split_from_their_numbers(self):
        self.assertEqual(page_text("<p>after $ 2,500 in purchases</p>"), "after $2,500 in purchases")

    def test_after_an_amount_in_purchases_in_the_first_months(self):
        text = ("Citi / AAdvantage Platinum Select card Earn 50,000 AAdvantage bonus miles after $2,500 in purchases in the first 3 months. "
                "$99 Annual Fee, waived for the first year Free First checked bag")
        offer = extract_offer(text)
        self.assertEqual(offer.method, "after_amount")
        self.assertEqual(offer.text, "Earn 50,000 AAdvantage bonus miles after $2,500 in purchases in the first 3 months")

    def test_an_annual_spend_benefit_is_not_a_welcome_offer(self):
        text = "Earn 4 AAdvantage miles for every $1 spent on eligible purchases After you spend $150,000 in purchases in a calendar year, earn a total of 5 miles for every $1"
        self.assertIsNone(extract_offer(text))

    def test_a_companion_certificate_benefit_is_not_a_welcome_offer(self):
        text = "Earn an American Airlines Companion Certificate for qualifying domestic travel after you spend $30,000 in purchases each cardmembership year and cardmembership is renewed"
        self.assertIsNone(extract_offer(text))

    def test_fee_waived_for_the_first_year(self):
        fee = extract_fee("Free First checked bag $99 Annual Fee, waived for the first year 1 Free First checked bag")
        self.assertEqual((fee.amount, fee.first_year_waived), (99.0, True))

    def test_fee_section_wording(self):
        fee = extract_fee("Annual Fee 1 $99 Waived for the first year Variable APR 1 19.49 %")
        self.assertEqual((fee.amount, fee.first_year_waived), (99.0, True))


class TrailingFootnoteDebris(unittest.TestCase):
    def test_cuts_a_footnote_number_and_what_follows_it(self):
        offer = extract_offer("Earn 60,000 bonus points after spending $4,000 in the first 3 months 2 $95 Annual Fee 1 Annual Hotel Benefit")
        self.assertEqual(offer.text, "Earn 60,000 bonus points after spending $4,000 in the first 3 months")

    def test_cuts_before_a_following_capitalised_item(self):
        offer = extract_offer("Earn 10,000 bonus points after spending $1,000 on purchases in the first 90 days 2 3X points on eligible purchases")
        self.assertTrue(offer.text.endswith("in the first 90 days"), offer.text)

    def test_keeps_numbers_that_are_part_of_the_offer(self):
        offer = extract_offer("Earn 60,000 bonus points after you spend $4,000 in purchases in the first 3 months from account opening")
        self.assertTrue(offer.text.endswith("from account opening"))


class OldAndNewBonusLabels(unittest.TestCase):
    def test_old_bonus_and_new_bonus_labels_are_flagged_like_a_strike_through(self):
        offer = extract_offer("EARN 40,000 old bonus 60,000 new bonus BONUS POINTS when you spend $1,000 in purchases in the first 3 months")
        self.assertTrue(offer.struck_through)


class BareNoFeeStatement(unittest.TestCase):
    """Discover-style "No annual fee" labels count only when nothing more specific is found."""

    def test_a_bare_label_next_to_the_apply_button_counts_as_zero(self):
        self.assertEqual(extract_fee("Balance Transfer Fee applies No annual fee See rates, rewards, fees Apply Now").amount, 0.0)

    def test_menu_headings_never_count(self):
        self.assertIsNone(extract_fee("Explore Credit Cards with No Annual Fee Low Intro APR"))
        self.assertIsNone(extract_fee("Rewards Cards (12) No Annual Fee Cards (19)"))
        self.assertIsNone(extract_fee("Browse No Annual Fee Credit Cards"))

    def test_no_fee_for_the_first_year_is_not_a_zero_fee(self):
        self.assertIsNone(extract_fee("Enjoy no annual fee for the first year"))

    def test_a_stated_fee_wins_over_a_bare_label(self):
        self.assertEqual(extract_fee("No annual fee menu ... Annual Fee: $95").amount, 95.0)


class ErrorPages(unittest.TestCase):
    def test_recognises_an_issuers_loading_error_page(self):
        self.assertTrue(looks_like_error_page("Skip to main Log In Loading Error Sorry, we are unable to load this page at this time. Please try again later."))

    def test_recognises_blocked_access(self):
        self.assertTrue(looks_like_error_page("Access Denied You don't have permission to access this page"))
        self.assertTrue(looks_like_error_page("Please verify you are a human to continue"))

    def test_a_normal_card_page_is_not_an_error(self):
        self.assertFalse(looks_like_error_page("Platinum Card Annual Fee: $895 Earn 80,000 points after you spend $8,000"))


class ErrorPageIsShort(unittest.TestCase):
    def test_a_long_normal_page_with_a_hidden_error_template_is_not_an_error(self):
        page = "Bank of America Customized Cash Rewards Credit Card We're sorry, this page is temporarily unavailable. " + "Real card content. " * 600
        self.assertFalse(looks_like_error_page(page))

    def test_a_short_page_with_the_message_is_an_error(self):
        self.assertTrue(looks_like_error_page("Bank of America Card We're sorry, this page is temporarily unavailable. Visit our homepage"))


class BankOfAmericaWording(unittest.TestCase):
    def test_bonus_after_making_at_least(self):
        text = "Plus, a $200 online cash rewards bonus offer. No annual fee. Online $200 cash rewards bonus after making at least $1,000 in purchases in the first 90 days of your account opening Double your choice category"
        offer = extract_offer(text)
        self.assertIn("$200 cash rewards bonus after making at least $1,000", offer.text)

    def test_a_first_year_category_bonus_alone_is_not_the_welcome_offer(self):
        self.assertIsNone(extract_offer("Earn 3% cash back + 3% first-year cash back bonus in the category of your choice"))


class BankOfAmericaMoreWording(unittest.TestCase):
    def test_headline_bonus_points_offer_is_found_and_marked_partial(self):
        offer = extract_offer("Go back to Spanish 25,000 online bonus points offer (a $250 value) and no annual fee \u2020 Earn unlimited 1.5 points for every $1")
        self.assertEqual(offer.method, "headline_bonus")
        self.assertIn("25,000 online bonus points", offer.text)

    def test_to_qualify_spend_offer(self):
        text = ("Limited-time online offer Get 50,000 bonus points and a $99 Companion Fare (plus taxes and fees from $23) with this offer. "
                "To qualify, spend $1,500 or more on purchases within the first 90 days of account opening.")
        offer = extract_offer(text)
        self.assertEqual(offer.method, "to_qualify_spend")
        self.assertIn("50,000 bonus points", offer.text)
        self.assertIn("spend $1,500", offer.text)

    def test_an_annual_companion_fare_is_not_the_welcome_offer(self):
        self.assertIsNone(extract_offer("Get a $99 Companion Fare (plus taxes and fees from $23) each account anniversary after you spend $10,000 in a year"))


class WithinTheFirstMonths(unittest.TestCase):
    def test_citi_business_offer_says_within_the_first_months(self):
        offer = extract_offer("Citi AAdvantage Business card For business owners Earn 65,000 AAdvantage bonus miles For your business after $4,000 in purchases "
                              "within the first 4 months of account opening. 2 $99 Annual Fee, waived for the first year")
        self.assertEqual(offer.method, "after_amount")
        self.assertEqual(offer.text, "Earn 65,000 AAdvantage bonus miles For your business after $4,000 in purchases within the first 4 months of account opening")


class TermsPageWording(unittest.TestCase):
    def test_you_will_qualify_for_bonus_points(self):
        text = ("FEATURES Bonus Points Offer. You will qualify for 25,000 bonus points if you use your new credit card account to make any combination of "
                "purchase transactions totaling at least $1,000 (excluding any fees) that post to your account within 90 days of the account open date. Returns, credits")
        offer = extract_offer(text)
        self.assertEqual(offer.method, "terms_qualify")
        for part in ("25,000 bonus points", "$1,000", "90 days"):
            self.assertIn(part, offer.text)


class Links(unittest.TestCase):
    def test_resolves_relative_links_and_unescapes_entities(self):
        html = '<a href="/terms/?a=1&amp;b=2">\u2020 Terms &amp; Conditions</a><a href="https://x.com/y">Other</a>'
        self.assertEqual(links(html, "https://ex.com/card/"),
                         [("https://ex.com/terms/?a=1&b=2", "\u2020 Terms & Conditions"), ("https://x.com/y", "Other")])


class UsBankBusinessWording(unittest.TestCase):
    def test_one_time_points_bonus_footnote(self):
        offer = extract_offer("New Credit Card Enrollment Bonus: One-time 75,000 bonus points will be awarded if eligible Net Purchases totaling $10,000 or more "
                              "are made to the Account Owner's Card within 120 days of account opening")
        self.assertEqual(offer.method, "one_time_bonus")
        self.assertIn("75,000 bonus points", offer.text)
        self.assertIn("$10,000", offer.text)

    def test_a_business_menu_heading_is_not_a_zero_fee(self):
        self.assertIsNone(extract_fee("Low intro rate credit cards No annual fee business credit cards Expense management Flexible payments"))
        self.assertIsNone(extract_fee("Explore No annual fee business cards"))

    def test_a_blank_fee_after_the_intro_year_is_not_read_as_zero(self):
        self.assertIsNone(extract_fee("Business travel is more rewarding with 75,000 bonus points $0 intro annual fee for the first year , $ per year thereafter"))


class ThereafterWording(unittest.TestCase):
    def test_intro_year_then_amount_thereafter(self):
        fee = extract_fee("other purchases. 1 $0 intro annual fee for the first year , $95 thereafter. See details below.")
        self.assertEqual((fee.amount, fee.first_year_waived), (95.0, True))

    def test_low_annual_fee_label_before_the_intro_wording(self):
        fee = extract_fee("Low annual fee $0 intro annual fee for the first year and $95 thereafter. Plus, free employee cards")
        self.assertEqual((fee.amount, fee.first_year_waived), (95.0, True))

    def test_a_blank_amount_after_the_intro_year_gives_no_fee(self):
        self.assertIsNone(extract_fee("Low annual fee $0 introductory annual fee for the first year and $ per year thereafter. Plus, free employee cards"))


class AnniversaryAndFootnoteEdgeCases(unittest.TestCase):
    def test_an_anniversary_year_benefit_is_not_a_welcome_offer(self):
        self.assertIsNone(extract_offer("Earn an additional 80 XP (totaling 100 XP) on the account anniversary after you spend at least $15,000 or more on purchases within the anniversary year"))

    def test_a_footnote_number_before_the_spend_requirement_does_not_cut_the_offer(self):
        text = "U.S. Bank Business Altitude Power Visa Signature Card 2 Earn 75,000 bonus points 3 Up to a $750 value 1 after spending $10,000 on the Account Owner's card in the first 120 days of opening your account"
        offer = extract_offer(text)
        self.assertIn("after spending $10,000", offer.text)
        self.assertIn("120 days", offer.text)

    def test_a_footnote_number_after_the_spend_requirement_still_cuts(self):
        offer = extract_offer("Earn 60,000 bonus points after spending $4,000 in the first 3 months 2 $95 Annual Fee 1 Annual Hotel Benefit")
        self.assertEqual(offer.text, "Earn 60,000 bonus points after spending $4,000 in the first 3 months")


class OfferKeepsTheFollowingText(unittest.TestCase):
    TEXT = ("Air Canada Aeroplan Card Earn 75,000 bonus points after you spend $4,000 on purchases in the first 3 months your account is open. "
            "Plus, 40,000 bonus points after you spend $20,000 on purchases in the first 12 months. $195 Annual Fee")

    def test_full_text_includes_a_second_tier_after_the_first_period(self):
        offer = extract_offer(self.TEXT)
        self.assertTrue(offer.text.endswith("your account is open"))
        self.assertIn("Plus, 40,000 bonus points after you spend $20,000", offer.full_text)

    def test_full_text_reads_past_an_asterisk_when_a_second_tier_follows_it(self):
        """Chase Aeroplan: '... account is open. * Plus, 40,000 bonus points after you spend $20,000 ... * AT A GLANCE ...'"""
        text = ("Earn 75,000 bonus points after you spend $4,000 on purchases in the first 3 months your account is open. * "
                "Plus, 40,000 bonus points after you spend $20,000 on purchases in the first 12 months. * AT A GLANCE Enjoy automatic Elite Status")
        offer = extract_offer(text)
        self.assertIn("Plus, 40,000 bonus points after you spend $20,000 on purchases in the first 12 months", offer.full_text)
        self.assertNotIn("AT A GLANCE", offer.full_text)

    def test_full_text_stops_at_a_footnote_asterisk(self):
        offer = extract_offer("Earn 100,000 points after you spend $6,000 in purchases in the first 3 months from account opening * $2,000 value of 100,000 points for travel")
        self.assertNotIn("*", offer.full_text)
        self.assertNotIn("$2,000 value", offer.full_text)


class FromMainHeading(unittest.TestCase):
    def test_starts_at_the_h1_tag_skipping_title_and_navigation(self):
        html = "<head><title>Gold Card</title></head><nav>Gold Card Annual Fee: $0</nav><h1>Gold Card</h1><p>Annual Fee: $325</p>"
        self.assertTrue(from_main_heading(html).startswith("<h1>"))
        self.assertEqual(extract_fee(page_text(from_main_heading(html))).amount, 325.0)

    def test_returns_the_whole_page_when_there_is_no_h1(self):
        html = "<p>no heading</p>"
        self.assertEqual(from_main_heading(html), html)


class MainHeading(unittest.TestCase):
    def test_returns_the_first_h1_text(self):
        self.assertEqual(main_heading("<nav>x</nav><h1>Business  <b>Gold</b> Card</h1><h1>Other</h1>"), "Business Gold Card")

    def test_returns_none_without_an_h1(self):
        self.assertIsNone(main_heading("<p>no heading</p>"))


class ExtractFee(unittest.TestCase):
    def test_simple_fee(self):
        fee = extract_fee("Sapphire Preferred $95 annual fee more text")
        self.assertEqual((fee.amount, fee.first_year_waived), (95.0, False))

    def test_first_year_waived(self):
        fee = extract_fee("Annual Fee: $0 intro annual fee for the first year, then $95")
        self.assertEqual((fee.amount, fee.first_year_waived), (95.0, True))

    def test_introductory_wording_also_counts_as_waived(self):
        fee = extract_fee("Annual Fee: $0 introductory annual fee for the first year, then $150.")
        self.assertEqual((fee.amount, fee.first_year_waived), (150.0, True))

    def test_faq_sentence(self):
        fee = extract_fee("What is it? The annual fee for the American Express Gold Card is $325 for a Basic Card.")
        self.assertEqual(fee.amount, 325.0)

    def test_uppercase_label_and_zero(self):
        self.assertEqual(extract_fee("ANNUAL FEE $0").amount, 0.0)

    def test_fee_applied_to_first_statement_is_not_waived(self):
        fee = extract_fee("ANNUAL FEE $149 applied to first billing statement")
        self.assertEqual((fee.amount, fee.first_year_waived), (149.0, False))

    def test_no_fee_text_returns_none(self):
        self.assertIsNone(extract_fee("Nothing about costs here."))


if __name__ == "__main__":
    unittest.main()
