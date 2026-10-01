import datetime
import unittest

from cardfinder.hotels import HotelSite, block_lines, merge_hotel_offers, read_site, read_sites
from cardfinder.models import FetchError, Page

SITE = HotelSite("demo", "https://hotel.example/cards", {
    "chase-a": ["Demo Premier Credit Card"],
    "chase-b": ["Demo Premier Select Credit Card"],
    "chase-c": ["Demo Credit Card"],
})

# A teaser block (headline only, no spend requirement) before the detailed sections, as the real pages have.
PAGE = """
<main>
 <div><h3>Demo Premier&reg; Credit Card</h3><p>Earn 180K bonus points</p><p>$150 annual fee</p></div>
 <div><h3><span>Demo Premier</span> Select Credit Card</h3><p>Earn 200K bonus points</p></div>
 <section><h2>DEMO PREMIER CREDIT CARD</h2>
  <p>Earn 180,000 bonus points after spending $3,000 in the first 3 months from account opening.*</p>
  <p>Earn 20,000 bonus points after you spend $15,000 on purchases each calendar year</p>
  <p>Offer ends 1/13/27.</p></section>
 <section><h2>Demo Premier Select Credit Card</h2>
  <p>Earn 200,000 bonus points after spending $5,000 in the first 3 months from account opening.*</p>
  <p>Enjoy one Free Night Reward every year.</p></section>
</main>"""


class Fetcher:
    def __init__(self, page=None, error=None):
        self.page, self.error = page, error

    def fetch(self, url):
        if self.error:
            raise self.error
        return Page(url=url, html=self.page)


class BlockLines(unittest.TestCase):
    def test_headings_are_lines_of_their_own_and_inline_tags_do_not_split_them(self):
        lines = block_lines(PAGE)
        self.assertIn("Demo Premier Select Credit Card", lines)
        self.assertIn("Demo Premier® Credit Card", lines)


class ReadSite(unittest.TestCase):
    def read(self, page=PAGE):
        result = read_site(SITE, Fetcher(page))
        return result, {r.card_id: r for r in result.reads}

    def test_a_cards_offer_comes_from_its_own_section_not_a_neighbours_and_not_the_teaser(self):
        result, reads = self.read()
        self.assertEqual(result.status, "ok")
        self.assertEqual(reads["chase-a"].offer.text, "Earn 180,000 bonus points after spending $3,000 in the first 3 months from account opening")
        self.assertEqual(reads["chase-b"].offer.text, "Earn 200,000 bonus points after spending $5,000 in the first 3 months from account opening")

    def test_only_the_offer_and_its_end_date_are_kept_never_the_benefits_that_follow(self):
        _, reads = self.read()
        self.assertTrue(reads["chase-a"].offer.full_text.endswith("Offer ends 1/13/27."))
        self.assertNotIn("20,000", reads["chase-a"].offer.full_text)
        self.assertNotIn("Free Night", reads["chase-b"].offer.full_text)

    def test_a_listed_card_missing_from_the_page_is_not_found_not_guessed(self):
        _, reads = self.read()
        self.assertEqual(reads["chase-c"].status, "not_found")
        self.assertIsNone(reads["chase-c"].offer)

    def test_unreadable_blocked_and_redesigned_pages_are_reported_and_never_raise(self):
        self.assertEqual(read_site(SITE, Fetcher(error=FetchError(403, "HTTP 403"))).status, "unreadable")
        self.assertEqual(read_site(SITE, Fetcher("<html><body>Access Denied. You don't have permission</body></html>")).status, "error_page")
        self.assertEqual(read_site(SITE, Fetcher("<main><h1>Our cards</h1><p>Earn 50,000 points after you spend $1,000</p></main>")).status,
                         "no_cards_recognised")


class ReadSites(unittest.TestCase):
    def test_only_sites_listing_a_wanted_card_are_read(self):
        other = HotelSite("other", "https://other.example", {"chase-z": ["Z"]})
        fetched = []

        class Spy(Fetcher):
            def fetch(self, url):
                fetched.append(url)
                return super().fetch(url)

        results = read_sites([SITE, other], Spy(PAGE), {"chase-a"})
        self.assertEqual([r.site for r in results], ["demo"])
        self.assertEqual(fetched, [SITE.url])


class MergeHotelOffers(unittest.TestCase):
    def test_found_reads_are_dated_and_unread_cards_keep_their_entry(self):
        result = read_site(SITE, Fetcher(PAGE))
        old = {"chase-c": {"seen": "2026-09-01", "site": "demo", "url": "u", "text": "old"}}
        merged = merge_hotel_offers([result], old, "2026-10-01")
        self.assertEqual(merged["chase-a"]["seen"], "2026-10-01")
        self.assertEqual(merged["chase-c"], old["chase-c"])
        self.assertEqual(old, {"chase-c": {"seen": "2026-09-01", "site": "demo", "url": "u", "text": "old"}})


class Configuration(unittest.TestCase):
    def test_every_hotel_card_and_cached_hotel_offer_is_a_tracked_card(self):
        from cardfinder.hotels import HOTEL_SITES
        from cardfinder.registry import CARDS, LAST_KNOWN_HOTEL_OFFERS
        tracked = {c.id for c in CARDS if c.expected}
        for site in HOTEL_SITES:
            for cid in site.cards:
                self.assertIn(cid, tracked, f"{site.name} lists {cid}, which is not a tracked card")
        for cid in LAST_KNOWN_HOTEL_OFFERS:
            self.assertIn(cid, tracked, cid)

    def test_a_card_is_listed_by_one_hotel_page_only(self):
        from collections import Counter
        from cardfinder.hotels import HOTEL_SITES
        counts = Counter(cid for site in HOTEL_SITES for cid in site.cards)
        self.assertEqual([cid for cid, n in counts.items() if n > 1], [])


if __name__ == "__main__":
    unittest.main()
