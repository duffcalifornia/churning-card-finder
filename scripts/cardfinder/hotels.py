"""Welcome offers read from a hotel program's own credit card page (IHG, Hilton, Marriott).

The hotel's page and the issuer's own card page describe the same card but can differ: one gets a new offer first,
or lists a different one. Both are read every day, and cardfinder.choose keeps whichever is better.

A hotel page lists several cards one after another, each under a heading with the card's name, so a card's offer is
read from the stretch of page between its heading and the next card's heading. A card's name often appears again
elsewhere (a teaser at the top, a comparison table), and the teaser may state only a headline with no spend
requirement; the first stretch that states a complete offer is the one used.

Nothing here raises: a hotel page that cannot be read leaves the card with the issuer's offer, which is exactly what the
site showed before this existed.
"""
import dataclasses
import html as html_lib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .extract import Offer, extract_offer, looks_like_error_page
from .models import FetchError

MAX_SEGMENT_CHARS = 4000
_OFFER_ENDS = re.compile(r"offer\s+ends\s+\d{1,2}/\d{1,2}/\d{2,4}", re.I)
_ENDS_WINDOW = 250


@dataclass
class HotelSite:
    name: str
    url: str
    cards: Dict[str, List[str]]     # card id -> the heading(s) the page uses for it


@dataclass
class HotelRead:
    card_id: str
    status: str                     # found, not_found
    site: str
    url: str
    offer: Optional[Offer] = None


@dataclass
class SiteResult:
    site: str
    url: str
    status: str                     # ok, unreadable, error_page, no_cards_recognised
    detail: str = ""
    reads: List[HotelRead] = field(default_factory=list)


HOTEL_SITES = [
    HotelSite("ihg", "https://www.ihg.com/onerewards/content/us/en/creditcard", {
        "chase-ihg-premier": ["IHG One Rewards Premier Credit Card"],
        "chase-ihg-premier-select": ["IHG One Rewards Premier Select Credit Card"],
        "chase-ihg-traveler": ["IHG One Rewards Credit Card"],
        "chase-ihg-premier-business": ["IHG One Rewards Business Credit Card"],
    }),
    HotelSite("hilton", "https://www.hilton.com/en/hilton-honors/credit-cards/", {
        "amex-hilton-honors": ["Hilton Honors Card"],
        "amex-hilton-surpass": ["Hilton Honors Surpass Card"],
        "amex-hilton-aspire": ["Hilton Honors Aspire Card", "Hilton Honors Aspire Card - Our Best Points Offer Yet"],
        "amex-hilton-business": ["Hilton Honors Business Card"],
    }),
    HotelSite("marriott", "https://www.marriott.com/credit-cards.mi", {
        "chase-marriott-boundless": ["Marriott Bonvoy Boundless Credit Card from Chase"],
        "chase-marriott-bold": ["Marriott Bonvoy Bold Credit Card from Chase"],
        # The Amex Marriott cards (Bevy, Brilliant, Business) are held back on purpose (site owner, 2026-10-01): Amex is paused, so
        # their cached offers cannot be checked against Marriott's page, and Marriott's lower Bevy and Brilliant offers would
        # replace Amex's expired ones. Add them back once Amex has been re-read.
    }),
]

_BLOCK_TAG = re.compile(
    r"</?(?:address|article|aside|blockquote|body|br|button|dd|div|dl|dt|figcaption|figure|footer|form|h[1-6]|header|hr|"
    r"li|main|nav|ol|p|section|table|tbody|td|tfoot|th|thead|tr|ul|a|label|option|select)\b[^>]*>", re.I)


def block_lines(raw_html):
    """The page as one string per block element, so a heading is a line of its own."""
    raw_html = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", raw_html, flags=re.S | re.I)
    raw_html = _BLOCK_TAG.sub("\n", raw_html)
    raw_html = re.sub(r"<[^>]+>", " ", raw_html)
    lines = (re.sub(r"\s+", " ", html_lib.unescape(line)).strip() for line in raw_html.split("\n"))
    return [line for line in lines if line]


