import unittest

from cardfinder.parse import parse_offer


def check(case, text, **expected):
    """Assert the given fields of the parsed offer."""
    parsed = parse_offer(text)
    for field, want in expected.items():
        got = getattr(parsed, field)
        case.assertEqual(got, want, f"{field}: expected {want!r}, got {got!r} for: {text[:90]}")
    return parsed


class PointsOffers(unittest.TestCase):
    def test_chase_points_offer(self):
        check(self, "Earn 75,000 points after you spend $5,000 in purchases in the first 3 months from account opening",
              kind="standard", points=75000, cash_back=None, min_spend=5000, window_months=3, ceiling=False)

    def test_miles_and_pqp_ignores_pqp(self):
        p = check(self, "Earn 60,000 bonus miles + 500 PQP after you spend $4,000 on purchases in the first 3 months your account is open",
                  points=60000, min_spend=4000, window_months=3)
        self.assertEqual(p.cash_back, None)

    def test_avios(self):
        check(self, "Earn 75,000 Avios after you spend $5,000 on purchases within the first 3 months of account opening", points=75000, min_spend=5000, window_months=3)

    def test_spending_wording_and_days_window(self):
        check(self, "Earn 10,000 bonus points after spending $1,000 on purchases in the first 90 days", points=10000, min_spend=1000, window_months=3)

    def test_once_you_spend(self):
        check(self, "Earn 75,000 bonus miles once you spend $4,000 on purchases within the first 3 months from account opening", points=75000, min_spend=4000, window_months=3)

    def test_when_you_spend(self):
        check(self, "Earn 60,000 bonus points when you spend $4,000 in purchases in the first 3 months", points=60000, min_spend=4000, window_months=3)

    def test_after_an_amount_in_purchases(self):
        check(self, "Earn 125,000 AAdvantage bonus miles after $15,000 in purchases in the first 5 months", points=125000, min_spend=15000, window_months=5)

    def test_within_the_first_months_of_account_opening(self):
        check(self, "Earn 65,000 AAdvantage bonus miles For your business after $4,000 in purchases within the first 4 months of account opening",
              points=65000, min_spend=4000, window_months=4)

    def test_brand_named_points(self):
        check(self, "Earn 70,000 bonus Skywards Miles after spending $3,000 on purchases in the first 90 days", points=70000, min_spend=3000, window_months=3)
        check(self, "Earn 30,000 bonus BreezePoints that is a $300 value, plus Breezy benefits, after spending $1,000 on purchase within the first 90 days",
              points=30000, cash_back=None, min_spend=1000)

    def test_just_spend_wording(self):
        check(self, "Earn 20,000 bonus points. 1 Just spend $1,000 in Net Purchases in the first 90 days", points=20000, min_spend=1000, window_months=3)

    def test_to_qualify_spend_and_a_companion_fare_is_not_cash(self):
        p = check(self, "Get 50,000 bonus points and a $99 Companion Fare (plus taxes and fees from $23) with this offer. To qualify, spend $1,500 or more on purchases within the first 90 days",
                  points=50000, cash_back=None, min_spend=1500, window_months=3)
        self.assertTrue(any("companion" in n.lower() for n in p.notes))

    def test_after_you_make_or_more(self):
        check(self, "Get 70,000 bonus points and a $99 Companion Fare after you make $4,000 or more in purchases in the first 90 days", points=70000, min_spend=4000, window_months=3)

    def test_terms_page_wording(self):
        check(self, "You will qualify for 25,000 bonus points if you use your new credit card account to make any combination of purchase transactions totaling at least $1,000 (excluding any fees) that post to your account within 90 days",
              points=25000, min_spend=1000, window_months=3)

    def test_amex_card_membership_wording(self):
        check(self, "Earn 125,000 Marriott Bonvoy Bonus Points Plus A $150 Statement Credit after you use your new Card to make $5,000 in purchases within the first 6 months of Card Membership",
              points=125000, cash_back=150, min_spend=5000, window_months=6)


class CashOffers(unittest.TestCase):
    def test_cash_bonus(self):
        check(self, "Earn a $200 bonus after you spend $500 on purchases in the first 3 months from account opening", cash_back=200, points=None, min_spend=500, window_months=3)

    def test_cash_back(self):
        check(self, "Earn $750 cash back after you spend $6,000 on purchases in the first 3 months after account opening", cash_back=750, min_spend=6000, window_months=3)

    def test_cash_rewards_bonus_without_earn(self):
        check(self, "$200 cash rewards bonus after making at least $1,000 in purchases in the first 90 days of your account opening", cash_back=200, min_spend=1000, window_months=3)

    def test_a_repeated_amount_is_counted_once(self):
        p = check(self, "Get a $200 bonus For a limited time, earn a $200 rewards bonus after you spend $1,000 in eligible purchases within the first 90 days", cash_back=200, min_spend=1000)
        self.assertTrue(any("merged" in n for n in p.notes))

    def test_gift_card_and_statement_credit_are_summed_at_face_value(self):
        check(self, "Get a $100 Disney Gift Card eGift to use today upon approval + earn a $50 statement credit after you spend $500 on purchases in the first 3 months from account opening",
              cash_back=150, min_spend=500, window_months=3)

    def test_gift_card_on_approval_has_no_spend(self):
        check(self, "get a $150 Amazon Gift Card instantly loaded into your Amazon account's Gift Card Balance on approval of your credit card application",
              cash_back=150, min_spend=None, window_months=None)

    def test_cash_bonus_plus_a_travel_credit(self):
        check(self, "Earn a $1,000 cash bonus and a $250 travel credit when you spend $10,000 in the first 3 months", cash_back=1250, min_spend=10000, window_months=3)

    def test_one_time_footnote_wording(self):
        check(self, "One-time $750 cash back will be awarded if eligible Net Purchases totaling $6,000 or more are made to the Account Owner's Card within 180 days of account opening",
              cash_back=750, min_spend=6000, window_months=6)

    def test_a_value_statement_is_not_cash(self):
        check(self, "Earn 30,000 Bonus Points equal to $300 off a future trip when you spend $1,000 in the first 90 days", cash_back=None, points=30000)


