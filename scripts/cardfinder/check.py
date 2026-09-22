"""Check one card end to end: find its page, then read its offer and fee.

Nothing here assumes a single method works. The card may have moved (discovery falls
back), the offer may only exist after scripts run (rendered fetch), the default page may
hide the offer that a variant page shows, and raw HTML for issuers that render offers
client side is never trusted for the offer.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional

from .discovery import Attempt, _variants, find_card
from .extract import Fee, Offer, extract_fee, extract_offer, from_main_heading, links, looks_like_error_page, page_text
from .matching import distinguishing_tokens, page_matches_card
from .models import Card, FetchError, IssuerConfig


@dataclass
class CardResult:
    card_id: str
    name: str
    status: str                      # found, found_via_fallback, not_found, skipped
    url: Optional[str] = None
    strategy: Optional[str] = None
    offer: Optional[Offer] = None
    fee: Optional[Fee] = None
    flags: List[str] = field(default_factory=list)
    attempts: List[Attempt] = field(default_factory=list)
    note: str = ""


def _offer_from(fetcher, url):
    return extract_offer(page_text(fetcher.fetch(url).html))


def check_card(card, issuer, http, rendered=None, siblings=()):
    if not card.expected:
        return CardResult(card.id, card.names[0], "skipped", note=card.note)

    found = find_card(card, issuer, http)
    if found.url is None:
        return CardResult(card.id, card.names[0], "not_found", attempts=found.attempts, note=card.note)

    flags = []
    status = "found" if found.strategy == "known_url" else "found_via_fallback"
    if status == "found_via_fallback":
        flags.append("url_changed")

    # For issuers that render offers client side, fetch the rendered page once and use it for the
    # offer and the fee; the plain copy stays as a fallback for the fee.
    rendered_page = None
    if issuer.render and rendered is not None:
        try:
            rendered_page = rendered.fetch(found.url)
        except FetchError:
            flags.append("render_failed")

    fee = None
    for page_html in ([rendered_page.html] if rendered_page else []) + [found.html]:
        fee = extract_fee(page_text(from_main_heading(page_html)),
                          near=card.names if issuer.fee_near_name else None,
                          others=[n for c in siblings if c is not card for n in c.names] if issuer.fee_near_name else None,
                          avoid=distinguishing_tokens(card, siblings) if issuer.fee_near_name else None)
        if fee:
            break

    offer = None
    fetcher_for_offers = http
    if issuer.render:
        # Raw HTML for these issuers carries stale marketing numbers; only the rendered page is reliable.
        if rendered is None:
            flags.append("needs_render")
        elif rendered_page is not None:
            fetcher_for_offers = rendered
            offer = extract_offer(page_text(rendered_page.html))
    else:
        offer = extract_offer(page_text(found.html))
        if offer is None and rendered is not None:
            try:
                offer = _offer_from(rendered, found.url)
                if offer:
                    flags.append("offer_from_rendered")
            except FetchError:
                flags.append("render_failed")

    offer_page_html = rendered_page.html if (issuer.render and rendered_page) else found.html
    if offer is None and looks_like_error_page(page_text(offer_page_html)):
        flags.append("page_error")   # the issuer served an error or block page: not evidence that there is no offer
    can_look_further = not {"needs_render", "render_failed", "page_error"} & set(flags)
    if offer is None and can_look_further:
        # The default page may hide the offer that a variant of the same page shows.
        for variant in _variants(found.url, issuer.variant_suffixes):
            try:
                page = fetcher_for_offers.fetch(variant)
            except FetchError:
                continue
            if not page_matches_card(card, page.html):
                continue
            offer = extract_offer(page_text(page.html))
            if offer:
                flags.append("offer_from_variant")
                break

    # A headline with no spend requirement: the card's terms page usually states it.
    if offer is not None and offer.method == "headline_bonus":
        for url, text in links(offer_page_html, found.url)[:200]:
            if not re.search(r"terms\s*(?:&|and)\s*conditions|terms-and-conditions|offer details", f"{text} {url}", re.I):
                continue
            try:
                completed = extract_offer(page_text(fetcher_for_offers.fetch(url).html))
            except FetchError:
                continue
            if completed and completed.method != "headline_bonus":
                offer = completed
                flags.append("offer_from_terms_page")
                break

    note = card.note
    if offer is None and card.last_known_offer:
        # The live page could not be read (block, error, missing offer): fall back to the last good read.
        offer = Offer(text=card.last_known_offer, method="last_known")
        flags = [f for f in flags if f != "no_offer_found"] + ["offer_from_last_known"]
        note = (note + " " if note else "") + f"Offer taken from the last successful read on {card.last_known_on}."
    elif offer is None and can_look_further:
        flags.append("no_offer_found")
    if offer and offer.method in ("amount_after_spend", "headline_bonus"):
        flags.append("offer_may_be_partial")   # found by the amount alone; the lead-in text may hold extra components
    if offer and offer.ceiling:
        flags.append("offer_is_ceiling")
    if offer and offer.struck_through:
        flags.append("check_struck_through")
    if fee is None and card.known_fee is not None:
        fee = Fee(text="provided by the site owner", amount=card.known_fee, first_year_waived=card.known_fee_first_year_waived)
        flags.append("fee_from_owner")
    elif fee is None:
        flags.append("no_fee_found")
    elif card.expected_fee is not None and fee.amount != card.expected_fee:
        flags.append("fee_changed")   # a moved card showing a different fee may be the wrong page

    return CardResult(card.id, card.names[0], status, url=found.url, strategy=found.strategy,
                      offer=offer, fee=fee, flags=flags, attempts=found.attempts, note=note)