def _norm(text):
    """Letters and digits only, lower case: '®', '™', dashes and spacing around inline tags do not matter."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _segments(lines, headings):
    """{card id: [text between each of its headings and the next heading of any card]}."""
    by_heading = {_norm(h): cid for cid, hs in headings.items() for h in hs}
    marks = [(i, by_heading[_norm(line)]) for i, line in enumerate(lines) if _norm(line) in by_heading]
    out = {}
    for n, (i, cid) in enumerate(marks):
        end = marks[n + 1][0] if n + 1 < len(marks) else len(lines)
        text = " ".join(lines[i + 1:end])
        text = re.sub(r"\$\s+(?=\d)", "$", re.sub(r"\s+", " ", text))[:MAX_SEGMENT_CHARS]
        out.setdefault(cid, []).append(text)
    return out


def _offer_in(text):
    """The first complete offer in this stretch of page, or None.

    Unlike an issuer's page, a hotel page does not mark where an offer ends (no footnote asterisks), so the text that
    follows the offer is ongoing benefits ("Enjoy one Free Night Reward", "$50 in statement credits each quarter"),
    never a second tier. Only the offer sentence is kept, plus its "Offer ends" date, which the choice between sources needs.
    """
    found = extract_offer(text)
    if not found or found.method == "headline_bonus":
        return None
    start = text.find(found.text)
    tail = text[start + len(found.text):start + len(found.text) + _ENDS_WINDOW] if start >= 0 else ""
    ends = _OFFER_ENDS.search(tail)
    return dataclasses.replace(found, full_text=f"{found.text}. {ends.group(0)}." if ends else found.text)


def read_site(site, fetcher):
    """Read every card this hotel page lists. Never raises."""
    try:
        page = fetcher.fetch(site.url)
    except FetchError as e:
        return SiteResult(site.name, site.url, "unreadable", str(e))
    lines = block_lines(page.html)
    if looks_like_error_page(" ".join(lines)):
        return SiteResult(site.name, site.url, "error_page", "the site served an error or block page")
    segments = _segments(lines, site.cards)
    if not segments:
        return SiteResult(site.name, site.url, "no_cards_recognised",
                          "none of the expected card headings were on the page (a redesign, or a page we were not given)")
    reads = []
    for cid in site.cards:
        offer = None
        for text in segments.get(cid, []):
            offer = _offer_in(text)
            if offer:
                break
        reads.append(HotelRead(cid, "found" if offer else "not_found", site.name, page.url, offer))
    return SiteResult(site.name, site.url, "ok", reads=reads)


def read_sites(sites, fetcher, wanted_ids, sleep=None, delay=0.0):
    """Read the sites that list at least one wanted card."""
    results = []
    for site in sites:
        if not wanted_ids & set(site.cards):
            continue
        if results and sleep and delay:
            sleep(delay)
        results.append(read_site(site, fetcher))
    return results


def merge_hotel_offers(results, last_hotel_offers, today):
    """Fold successful reads into the cache; a card not read this run keeps its entry (and its date, so it can go stale)."""
    merged = dict(last_hotel_offers)
    for result in results:
        for r in result.reads:
            if r.status != "found":
                continue
            entry = {"seen": today, "site": r.site, "url": r.url, "text": r.offer.text}
            if r.offer.full_text and r.offer.full_text != r.offer.text:
                entry["full_text"] = r.offer.full_text
            merged[r.card_id] = entry
    return merged


def format_site_result(result):
    lines = [f"[HOTEL {result.site}] {result.url}: {result.status}" + (f" ({result.detail})" if result.detail else "")]
    for r in result.reads:
        lines.append(f"    {r.card_id}: " + (r.offer.text if r.offer else "(no complete offer found on this page)"))
    return "\n".join(lines)