class StatementCreditsMustBeGeneral(unittest.TestCase):
    """Owner rule (2026-09-20): a general statement credit counts; one tied to a specific type of spending does not."""

    def test_a_general_statement_credit_counts(self):
        check(self, "Earn 50,000 points and a $250 statement credit after you spend $3,000 on purchases in the first 3 months", points=50000, cash_back=250, min_spend=3000)

    def test_a_credit_earned_by_spending_on_airfare_does_not_count(self):
        p = check(self, "Earn 60,000 bonus points after you spend $4,000 in purchases in the first 3 months, plus a $100 statement credit after you spend $500 on airfare",
                  points=60000, cash_back=None, min_spend=4000, window_months=3, ceiling=False)
        self.assertTrue(any("specific" in n for n in p.notes))

    def test_an_airline_purchases_credit_does_not_count_and_is_not_a_ceiling(self):
        p = check(self, "Earn 3 Free Night Awards after spending $3,000 on eligible purchases within 3 months. Get up to $100 in statement credits after spending $500 on eligible airline purchases",
                  cash_back=None, free_night_awards=3, min_spend=3000, ceiling=False)
        self.assertTrue(any("specific" in n for n in p.notes))

    def test_a_credit_for_dining_or_a_named_merchant_does_not_count(self):
        check(self, "Earn 40,000 points after you spend $2,000 in purchases in the first 3 months plus a $50 statement credit after you spend $200 at restaurants", cash_back=None, points=40000)
        check(self, "Earn 40,000 points after you spend $2,000 in purchases in the first 3 months plus a $50 statement credit after you spend $200 at Amazon", cash_back=None, points=40000)

    def test_a_credit_for_general_purchases_still_counts(self):
        check(self, "Get a $100 Disney Gift Card eGift to use today upon approval + earn a $50 statement credit after you spend $500 on purchases in the first 3 months",
              cash_back=150)
        check(self, "Earn 125,000 Bonus Points Plus A $150 Statement Credit after you use your new Card to make $5,000 in purchases within the first 6 months", cash_back=150)
        check(self, "Earn a $250 Statement Credit after you spend $3,000 in purchases on your Card in your first 3 months", cash_back=250)
        check(self, "Earn a $1,000 cash bonus and a $250 travel credit when you spend $10,000 in the first 3 months", cash_back=1250)

    def test_a_credit_on_eligible_or_qualifying_purchases_counts(self):
        check(self, "Earn a $100 statement credit after you spend $500 on eligible purchases in the first 3 months", cash_back=100)
        check(self, "Earn a $100 statement credit after you spend $500 on qualifying purchases in the first 3 months", cash_back=100)

    def test_a_cash_bonus_is_not_affected_by_this_rule(self):
        check(self, "Earn a $200 cash bonus after you spend $500 on airfare in the first 3 months", cash_back=200)


class NotBonusAmounts(unittest.TestCase):
    def test_a_redemption_value_is_not_a_bonus(self):
        check(self, "Earn 50,000 online bonus points after you make at least $5,000 in purchases in the first 90 days of your account opening, which can be redeemed for a $500 statement credit toward travel",
              points=50000, cash_back=None, min_spend=5000)

    def test_a_fee_is_not_a_credit(self):
        check(self, "Earn 60,000 bonus points when you spend $4,000 in purchases in the first 3 months 1 - that is $600 toward your next trip $95 Annual Fee Important Credit terms",
              points=60000, cash_back=None, min_spend=4000)

    def test_a_zero_dollar_amount_is_never_cash(self):
        check(self, "Earn a $100 cash rewards bonus when you spend $500 in purchases in the first 3 months 1 Plus, earn unlimited 2% cash rewards on purchases 2 $0 Annual Fee",
              cash_back=100)


