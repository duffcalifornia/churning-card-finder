"""Pick, for each card, the better of the issuer's offer and the hotel site's offer.

"Better" is the site's own measure: the bonus value in dollars (points x cents per point from data/valuations.json,
plus cash, plus free night certificates). Both pages describe the same card, so the annual fee is the same and cancels.
Two things outrank value, because comparing numbers is meaningless when one of them is not true any more:

  1. an offer whose own text says it ended ("Offer ends 9/30/26") is out, unless every source has ended;
  2. an offer last read more than STALE_DAYS ago loses to one read today. (Amex is paused, so its cached offers age
     while the hotel pages stay current.) If every source is stale they are compared as usual.

A tie, or an offer that cannot be valued, goes to the issuer, the page the card is actually applied for on.
"""
import datetime
import re

from .parse import parse_offer
from .value import bonus_value

STALE_DAYS = 7
_ENDS = re.compile(r"offer\s+ends\s+(\d{1,2})/(\d{1,2})/(\d{2,4})", re.I)


def offer_end_date(entry):
    """The date an offer's text says it ends, or None."""
    m = _ENDS.search(entry.get("full_text") or entry["text"])
    if not m:
        return None
    month, day, year = (int(g) for g in m.groups())
    try:
        return datetime.date(year + 2000 if year < 100 else year, month, day)
    except ValueError:
        return None


def _ended(entry, today):
    end = offer_end_date(entry)
    return end is not None and end < today


def _stale(entry, today):
    return (today - datetime.date.fromisoformat(entry["seen"])).days > STALE_DAYS


def _value(card_id, entry, valuations, card_currency, certificates):
    """Bonus value in dollars of a standard offer, or None when it cannot be valued (never guessed)."""
    p = parse_offer(entry.get("full_text") or entry["text"])
    if p.kind != "standard":
        return None
    parsed = {"points": p.points, "cashBack": p.cash_back, "freeNightAwards": p.free_night_awards}
    currency = card_currency.get(card_id) if (p.points or p.free_night_awards) else "cash"
    try:
        return bonus_value(parsed, currency, valuations, certificate=certificates.get(card_id))
    except (KeyError, ValueError, TypeError):
        return None


def choose_offers(issuer_offers, hotel_offers, valuations, card_currency, certificates, today):
    """(offers, sources): a fresh offers dict (the same entry shape the parser reads) with each hotel-sourced entry
    carrying "source" and "sourceUrl", and {card id: "issuer" or "hotel"} for every card with an offer."""
    offers, sources = dict(issuer_offers), {cid: "issuer" for cid in issuer_offers}
    for cid, hotel in hotel_offers.items():
        issuer = issuer_offers.get(cid)
        if issuer is None:
            winner = "hotel"
        else:
            candidates = {"issuer": issuer, "hotel": hotel}
            for keep in (lambda e: not _ended(e, today) and not _stale(e, today), lambda e: not _ended(e, today), lambda e: True):
                pool = {k: e for k, e in candidates.items() if keep(e)}
                if pool:
                    break
            if len(pool) == 1:
                winner = next(iter(pool))
            else:
                values = {k: _value(cid, e, valuations, card_currency, certificates) for k, e in pool.items()}
                winner = "hotel" if (values["hotel"] is not None and values["issuer"] is not None
                                     and values["hotel"] > values["issuer"]) else "issuer"
        if winner == "hotel":
            entry = {k: v for k, v in hotel.items() if k in ("seen", "text", "full_text")}
            entry.update(source="hotel", sourceUrl=hotel["url"])
            offers[cid], sources[cid] = entry, "hotel"
    return offers, sources
