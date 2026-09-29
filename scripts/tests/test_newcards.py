import unittest

from cardfinder import newcards as nc
from cardfinder.models import Card, FetchError, IssuerConfig, Page

KNOWN = [
    "https://www.usbank.com/business-banking/business-credit-cards/business-shield-credit-card.html",
    "https://www.usbank.com/business-banking/business-credit-cards/business-altitude-connect-credit-card.html",
    "https://www.usbank.com/credit-cards/altitude-go-visa-signature-credit-card.html",
    "https://www.usbank.com/credit-cards/cash-plus-visa-signature-credit-card.html",
]


def card_html(title, h1, extra=""):
    return (f"<html><head><title>{title}</title></head><body><h1>{h1}</h1>"
            f"<p>Earn a $200 cash rewards bonus after you spend $500 in purchases in the first 3 months. $95 Annual Fee</p>{extra}</body></html>")


class FakeFetcher:
    def __init__(self, pages):
        self.pages, self.fetched = pages, []

    def fetch(self, url):
        self.fetched.append(url)
        if url not in self.pages:
            raise FetchError(404)
        return Page(url, self.pages[url])


class Urls(unittest.TestCase):
    def test_normalize_drops_query_fragment_and_trailing_slash(self):
        self.assertEqual(nc.normalize_url("HTTPS://Example.com/a/b/?x=1#top"), "https://example.com/a/b")

    def test_slug_drops_card_words_and_extension(self):
        self.assertEqual(nc.slug_of("https://x.com/business-credit-cards/business-essentials-plus-credit-card.html"), "business-essentials-plus")

    def test_a_new_link_in_a_known_folder_is_a_candidate(self):
        new = "https://www.usbank.com/business-banking/business-credit-cards/business-essentials-credit-card.html"
        self.assertEqual(nc.candidate_urls([new], KNOWN), [new])

    def test_known_cards_and_their_query_string_variants_are_not(self):
        self.assertEqual(nc.candidate_urls([KNOWN[0], KNOWN[0] + "?src=1", KNOWN[0].replace("https", "HTTPS") + "/"], KNOWN), [])

    def test_a_different_folder_is_not_a_candidate(self):
        self.assertEqual(nc.candidate_urls(["https://www.usbank.com/business-banking/business-resource-center/some-new-card.html"], KNOWN), [])

    def test_a_different_host_is_not_a_candidate(self):
        self.assertEqual(nc.candidate_urls(["https://evil.example/credit-cards/cash-back-card.html"], KNOWN), [])

    def test_a_different_style_is_not_a_candidate(self):
        self.assertEqual(nc.candidate_urls(["https://www.usbank.com/credit-cards/some-new-card"], KNOWN), [])

    def test_junk_words_anywhere_in_the_path_rule_a_link_out(self):
        base = "https://www.usbank.com/credit-cards/"
        for slug in ("compare-cards.html", "faq-cards.html", "apply-now-card.html"):
            self.assertEqual(nc.candidate_urls([base + slug], KNOWN), [], slug)

    def test_about_us_news_is_out_even_with_a_bland_last_segment(self):
        known = ["https://b.example/banking/cards/a-card/", "https://b.example/banking/cards/b-card/"]
        self.assertEqual(nc.candidate_urls(["https://b.example/banking/about-us/news-and-views/insights/xyz-report-card"], known), [])

    def test_skip_urls_and_duplicates_are_dropped(self):
        new = "https://www.usbank.com/credit-cards/new-card-visa-credit-card.html"
        self.assertEqual(nc.candidate_urls([new, new + "?a=1"], KNOWN, skip_urls=[new]), [])
        self.assertEqual(nc.candidate_urls([new, new + "?a=1"], KNOWN), [new])

    def test_a_card_alone_in_its_folder_is_matched_by_top_folder_and_depth(self):
        known = ["https://c.example/travel-credit-cards/united/explorer", "https://c.example/travel-credit-cards/marriott/bold"]
        self.assertEqual(nc.candidate_urls(["https://c.example/travel-credit-cards/hyatt/newcard"], known),
                         ["https://c.example/travel-credit-cards/hyatt/newcard"])

    def test_one_level_addresses_must_name_a_card(self):
        known = ["https://w.example/active-cash-credit-card/"]
        self.assertEqual(nc.candidate_urls(["https://w.example/contact-us-here", "https://w.example/reflect-visa-credit-card"], known),
                         ["https://w.example/reflect-visa-credit-card"])


