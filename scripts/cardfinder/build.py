"""Build the structured offer records the site will use from the recorded offer texts."""
from .parse import parse_offer

_REVIEW_MARKERS = ("struck-through", "no spend requirement found", "no time window", "no bonus amount", "first part")


def _tier(t):
    return {"points": t.points, "cashBack": t.cash_back, "minSpend": t.min_spend, "windowMonths": t.window_months, "note": t.note}


def build_parsed_offers(cards, last_known_offers, confirmed_none=frozenset(), reviewed=frozenset(),
                        cash_paid_as_points=None, stale_issuers=None, stale_since=None):
    """One record per tracked card: its parsed welcome offer, or a note that it has none.

    A card with no recorded offer is recorded as having none only if the site owner confirmed that (confirmed_none);
    otherwise its offer is unknown and it is marked for review, so a card we never managed to read is not mistaken
    for one without a bonus.

    Offers from an issuer in stale_issuers are marked stale, unless stale_since is given and the offer was read on or after it.
    """
    records = []
    cash_paid_as_points = cash_paid_as_points or {}
    stale_issuers = stale_issuers or {}
    for card in cards:
        if not card.expected:
            continue
        record = {"cardId": card.id, "name": card.names[0], "issuer": card.issuer, "cardKind": card.kind}
        entry = last_known_offers.get(card.id)
        if not entry:
            confirmed = card.id in confirmed_none
            records.append({**record, "hasWelcomeOffer": False if confirmed else None, "needsReview": not confirmed})
            continue
        text = entry.get("full_text") or entry["text"]
        p = parse_offer(text)
        parsed = {
            "kind": p.kind, "points": p.points, "cashBack": p.cash_back, "freeNightAwards": p.free_night_awards,
            "minSpend": p.min_spend, "windowMonths": p.window_months,
            "additionalTiers": [_tier(t) for t in p.additional_tiers],
            "ceiling": p.ceiling, "notes": list(p.notes), "displayedAsCash": None,
        }
        if card.id in cash_paid_as_points and p.cash_back and p.points is None:
            # advertised as cash back but actually awarded as points (e.g. Chase Freedom: $200 is 20,000 Ultimate Rewards)
            currency, per_dollar = cash_paid_as_points[card.id]
            parsed.update(points=p.cash_back * per_dollar, currency=currency, displayedAsCash=p.cash_back, cashBack=None)
            parsed["notes"].append(f"advertised as ${p.cash_back:,.0f} cash back but paid as {currency} points")
        needs_review = p.kind == "unparsed" or any(m in n for n in p.notes for m in _REVIEW_MARKERS)
        record.update({"hasWelcomeOffer": True, "sourceText": entry["text"], "seenOn": entry["seen"], "parsed": parsed})
        if card.id in reviewed:
            needs_review = False
            record["reviewedByOwner"] = True
        record["needsReview"] = needs_review
        if card.issuer in stale_issuers and (stale_since is None or entry["seen"] < stale_since):
            record["stale"] = True
            record["staleReason"] = stale_issuers[card.issuer]
        records.append(record)
    return records