class FreeNights(unittest.TestCase):
    def test_free_night_awards(self):
        check(self, "Earn 3 Free Night Awards after spending $3,000 on eligible purchases within 3 months of account opening", free_night_awards=3, points=None, min_spend=3000, window_months=3)

    def test_points_plus_a_free_night(self):
        check(self, "Earn 70,000 Hilton Honors Bonus Points + A Free Night Reward after you spend $2,000 in purchases in the first 6 months", points=70000, free_night_awards=1, min_spend=2000, window_months=6)

    def test_points_and_1_free_night_award(self):
        check(self, "Earn 100,000 Marriott Bonvoy Bonus Points and 1 Free Night Award after you spend $8,000 in purchases within the first 6 months", points=100000, free_night_awards=1)


class Flags(unittest.TestCase):
    def test_as_high_as_is_a_ceiling(self):
        check(self, "AS HIGH AS 175,000 Membership Rewards points after you spend $12,000 in purchases on your new Card within the first 6 months of Card Membership",
              points=175000, ceiling=True, min_spend=12000, window_months=6)

    def test_up_to_dollars_is_a_ceiling(self):
        check(self, "Earn up to $600 in rewards 5 when you spend $6,000 in eligible purchases within the first 90 days", cash_back=600, ceiling=True, min_spend=6000)

    def test_a_struck_through_pair_uses_the_second_number_and_asks_for_review(self):
        for text in ("Earn 150,000 strike through 200,000 points after you spend $30,000 on purchases in your first 6 months from account opening",
                     "Earn 60,000 90,000 Bonus Miles after you spend $6,000 in purchases on your new Card in your first 6 months of Card Membership",
                     "EARN 40,000 old bonus 60,000 new bonus BONUS POINTS when you spend $1,000 in purchases in the first 3 months"):
            p = parse_offer(text)
            self.assertIn(p.points, (200000, 90000, 60000))
            self.assertTrue(any("struck" in n for n in p.notes), text)
        self.assertEqual(parse_offer("Earn 150,000 strike through 200,000 points after you spend $30,000 on purchases in your first 6 months").points, 200000)

    def test_an_authorized_user_bonus_is_excluded(self):
        p = check(self, "Earn 50,000 bonus miles after you spend $3,000 on purchases in the first 3 months, plus 10,000 bonus miles after you add an authorized user in the first 3 months",
                  points=50000, min_spend=3000)
        self.assertTrue(any("authorized" in n for n in p.notes))


class TieredOffers(unittest.TestCase):
    def test_hyatt_style_counts_only_the_first_part(self):
        p = check(self, "Earn up to 60,000 Bonus Points 30,000 Bonus Points after you spend $3,000 on purchases in your first 3 months of account opening",
                  points=30000, min_spend=3000, window_months=3, additional_tiers=[])
        self.assertTrue(any("first part" in n for n in p.notes))

    def test_aeroplan_style_second_tier_is_kept_separately(self):
        p = parse_offer("Earn 75,000 bonus points after you spend $4,000 on purchases in the first 3 months your account is open. "
                        "Plus, 40,000 bonus points after you spend $20,000 on purchases in the first 12 months")
        self.assertEqual((p.points, p.min_spend, p.window_months), (75000, 4000, 3))
        self.assertEqual(len(p.additional_tiers), 1)
        t = p.additional_tiers[0]
        self.assertEqual((t.points, t.min_spend, t.window_months), (40000, 20000, 12))

    def test_wyndham_two_part_offer(self):
        p = parse_offer("Earn 45,000 bonus points after spending $1,000 on qualifying purchases in the first 90 days and also earn 55,000 bonus points after spending $500 at Hotels by Wyndham in the first 90 days")
        self.assertEqual((p.points, p.min_spend, p.window_months), (45000, 1000, 3))
        self.assertEqual([(t.points, t.min_spend) for t in p.additional_tiers], [(55000, 500)])

    def test_total_spend_style_second_tier(self):
        # the spend clause comes before the earn amount here, and "a total of" marks it as cumulative rather than additional
        p = parse_offer("Earn 30,000 bonus points after you spend $3,000 on purchases in the first 3 months. "
                        "If you spend a total of $10,000 within the first 6 months, earn an additional 20,000 bonus points")
        self.assertEqual((p.points, p.min_spend, p.window_months), (30000, 3000, 3))
        self.assertEqual(len(p.additional_tiers), 1)
        t = p.additional_tiers[0]
        self.assertEqual((t.points, t.min_spend, t.window_months), (20000, 10000, 6))


class NoFixedAmount(unittest.TestCase):
    def test_first_year_match(self):
        p = check(self, "match all the cash back you earn at the end of your first year after you open your new Discover it Cash Back Card", kind="match", points=None, cash_back=None)
        self.assertTrue(any("match" in n for n in p.notes))

    def test_unparseable_text_is_marked_for_review(self):
        p = parse_offer("Earn an additional 80 XP (totaling 100 XP) on the account anniversary")
        self.assertEqual(p.kind, "unparsed")
        self.assertTrue(p.notes)


class Notes(unittest.TestCase):
    def test_missing_spend_and_window_are_noted_not_guessed(self):
        p = parse_offer("25,000 online bonus points offer")
        self.assertEqual((p.points, p.min_spend, p.window_months), (25000, None, None))
        self.assertTrue(any("spend" in n for n in p.notes))


if __name__ == "__main__":
    unittest.main()
