import json
import unittest

from cardfinder.check import CardResult
from cardfinder.cli import select_cards, exit_code, format_report, to_json, run, split_paused
from cardfinder.discovery import Attempt
from cardfinder.extract import Fee, Offer
from cardfinder.models import Card, IssuerConfig, Page, FetchError


def card(cid, issuer="chase", name="Sapphire Preferred", expected=True):
    return Card(id=cid, issuer=issuer, names=[name], urls=["https://x"], expected=expected, note="" if expected else "gone")


CARDS = [card("a", "chase", "Chase Sapphire Preferred"), card("b", "chase", "Chase Freedom Flex"), card("c", "amex", "Platinum Card")]


class SelectCards(unittest.TestCase):
    def test_filters_by_issuer(self):
        self.assertEqual([c.id for c in select_cards(CARDS, "amex", None)], ["c"])

    def test_all_returns_everything(self):
        self.assertEqual(len(select_cards(CARDS, "all", None)), 3)

    def test_filters_by_name_text(self):
        self.assertEqual([c.id for c in select_cards(CARDS, "all", "freedom")], ["b"])


def result(status, **kw):
    return CardResult("id", "Some Card", status, **kw)


class Reporting(unittest.TestCase):
    def test_exit_code_is_zero_when_everything_is_found_or_skipped(self):
        self.assertEqual(exit_code([result("found"), result("found_via_fallback"), result("skipped")]), 0)

    def test_exit_code_is_two_when_a_card_could_not_be_found(self):
        self.assertEqual(exit_code([result("found"), result("not_found")]), 2)

    def test_report_lists_what_was_tried_for_a_missing_card(self):
        r = result("not_found", attempts=[Attempt("known_url", "https://x/a", "http_404"), Attempt("sitemap", "https://x/sitemap.xml", "http_500")])
        text = format_report([r])
        self.assertIn("NOT FOUND", text)
        self.assertIn("known_url", text)
        self.assertIn("http_404", text)
        self.assertIn("sitemap", text)

    def test_report_shows_offer_fee_and_flags(self):
        r = result("found", url="https://x", strategy="known_url",
                   offer=Offer("Earn 75,000 points after you spend $5,000", "after_spend"), fee=Fee("$95 annual fee", 95.0), flags=["offer_is_ceiling"])
        text = format_report([r])
        self.assertIn("75,000", text)
        self.assertIn("$95", text)
        self.assertIn("offer_is_ceiling", text)

    def test_report_ends_with_a_summary_of_counts(self):
        text = format_report([result("found"), result("not_found"), result("skipped")])
        self.assertIn("1 found", text)
        self.assertIn("1 not found", text)
        self.assertIn("1 skipped", text)

    def test_json_output_is_machine_readable(self):
        r = result("found", url="https://x", offer=Offer("Earn 1 after you spend $1", "after_spend", ceiling=True), fee=Fee("$0", 0.0, first_year_waived=True), flags=["f"])
        data = json.loads(to_json([r]))
        self.assertEqual(data[0]["status"], "found")
        self.assertTrue(data[0]["offer"]["ceiling"])
        self.assertTrue(data[0]["fee"]["first_year_waived"])
        self.assertEqual(data[0]["flags"], ["f"])


class PausedIssuers(unittest.TestCase):
    ISSUERS = {"chase": IssuerConfig(name="chase"), "amex": IssuerConfig(name="amex", paused="Blocked our IP address; revisit later.")}

    def test_paused_issuers_are_split_out_with_their_reason(self):
        active, paused = split_paused(CARDS, self.ISSUERS)
        self.assertEqual([c.id for c in active], ["a", "b"])
        self.assertEqual(paused, {"amex": "Blocked our IP address; revisit later."})

    def test_nothing_is_paused_by_default(self):
        active, paused = split_paused(CARDS, {"chase": IssuerConfig(name="chase"), "amex": IssuerConfig(name="amex")})
        self.assertEqual(len(active), 3)
        self.assertEqual(paused, {})

    def test_a_paused_issuer_is_only_reported_when_it_has_selected_cards(self):
        active, paused = split_paused([c for c in CARDS if c.issuer == "chase"], self.ISSUERS)
        self.assertEqual(paused, {})


class CountingFetcher:
    def __init__(self, html):
        self.html, self.calls = html, []

    def fetch(self, url):
        self.calls.append(url)
        return Page(url, self.html)


ERROR_HTML = ("<html><head><title>Card {n}</title></head><body><h1>Card {n}</h1>"
              "<p>Loading Error Sorry, we are unable to load this page at this time. Please try again later.</p></body></html>")


class DuplicatePages(unittest.TestCase):
    def test_two_cards_that_resolve_to_the_same_page_are_both_flagged(self):
        issuers = {"ex": IssuerConfig(name="ex")}
        a = Card(id="a", issuer="ex", names=["Business Cash Rewards"], kind="business", urls=["https://ex.com/biz-cash"])
        b = Card(id="b", issuer="ex", names=["Business Cash Rewards"], kind="business", urls=["https://ex.com/biz-cash"])
        c = Card(id="c", issuer="ex", names=["Other Card"], urls=["https://ex.com/other"])
        pages = {"https://ex.com/biz-cash": "<html><head><title>Business Cash Rewards Business Card</title></head><body><h1>Business Cash Rewards</h1></body></html>",
                 "https://ex.com/other": "<html><head><title>Other Card</title></head><body><h1>Other Card</h1></body></html>"}

        class Fetch:
            def fetch(self, url):
                if url not in pages:
                    raise FetchError(404, "404")
                return Page(url, pages[url])

        results = {r.card_id: r for r in run([a, b, c], issuers, Fetch())}
        self.assertIn("same_page_as_another_card", results["a"].flags)
        self.assertIn("same_page_as_another_card", results["b"].flags)
        self.assertNotIn("same_page_as_another_card", results["c"].flags)


class CircuitBreaker(unittest.TestCase):
    def cards(self, n):
        return [Card(id=f"c{i}", issuer="ex", names=[f"Card {i}"], urls=[f"https://ex.com/{i}"]) for i in range(n)]

    def test_stops_requesting_from_an_issuer_after_repeated_error_pages(self):
        issuers = {"ex": IssuerConfig(name="ex", render=True)}
        cards = self.cards(8)

        class ErrorPages:
            calls = []

            def fetch(self, url):
                self.calls.append(url)
                n = url.rsplit("/", 1)[1]
                return Page(url, ERROR_HTML.format(n=n))

        http, rendered = ErrorPages(), ErrorPages()
        rendered.calls = []
        # the plain page matches the card; the rendered page is the error page
        http_pages = {c.urls[0]: f"<html><head><title>{c.names[0]}</title></head><body><h1>{c.names[0]}</h1></body></html>" for c in cards}

        class Plain:
            calls = []

            def fetch(self, url):
                self.calls.append(url)
                return Page(url, http_pages[url])

        plain = Plain()
        results = run(cards, issuers, plain, rendered)
        self.assertEqual(len(results), 8)
        self.assertLessEqual(len(rendered.calls), 3)
        stopped = [r for r in results if r.status == "skipped" and "stopped" in r.note.lower()]
        self.assertEqual(len(stopped), 5)


if __name__ == "__main__":
    unittest.main()