class Judging(unittest.TestCase):
    def test_singular_card_headings_are_card_pages(self):
        self.assertTrue(nc.is_card_page("Chase Freedom Rise Credit Card", "Chase Freedom Rise Credit Card"))
        self.assertTrue(nc.is_card_page("", "Business Essentials Visa Card"))

    def test_category_and_offer_pages_are_not(self):
        for h1, title in (("Cash back credit cards", "Cash Back Credit Cards"), ("Avios Credit Cards", "Avios"),
                          ("Discover it Balance Transfer Offer", "Balance Transfer Credit Card Offers"),
                          ("Chase Freedom Credit Cards", "Compare Chase Freedom Credit Cards"), ("Some article", "Some article")):
            self.assertFalse(nc.is_card_page(h1, title), h1)

    def test_a_business_essentials_plus_page_is_not_the_plain_essentials_card(self):
        known = [Card(id="usbank-business-essentials", issuer="usbank", names=["Business Essentials Visa Card", "Business Essentials"])]
        self.assertFalse(nc.is_known_card(["U.S. Bank Business Essentials Plus Visa Signature Card", "Business Essentials Plus Visa Card"], known))

    def test_the_same_card_under_another_url_is_known(self):
        known = [Card(id="chase-freedom-rise", issuer="chase", names=["Chase Freedom Rise", "Freedom Rise"])]
        self.assertTrue(nc.is_known_card(["Chase Freedom Rise Credit Card"], known))

    def test_name_prefers_a_singular_card_heading_over_a_generic_title(self):
        html = card_html("Cash Back Credit Card - Active Cash Visa Card Wells Fargo", "Active Cash &reg; Credit Card")
        self.assertEqual(nc.page_name(html), "Active Cash Credit Card")

    def test_id_is_unique(self):
        self.assertEqual(nc.propose_id("usbank", "https://x/a/business-essentials-credit-card.html", {"usbank-business-essentials"}),
                         "usbank-business-essentials-2")


CFG = IssuerConfig(name="usbank", listing_pages=["https://www.usbank.com/credit-cards/"])
KNOWN_CARDS = [Card(id="usbank-business-shield", issuer="usbank", names=["Business Shield Visa Card"], kind="business", urls=[KNOWN[0]])]


class Evaluate(unittest.TestCase):
    URL = "https://www.usbank.com/business-banking/business-credit-cards/business-new-credit-card.html"

    def evaluate(self, html, cards=KNOWN_CARDS):
        return nc.evaluate_candidate(self.URL, "usbank", CFG, cards, FakeFetcher({self.URL: html}), None, {c.id for c in cards})

    def test_a_real_untracked_card_becomes_a_proposal(self):
        verdict, p = self.evaluate(card_html("Business New Visa Card | U.S. Bank", "Business New Visa Card"))
        self.assertEqual(verdict, "candidate")
        self.assertEqual((p["id"], p["name"], p["kind"], p["issuer"]), ("usbank-business-new", "Business New Visa Card", "business", "usbank"))
        self.assertEqual(p["fee"]["amount"], 95.0)
        self.assertEqual(p["reads_as"]["cashBack"], 200.0)

    def test_a_category_page_is_rejected(self):
        self.assertEqual(self.evaluate(card_html("Best Business Cards | U.S. Bank", "Business credit cards"))[0], "reject")

    def test_a_card_we_already_have_is_rejected(self):
        self.assertEqual(self.evaluate(card_html("Business Shield Visa Card | U.S. Bank", "Business Shield Visa Card"))[0], "reject")

    def test_a_card_page_with_no_annual_fee_is_rejected(self):
        html = "<html><head><title>Business New Visa Card</title></head><body><h1>Business New Visa Card</h1><p>Earn a $200 cash rewards bonus after you spend $500 in purchases in the first 3 months</p></body></html>"
        self.assertEqual(self.evaluate(html)[0], "reject")

    def test_a_failed_fetch_or_an_error_page_teaches_nothing(self):
        self.assertEqual(nc.evaluate_candidate(self.URL, "usbank", CFG, KNOWN_CARDS, FakeFetcher({}), None, set())[0], "unsure")
        self.assertEqual(self.evaluate("<html><body>Access denied</body></html>")[0], "unsure")


