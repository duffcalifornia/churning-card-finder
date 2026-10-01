"""The offers the site actually uses: the issuer's and the hotel site's, whichever is better (see cardfinder.choose)."""
import datetime
import json
import os

from .choose import choose_offers
from .registry import CARD_CURRENCY, FREE_NIGHT_CERTIFICATE

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def effective_offers(issuer_offers, hotel_offers, today=None):
    with open(os.path.join(ROOT, "data", "valuations.json")) as f:
        valuations = json.load(f)
    offers, _ = choose_offers(issuer_offers, hotel_offers, valuations, CARD_CURRENCY, FREE_NIGHT_CERTIFICATE,
                              today or datetime.date.today())
    return offers
