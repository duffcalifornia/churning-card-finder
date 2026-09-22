"""Fold a fresh checking run's successful reads back into the last-known cache files.

Only cards actually read this run (status found or found_via_fallback) are touched. Everything else —
not_found, skipped (paused issuer, a discontinued card, or the issuer's circuit breaker tripped) — keeps
its existing cached entry untouched, exactly like the fallback check_card() itself uses when a live read
fails. A missing offer or fee on an otherwise-found card (one read worked, the other didn't) leaves that
one field's old value alone rather than dropping it.

Pure: never mutates its inputs, makes no network or file requests.
"""


def merge_last_known(results, last_offers, last_fees, waived_fee_ids, today):
    """(new_offers, new_fees, new_waived_fee_ids), each a fresh dict/set, none of the inputs changed."""
    new_offers = dict(last_offers)
    new_fees = dict(last_fees)
    new_waived = set(waived_fee_ids)

    for r in results:
        if r.status not in ("found", "found_via_fallback"):
            continue
        if r.offer:
            entry = {"seen": today, "text": r.offer.text}
            if r.offer.full_text and r.offer.full_text != r.offer.text:
                entry["full_text"] = r.offer.full_text
            new_offers[r.card_id] = entry
        if r.fee:
            new_fees[r.card_id] = r.fee.amount
            if r.fee.first_year_waived:
                new_waived.add(r.card_id)
            # A fee read without the waived wording is not evidence the waiver ended; never remove it here.

    return new_offers, new_fees, new_waived
