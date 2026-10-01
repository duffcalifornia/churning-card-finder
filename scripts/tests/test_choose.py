import datetime
import unittest

from cardfinder.choose import choose_offers, offer_end_date

VALUATIONS = {"values": {"hilton-honors": 0.5, "ihg-one-rewards": 0.6}, "freeNightCertificates": {"hilton": 500}}
CURRENCY = {"c-ihg": "ihg-one-rewards", "c-hilton": "hilton-honors"}
CERTS = {"c-hilton": "hilton"}
TODAY = datetime.date(2026, 10, 1)


def entry(points, spend=3000, seen="2026-10-01", ends=None, months=3):
    text = f"Earn {points:,} bonus points after you spend ${spend:,} in the first {months} months"
    e = {"seen": seen, "text": text}
    if ends:
        e["full_text"] = f"{text}. Offer ends {ends}."
    return e


def hotel(points, **kw):
    return {**entry(points, **kw), "site": "ihg", "url": "https://hotel.example"}


def choose(issuer, hotel_offers, card="c-ihg"):
    offers, sources = choose_offers({card: issuer} if issuer else {}, {card: hotel_offers} if hotel_offers else {},
                                    VALUATIONS, CURRENCY, CERTS, TODAY)
    return offers.get(card), sources.get(card)


class Choose(unittest.TestCase):
    def test_the_higher_value_offer_wins_whichever_side_it_is_on(self):
        self.assertEqual(choose(entry(140000), hotel(180000))[1], "hotel")
        self.assertEqual(choose(entry(180000), hotel(140000))[1], "issuer")

    def test_a_hotel_win_is_marked_with_its_source_and_page(self):
        offer, source = choose(entry(140000), hotel(180000))
        self.assertEqual((offer["source"], offer["sourceUrl"]), ("hotel", "https://hotel.example"))
        self.assertNotIn("url", offer)

    def test_a_tie_goes_to_the_issuer(self):
        offer, source = choose(entry(180000), hotel(180000))
        self.assertEqual(source, "issuer")
        self.assertNotIn("source", offer)

    def test_a_card_only_the_hotel_page_has_uses_it_and_one_only_the_issuer_has_keeps_it(self):
        self.assertEqual(choose(None, hotel(100000))[1], "hotel")
        offers, sources = choose_offers({"c-ihg": entry(1000)}, {}, VALUATIONS, CURRENCY, CERTS, TODAY)
        self.assertEqual(sources, {"c-ihg": "issuer"})

    def test_an_offer_that_has_ended_loses_even_if_it_is_bigger(self):
        self.assertEqual(choose(entry(250000, ends="9/30/26"), hotel(100000))[1], "hotel")
        self.assertEqual(choose(entry(250000, ends="10/1/26"), hotel(100000))[1], "issuer")   # still good on its last day
        self.assertEqual(choose(entry(100000), hotel(250000, ends="9/30/26"))[1], "issuer")

    def test_if_every_offer_has_ended_they_are_compared_anyway(self):
        self.assertEqual(choose(entry(250000, ends="9/1/26"), hotel(100000, ends="9/30/26"))[1], "issuer")

    def test_a_stale_read_loses_to_a_fresh_one_but_two_stale_reads_are_compared(self):
        self.assertEqual(choose(entry(250000, seen="2026-09-22"), hotel(100000))[1], "hotel")
        self.assertEqual(choose(entry(250000, seen="2026-09-24"), hotel(100000))[1], "issuer")   # 7 days old is not stale yet
        self.assertEqual(choose(entry(250000, seen="2026-09-01"), hotel(100000, seen="2026-09-02"))[1], "issuer")

    def test_an_offer_that_cannot_be_valued_never_displaces_the_issuers(self):
        self.assertEqual(choose(entry(1000), {**hotel(5000), "text": "Earn a bonus when you spend", "full_text": "Earn a bonus when you spend"})[1], "issuer")
        offers, sources = choose_offers({"c-x": entry(1000)}, {"c-x": hotel(900000)}, VALUATIONS, {}, {}, TODAY)   # no currency known
        self.assertEqual(sources["c-x"], "issuer")

    def test_free_night_awards_count_at_the_cards_certificate_value(self):
        free_night = {"seen": "2026-10-01", "text": "Earn a Free Night Reward + 70,000 Hilton Honors Bonus Points after you spend $2,000 in the first 6 months"}
        self.assertEqual(choose(entry(70000, spend=2000, months=6), {**free_night, "url": "u"}, card="c-hilton")[1], "hotel")   # +1 night

    def test_the_inputs_are_not_changed(self):
        issuer, hotel_offers = {"c-ihg": entry(1000)}, {"c-ihg": hotel(180000)}
        choose_offers(issuer, hotel_offers, VALUATIONS, CURRENCY, CERTS, TODAY)
        self.assertEqual(issuer, {"c-ihg": entry(1000)})
        self.assertEqual(hotel_offers, {"c-ihg": hotel(180000)})


class OfferEndDate(unittest.TestCase):
    def test_two_and_four_digit_years(self):
        self.assertEqual(offer_end_date({"text": "x", "full_text": "Offer ends 1/13/27."}), datetime.date(2027, 1, 13))
        self.assertEqual(offer_end_date({"text": "x", "full_text": "offer ends 09/30/2026"}), datetime.date(2026, 9, 30))
        self.assertIsNone(offer_end_date({"text": "Earn 1,000 points"}))


if __name__ == "__main__":
    unittest.main()
