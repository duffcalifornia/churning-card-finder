import unittest

from cardfinder.check import check_card
from cardfinder.models import Card, IssuerConfig, Page, FetchError

SITE = "https://ex.com"


def html(title, body):
    return f"<html><head><title>{title}</title></head><body><h1>{title}</h1><p>{body}</p></body></html>"


class Fake:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def fetch(self, url):
        self.calls.append(url)
        v = self.pages.get(url)
        if v is None:
            raise FetchError(404, "404")
        if isinstance(v, Exception):
            raise v
        return Page(url, v)


CARD = Card(id="csp", issuer="ex", names=["Chase Sapphire Preferred", "Sapphire Preferred"], urls=[f"{SITE}/sapphire/preferred"])
PLAIN = IssuerConfig(name="ex", sitemaps=[f"{SITE}/sitemap.xml"], listing_pages=[f"{SITE}/cards"], variant_suffixes=["28810/"])
NEAR = IssuerConfig(name="ex", sitemaps=[f"{SITE}/sitemap.xml"], fee_near_name=True)
RENDER = IssuerConfig(name="ex", sitemaps=PLAIN.sitemaps, listing_pages=PLAIN.listing_pages, variant_suffixes=["28810/"], render=True)

GOOD = html("Chase Sapphire Preferred", "Earn 75,000 points after you spend $5,000 in purchases in the first 3 months from account opening. $95 annual fee")