class FindNewCards(unittest.TestCase):
    LISTING = "https://www.usbank.com/credit-cards/"
    NEW = "https://www.usbank.com/business-banking/business-credit-cards/business-new-credit-card.html"
    JUNK = "https://www.usbank.com/business-banking/business-credit-cards/business-perks-overview.html"

    def fetcher(self):
        listing = "".join(f'<a href="{u}">x</a>' for u in (KNOWN[0], self.NEW, self.JUNK))
        return FakeFetcher({self.LISTING: listing,
                            self.NEW: card_html("Business New Visa Card | U.S. Bank", "Business New Visa Card"),
                            self.JUNK: "<html><head><title>Tools</title></head><body><h1>Tools</h1></body></html>"})

    def run_it(self, ignored=(), rejects=None):
        cfg = IssuerConfig(name="usbank", listing_pages=[self.LISTING])
        return nc.find_new_cards({"usbank": cfg}, KNOWN_CARDS, self.fetcher(), None, set(ignored), rejects or {}, "2026-09-29", log=lambda m: None)

    def test_finds_the_new_card_and_rejects_the_junk_page(self):
        proposals, rejects = self.run_it()
        self.assertEqual([p["id"] for p in proposals], ["usbank-business-new"])
        self.assertEqual(rejects, {self.JUNK: "2026-09-29"})

    def test_an_ignored_page_is_never_looked_at(self):
        proposals, rejects = self.run_it(ignored=[self.NEW])
        self.assertEqual(proposals, [])

    def test_a_recent_reject_is_skipped_but_an_old_one_is_looked_at_again(self):
        f = self.fetcher()
        cfg = IssuerConfig(name="usbank", listing_pages=[self.LISTING])
        nc.find_new_cards({"usbank": cfg}, KNOWN_CARDS, f, None, set(), {self.JUNK: "2026-09-20"}, "2026-09-29", log=lambda m: None)
        self.assertNotIn(self.JUNK, f.fetched)
        f = self.fetcher()
        nc.find_new_cards({"usbank": cfg}, KNOWN_CARDS, f, None, set(), {self.JUNK: "2026-06-01"}, "2026-09-29", log=lambda m: None)
        self.assertIn(self.JUNK, f.fetched)

    def test_an_issuer_whose_listing_cannot_be_read_yields_nothing_and_no_error(self):
        cfg = IssuerConfig(name="usbank", listing_pages=["https://www.usbank.com/nope/"])
        self.assertEqual(nc.find_new_cards({"usbank": cfg}, KNOWN_CARDS, FakeFetcher({}), None, set(), {}, "2026-09-29", log=lambda m: None), ([], {}))


class IssueText(unittest.TestCase):
    P = {"id": "usbank-business-new", "name": "Business New Visa Card", "issuer": "usbank", "kind": "business",
         "url": "https://www.usbank.com/x.html", "offer": {"text": "Earn $200 -- fast"}, "fee": {"amount": 95.0, "firstYearWaived": False},
         "reads_as": {"points": None, "cashBack": 200.0, "freeNightAwards": 0, "minSpend": 500.0, "windowMonths": 3}}

    def test_proposal_round_trips_through_the_hidden_marker_even_with_double_dashes(self):
        self.assertEqual(nc.decode_proposal(nc.issue_body(self.P, ["cash", "ultimate-rewards"])), self.P)

    def test_body_says_what_was_read_and_how_to_answer(self):
        body = nc.issue_body(self.P, ["cash", "ultimate-rewards"])
        for text in ("Business New Visa Card", "$200 cash back", "$95", "/track", "/ignore", "currency=", "`ultimate-rewards`", "must give the currency", "mobile app"):
            self.assertIn(text, body)

    def test_unreadable_markers_decode_to_nothing(self):
        for body in (None, "no marker", "<!-- new-card: !!!not-base64 -->", "<!-- new-card: bm90IGpzb24= -->"):
            self.assertIsNone(nc.decode_proposal(body))

    def test_title(self):
        self.assertEqual(nc.issue_title("X"), "New card found: X")


class PlanReports(unittest.TestCase):
    def cand(self, n):
        return {"id": f"usbank-c{n}", "name": f"C{n}", "issuer": "usbank", "kind": "personal", "url": f"https://www.usbank.com/c{n}.html"}

    def test_a_candidate_with_an_open_issue_is_not_raised_again(self):
        open_issue = {"number": 1, "state": "OPEN", "body": f"<!-- new-card: {nc.encode_proposal(self.cand(1))} -->"}
        doc = {"candidates": [self.cand(1), self.cand(2)]}
        self.assertEqual([c["id"] for c in nc.plan_new_reports(doc, [open_issue])], ["usbank-c2"])

    def test_at_most_a_handful_are_opened_per_run(self):
        doc = {"candidates": [self.cand(n) for n in range(9)]}
        self.assertEqual(len(nc.plan_new_reports(doc, [])), nc.MAX_NEW_ISSUES_PER_RUN)


if __name__ == "__main__":
    unittest.main()
