import unittest

from cardfinder.discovery import find_card
from cardfinder.models import Card, IssuerConfig, Page, FetchError


def page(title, h1=None):
    return f"<html><head><title>{title}</title></head><body><h1>{h1 or title}</h1><p>Earn 75,000 points after you spend $5,000</p></body></html>"


def sitemap(*urls):
    return "<urlset>" + "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>"


def sitemap_index(*urls):
    return "<sitemapindex>" + "".join(f"<sitemap><loc>{u}</loc></sitemap>" for u in urls) + "</sitemapindex>"


def listing(*links):
    return "<html><body>" + "".join(f'<a href="{href}">{text}</a>' for href, text in links) + "</body></html>"


class FakeFetcher:
    """Serves canned pages; anything else is a 404. Records every request."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def fetch(self, url):
        self.calls.append(url)
        value = self.pages.get(url)
        if value is None:
            raise FetchError(404, f"404 {url}")
        if isinstance(value, Exception):
            raise value
        return Page(url=url, html=value)


SITE = "https://ex.com"
RESERVE = Card(id="csr", issuer="ex", names=["Chase Sapphire Reserve", "Sapphire Reserve"], kind="personal",
               urls=[f"{SITE}/rewards/sapphire/reserve"])
CONFIG = IssuerConfig(name="ex", sitemaps=[f"{SITE}/sitemap.xml"], listing_pages=[f"{SITE}/cards"], variant_suffixes=["28810/"])


class FindCard(unittest.TestCase):
    def test_uses_known_url_when_it_still_works(self):
        f = FakeFetcher({RESERVE.urls[0]: page("Chase Sapphire Reserve")})
        result = find_card(RESERVE, CONFIG, f)
        self.assertEqual((result.url, result.strategy), (RESERVE.urls[0], "known_url"))
        self.assertEqual(len(result.attempts), 1)

    def test_falls_back_to_sitemap_when_known_url_is_gone(self):
        new = f"{SITE}/rewards/sapphire-reserve"
        f = FakeFetcher({f"{SITE}/sitemap.xml": sitemap(f"{SITE}/rewards/freedom/unlimited", new),
                         new: page("Chase Sapphire Reserve")})
        result = find_card(RESERVE, CONFIG, f)
        self.assertEqual((result.url, result.strategy), (new, "sitemap"))

    def test_rejects_known_url_that_now_redirects_to_an_index_page(self):
        new = f"{SITE}/rewards/sapphire-reserve"
        f = FakeFetcher({RESERVE.urls[0]: page("Credit Cards from Ex", "All credit cards"),
                         f"{SITE}/sitemap.xml": sitemap(new), new: page("Chase Sapphire Reserve")})
        result = find_card(RESERVE, CONFIG, f)
        self.assertEqual(result.url, new)
        self.assertIn(("known_url", RESERVE.urls[0], "wrong_page"), [(a.strategy, a.url, a.outcome) for a in result.attempts])

    def test_falls_back_to_listing_page_links_when_sitemap_is_unavailable(self):
        new = f"{SITE}/rewards/reserve-card"
        f = FakeFetcher({f"{SITE}/sitemap.xml": FetchError(500, "boom"),
                         f"{SITE}/cards": listing(("/rewards/freedom", "Freedom Unlimited"), ("/rewards/reserve-card", "Chase Sapphire Reserve")),
                         new: page("Chase Sapphire Reserve")})
        result = find_card(RESERVE, CONFIG, f)
        self.assertEqual((result.url, result.strategy), (new, "listing"))

    def test_tries_url_variants_of_the_known_url(self):
        variant = RESERVE.urls[0] + "/28810/"
        f = FakeFetcher({variant: page("Chase Sapphire Reserve")})
        result = find_card(RESERVE, CONFIG, f)
        self.assertEqual((result.url, result.strategy), (variant, "variant"))

    def test_trailing_slash_is_tried_as_a_variant(self):
        card = Card(id="x", issuer="ex", names=["Chase Sapphire Reserve"], kind="personal", urls=[f"{SITE}/rewards/reserve"])
        f = FakeFetcher({f"{SITE}/rewards/reserve/": page("Chase Sapphire Reserve")})
        self.assertEqual(find_card(card, CONFIG, f).strategy, "variant")

    def test_follows_a_sitemap_index_to_child_sitemaps(self):
        new = f"{SITE}/rewards/sapphire-reserve"
        f = FakeFetcher({f"{SITE}/sitemap.xml": sitemap_index(f"{SITE}/cards-sitemap.xml"),
                         f"{SITE}/cards-sitemap.xml": sitemap(new), new: page("Chase Sapphire Reserve")})
        self.assertEqual(find_card(RESERVE, CONFIG, f).url, new)

    def test_picks_the_right_sibling_and_never_accepts_the_wrong_page(self):
        pref, res = f"{SITE}/rewards/sapphire-preferred", f"{SITE}/rewards/sapphire-reserve"
        f = FakeFetcher({f"{SITE}/sitemap.xml": sitemap(pref, res),
                         pref: page("Chase Sapphire Preferred"), res: page("Chase Sapphire Reserve")})
        self.assertEqual(find_card(RESERVE, CONFIG, f).url, res)

    def test_reports_every_strategy_when_the_card_cannot_be_found(self):
        f = FakeFetcher({})
        result = find_card(RESERVE, CONFIG, f)
        self.assertIsNone(result.url)
        self.assertEqual({a.strategy for a in result.attempts}, {"known_url", "variant", "sitemap", "listing"})

    def test_never_fetches_the_same_url_twice(self):
        f = FakeFetcher({f"{SITE}/sitemap.xml": sitemap(RESERVE.urls[0])})
        find_card(RESERVE, CONFIG, f)
        self.assertEqual(len(f.calls), len(set(f.calls)))

    def test_finds_a_card_with_no_known_url_from_a_prefixed_merged_word_slug(self):
        aeroplan = Card(id="aer", issuer="ex", names=["Air Canada Aeroplan Card", "Aeroplan Credit Card"], kind="personal", urls=[])
        url = f"{SITE}/travel-credit-cards/aircanada/aeroplan"
        f = FakeFetcher({f"{SITE}/sitemap.xml": sitemap(f"{SITE}/travel-credit-cards/southwest/plus", url),
                         url: page("Air Canada Aeroplan\u00ae Card | Chase.com")})
        result = find_card(aeroplan, CONFIG, f)
        self.assertEqual((result.url, result.strategy), (url, "sitemap"))

    def test_prefers_the_more_specific_url_when_scores_tie(self):
        """A family landing page (/disney) can share a card's title; the product page is deeper."""
        card = Card(id="dv", issuer="ex", names=["Disney Visa Card"], kind="personal", urls=[])
        landing, product = f"{SITE}/rewards-credit-cards/disney", f"{SITE}/rewards-credit-cards/disney/rewards"
        f = FakeFetcher({f"{SITE}/sitemap.xml": sitemap(landing, product),
                         landing: page("Disney\u00ae Visa\u00ae Card"), product: page("Disney\u00ae Visa\u00ae Card")})
        self.assertEqual(find_card(card, CONFIG, f).url, product)

    def test_prefers_card_related_child_sitemaps_when_an_index_has_many(self):
        """A big index lists dozens of children (videos, locations); the card one must still be reached."""
        new = f"{SITE}/rewards/sapphire-reserve"
        noise = [f"{SITE}/sitemaps/locations-{i}.xml" for i in range(15)]
        cards_map = f"{SITE}/sitemaps/credit-cards-sitemap.xml"
        f = FakeFetcher({f"{SITE}/sitemap.xml": sitemap_index(*noise, cards_map),
                         cards_map: sitemap(new), new: page("Chase Sapphire Reserve")})
        self.assertEqual(find_card(RESERVE, CONFIG, f).url, new)

    def test_resolves_listing_links_against_the_page_it_was_redirected_to(self):
        """Wells Fargo's /credit-cards/ redirects to another host and links to cards with relative paths."""
        target = "https://cards.ex.org/reserve-card/"

        class Redirecting(FakeFetcher):
            def fetch(self, url):
                if url == f"{SITE}/cards":
                    self.calls.append(url)
                    return Page(url="https://cards.ex.org/", html=listing(("/reserve-card/", "Chase Sapphire Reserve")))
                return super().fetch(url)

        f = Redirecting({target: page("Chase Sapphire Reserve")})
        result = find_card(RESERVE, CONFIG, f)
        self.assertEqual((result.url, result.strategy), (target, "listing"))

    def test_limits_how_many_sitemap_candidates_are_fetched(self):
        urls = [f"{SITE}/rewards/sapphire-reserve-{i}" for i in range(20)]
        f = FakeFetcher({f"{SITE}/sitemap.xml": sitemap(*urls)})
        find_card(RESERVE, CONFIG, f)
        candidate_fetches = [c for c in f.calls if "sapphire-reserve-" in c]
        self.assertLessEqual(len(candidate_fetches), 5)


if __name__ == "__main__":
    unittest.main()