class CheckCard(unittest.TestCase):
    def test_reads_offer_and_fee_from_the_known_url(self):
        r = check_card(CARD, PLAIN, Fake({CARD.urls[0]: GOOD}))
        self.assertEqual(r.status, "found")
        self.assertIn("75,000 points", r.offer.text)
        self.assertEqual(r.fee.amount, 95.0)
        self.assertEqual(r.flags, [])

    def test_a_moved_card_is_found_via_fallback_and_says_so(self):
        new = f"{SITE}/cards/sapphire-preferred"
        f = Fake({f"{SITE}/sitemap.xml": f"<urlset><url><loc>{new}</loc></url></urlset>", new: GOOD})
        r = check_card(CARD, PLAIN, f)
        self.assertEqual((r.status, r.url, r.strategy), ("found_via_fallback", new, "sitemap"))
        self.assertIn("url_changed", r.flags)

    def test_an_unfindable_card_is_reported_with_everything_that_was_tried(self):
        r = check_card(CARD, PLAIN, Fake({}))
        self.assertEqual(r.status, "not_found")
        self.assertTrue(r.attempts)

    def test_cards_marked_not_expected_are_skipped_without_any_requests(self):
        gone = Card(id="x", issuer="ex", names=["Cash Magnet"], urls=[f"{SITE}/x"], expected=False, note="discontinued")
        f = Fake({})
        r = check_card(gone, PLAIN, f)
        self.assertEqual(r.status, "skipped")
        self.assertEqual(f.calls, [])

    def test_raw_html_offer_is_not_trusted_when_the_issuer_needs_rendering(self):
        stale = html("Chase Sapphire Preferred", "Earn 50,000 after you spend $2,000 in purchases. $95 annual fee")
        r = check_card(CARD, RENDER, Fake({CARD.urls[0]: stale}))
        self.assertIsNone(r.offer)
        self.assertIn("needs_render", r.flags)
        self.assertEqual(r.fee.amount, 95.0)

    def test_offer_comes_from_the_rendered_page_when_available(self):
        rendered = Fake({CARD.urls[0]: html("Chase Sapphire Preferred", "AS HIGH AS 175,000 after you spend $12,000 in purchases within the first 6 months of Card Membership.")})
        r = check_card(CARD, RENDER, Fake({CARD.urls[0]: html("Chase Sapphire Preferred", "$95 annual fee")}), rendered=rendered)
        self.assertIn("175,000", r.offer.text)
        self.assertIn("offer_is_ceiling", r.flags)
        self.assertNotIn("needs_render", r.flags)

    def test_a_failed_render_is_flagged_not_fatal(self):
        rendered = Fake({CARD.urls[0]: FetchError(None, "no browser")})
        r = check_card(CARD, RENDER, Fake({CARD.urls[0]: html("Chase Sapphire Preferred", "$95 annual fee")}), rendered=rendered)
        self.assertIsNone(r.offer)
        self.assertIn("render_failed", r.flags)

    def test_a_hidden_offer_is_looked_for_on_variant_pages(self):
        hidden = html("Chase Sapphire Preferred", "Apply and find out your welcome offer. $95 annual fee")
        variant = html("Chase Sapphire Preferred", "AS HIGH AS 100,000 after you spend $8,000 in purchases within the first 6 months of Card Membership.")
        f = Fake({CARD.urls[0]: hidden, CARD.urls[0] + "/28810/": variant})
        r = check_card(CARD, PLAIN, f)
        self.assertIn("100,000", r.offer.text)
        self.assertIn("offer_from_variant", r.flags)
        self.assertEqual(r.status, "found")

    def test_offer_falls_back_to_rendered_when_plain_page_has_none(self):
        bare = html("Chase Sapphire Preferred", "Loading... $95 annual fee")
        rendered = Fake({CARD.urls[0]: html("Chase Sapphire Preferred", "Earn 75,000 points after you spend $5,000 in the first 3 months")})
        r = check_card(CARD, PLAIN, Fake({CARD.urls[0]: bare}), rendered=rendered)
        self.assertIn("75,000", r.offer.text)
        self.assertIn("offer_from_rendered", r.flags)

    def test_flags_a_fee_that_differs_from_the_last_known_fee(self):
        import dataclasses
        card = dataclasses.replace(CARD, expected_fee=0.0)
        r = check_card(card, PLAIN, Fake({CARD.urls[0]: GOOD}))   # page says $95
        self.assertIn("fee_changed", r.flags)

    def test_no_fee_flag_when_the_fee_matches(self):
        import dataclasses
        card = dataclasses.replace(CARD, expected_fee=95.0)
        self.assertNotIn("fee_changed", check_card(card, PLAIN, Fake({CARD.urls[0]: GOOD})).flags)

    def test_no_fee_flag_when_no_last_known_fee_is_recorded(self):
        self.assertNotIn("fee_changed", check_card(CARD, PLAIN, Fake({CARD.urls[0]: GOOD})).flags)

    def test_on_render_issuers_the_fee_comes_from_the_rendered_page(self):
        plain = html("Chase Sapphire Preferred", "nothing useful")
        rendered = Fake({CARD.urls[0]: html("Chase Sapphire Preferred", "Annual Fee: $95 AS HIGH AS 100,000 after you spend $8,000 within the first 6 months")})
        r = check_card(CARD, RENDER, Fake({CARD.urls[0]: plain}), rendered=rendered)
        self.assertEqual(r.fee.amount, 95.0)
        self.assertNotIn("no_fee_found", r.flags)

    def test_a_fee_in_the_navigation_before_the_heading_is_ignored(self):
        page = "<html><head><title>Chase Sapphire Preferred</title></head><body><nav>Other Card Annual Fee: $0</nav><h1>Chase Sapphire Preferred</h1><p>Annual Fee: $95 Earn 75,000 points after you spend $5,000</p></body></html>"
        self.assertEqual(check_card(CARD, PLAIN, Fake({CARD.urls[0]: page})).fee.amount, 95.0)

    def test_a_fee_belonging_to_another_card_is_not_reported(self):
        page = html("Chase Sapphire Preferred", "Compare Chase Sapphire Reserve Annual Fee: $795. Earn 75,000 points after you spend $5,000")
        reserve = Card(id="csr", issuer="ex", names=["Chase Sapphire Reserve"], urls=[f"{SITE}/r"])
        r = check_card(CARD, NEAR, Fake({CARD.urls[0]: page}), siblings=[CARD, reserve])
        self.assertIsNone(r.fee)
        self.assertIn("no_fee_found", r.flags)

    def test_a_sibling_upgrades_fee_is_avoided_using_the_other_cards(self):
        base = Card(id="b", issuer="ex", names=["Hilton Honors Card"], urls=[f"{SITE}/b"])
        surpass = Card(id="s", issuer="ex", names=["Hilton Honors Surpass Card"], urls=[f"{SITE}/s"])
        page = html("Hilton Honors Card", "Hilton Honors Surpass Card Annual Fee: $150. Hilton Honors Card Annual Fee: $0. Earn 70,000 points after you spend $2,000")
        r = check_card(base, NEAR, Fake({base.urls[0]: page}), siblings=[base, surpass])
        self.assertEqual(r.fee.amount, 0.0)

    def test_an_offer_found_by_the_amount_alone_is_flagged_as_possibly_partial(self):
        body = "Earn two certificates valid in the U.S. 48, along with 50,000 Bonus Miles after you spend $10,000 in purchases in the first 6 months."
        r = check_card(CARD, PLAIN, Fake({CARD.urls[0]: html("Chase Sapphire Preferred", body)}))
        self.assertIn("offer_may_be_partial", r.flags)

    def test_an_error_page_is_reported_as_an_error_not_as_no_offer(self):
        err = html("Chase Sapphire Preferred", "Loading Error Sorry, we are unable to load this page at this time. Please try again later.")
        rendered = Fake({CARD.urls[0]: err})
        r = check_card(CARD, RENDER, Fake({CARD.urls[0]: html("Chase Sapphire Preferred", "$95 annual fee")}), rendered=rendered)
        self.assertIn("page_error", r.flags)
        self.assertNotIn("no_offer_found", r.flags)

    def test_a_headline_only_offer_is_flagged_as_possibly_partial(self):
        r = check_card(CARD, PLAIN, Fake({CARD.urls[0]: html("Chase Sapphire Preferred", "25,000 online bonus points offer (a $250 value) and no annual fee")}))
        self.assertIn("offer_may_be_partial", r.flags)

    def test_a_headline_offer_is_completed_from_the_terms_page_it_links_to(self):
        terms = f"{SITE}/terms/?x=1&y=2"
        page = ('<html><head><title>Chase Sapphire Preferred</title></head><body><h1>Chase Sapphire Preferred</h1>'
                '<p>25,000 online bonus points offer (a $250 value) and no annual fee $95 annual fee</p>'
                '<a href="/terms/?x=1&amp;y=2">\u2020 Terms &amp; Conditions for Chase Sapphire Preferred</a></body></html>')
        terms_page = ("<html><body>Bonus Points Offer. You will qualify for 25,000 bonus points if you use your new credit card account to make any combination of "
                      "purchase transactions totaling at least $1,000 (excluding any fees) that post to your account within 90 days of the account open date.</body></html>")
        r = check_card(CARD, PLAIN, Fake({CARD.urls[0]: page, terms: terms_page}))
        self.assertEqual(r.offer.method, "terms_qualify")
        self.assertIn("offer_from_terms_page", r.flags)
        self.assertNotIn("offer_may_be_partial", r.flags)

    def test_the_headline_stays_flagged_partial_when_the_terms_page_cannot_be_read(self):
        page = ('<html><head><title>Chase Sapphire Preferred</title></head><body><h1>Chase Sapphire Preferred</h1>'
                '<p>25,000 online bonus points offer (a $250 value) $95 annual fee</p><a href="/terms/">Terms &amp; Conditions</a></body></html>')
        r = check_card(CARD, PLAIN, Fake({CARD.urls[0]: page}))
        self.assertEqual(r.offer.method, "headline_bonus")
        self.assertIn("offer_may_be_partial", r.flags)

    def test_a_last_known_offer_is_used_when_the_live_page_cannot_be_read(self):
        import dataclasses
        card = dataclasses.replace(CARD, last_known_offer="Earn 125,000 points after you use your new Card to make $5,000 in purchases", last_known_on="2026-09-20")
        err = html("Chase Sapphire Preferred", "Loading Error Sorry, we are unable to load this page at this time. Please try again later.")
        r = check_card(card, RENDER, Fake({CARD.urls[0]: html("Chase Sapphire Preferred", "$95 annual fee")}), rendered=Fake({CARD.urls[0]: err}))
        self.assertIn("125,000", r.offer.text)
        self.assertIn("offer_from_last_known", r.flags)
        self.assertIn("2026-09-20", r.note)

    def test_a_live_offer_always_wins_over_the_last_known_one(self):
        import dataclasses
        card = dataclasses.replace(CARD, last_known_offer="Earn 1 point after you spend $1", last_known_on="2026-09-20")
        r = check_card(card, PLAIN, Fake({CARD.urls[0]: GOOD}))
        self.assertIn("75,000", r.offer.text)
        self.assertNotIn("offer_from_last_known", r.flags)

    def test_an_owner_provided_fee_fills_in_when_the_page_leaves_the_amount_blank(self):
        import dataclasses
        card = dataclasses.replace(CARD, known_fee=95.0, known_fee_first_year_waived=True)
        page = html("Chase Sapphire Preferred", "Low annual fee $0 intro annual fee for the first year and $ per year thereafter. Earn 75,000 points after you spend $5,000")
        r = check_card(card, PLAIN, Fake({CARD.urls[0]: page}))
        self.assertEqual((r.fee.amount, r.fee.first_year_waived), (95.0, True))
        self.assertIn("fee_from_owner", r.flags)
        self.assertNotIn("no_fee_found", r.flags)

    def test_a_fee_read_from_the_page_wins_over_the_owner_provided_one(self):
        import dataclasses
        card = dataclasses.replace(CARD, known_fee=1.0)
        r = check_card(card, PLAIN, Fake({CARD.urls[0]: GOOD}))    # page says $95
        self.assertEqual(r.fee.amount, 95.0)
        self.assertNotIn("fee_from_owner", r.flags)

    def test_no_offer_anywhere_is_flagged(self):
        r = check_card(CARD, PLAIN, Fake({CARD.urls[0]: html("Chase Sapphire Preferred", "$95 annual fee")}))
        self.assertIsNone(r.offer)
        self.assertIn("no_offer_found", r.flags)

    def test_struck_through_offer_and_missing_fee_are_flagged(self):
        body = "Earn 60,000 90,000 Bonus Miles after you spend $6,000 in purchases in your first 6 months of Card Membership."
        r = check_card(CARD, PLAIN, Fake({CARD.urls[0]: html("Chase Sapphire Preferred", body)}))
        self.assertIn("check_struck_through", r.flags)
        self.assertIn("no_fee_found", r.flags)


if __name__ == "__main__":
    unittest.main()
