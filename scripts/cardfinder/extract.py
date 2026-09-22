"""Pull a card's welcome offer and annual fee out of page text.

Each field is found by trying several patterns in order; the pattern that worked is
recorded so a human can judge how much to trust it.
"""
import html as html_lib
import re
from dataclasses import dataclass
from urllib.parse import urljoin

from .matching import last_mention_end, normalize_tokens


@dataclass
class Offer:
    text: str
    method: str            # which pattern found it
    ceiling: bool = False  # "as high as ...": a maximum, not what everyone gets
    struck_through: bool = False  # old and new figures both present; check which is current
    full_text: str = ""           # the offer plus the sentences that follow it (a second tier often starts "Plus, ...")


@dataclass
class Fee:
    text: str
    amount: float
    first_year_waived: bool = False


def page_text(raw_html):
    raw_html = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw_html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = re.sub(r"\s+", " ", html_lib.unescape(text)).strip()
    return re.sub(r"\$\s+(?=\d)", "$", text)   # rendered pages sometimes split "$" from its number


# "after you spend", "after spending", "after you make", or (with a dollar amount, so that marketing like
# "when you spend at restaurants" is not mistaken for an offer) "when you spend $500" / "once you spend $4,000".
_AFTER_SPEND = r"(?:after (?:you )?(?:spend|spending|make|use (?:your )?new Card to make)|(?:when|once) you spend\s+\$[\d,]+)"
# The offer starts at the "Earn"/"Get" closest to its trigger: a capitalised Earn/Get inside the
# gap means an earlier heading or bullet list, so the match is forced to start later.
_NO_NEW_START = r"(?!(?-i:\b(?:Earn|Get)\b))"
OFFER_PATTERNS = [
    # Citi: "Earn 50,000 AAdvantage bonus miles after $2,500 in purchases in the first 3 months" (no "spend").
    # The "in the first N months" wording marks a welcome offer, so this is tried first.
    ("after_amount", rf"(?:Earn|Get)\b(?:{_NO_NEW_START}[^.]){{0,200}}?after\s+\$[\d,]+\s+in\s+(?:net\s+)?purchases\s+(?:in|within)\s+the\s+first\s+\d+\s+(?:months|days)(?:\s+(?:of|from)\s+(?:your\s+)?account\s+opening)?", False),
    ("ceiling", r"as high as\s+\$?[\d,]+[^.]{0,260}?(?:after (?:you )?|within the first)[^.]{0,200}", True),
    ("after_spend", rf"(?:Earn|Get)\b(?:{_NO_NEW_START}[^.]){{0,200}}?{_AFTER_SPEND}[^.]{{0,220}}", False),
    ("on_approval", rf"(?:Earn|Get)\b(?:{_NO_NEW_START}[^.]){{0,200}}?(?:on|upon) approval[^.]{{0,80}}", False),
    # Bank of America: "Online $200 cash rewards bonus after making at least $1,000 in purchases in the first 90 days"
    ("bonus_after_making", r"\$[\d,]+\s+(?:online\s+)?cash\s+rewards\s+bonus\s+after\s+making\s+(?:at\s+least\s+)?\$[\d,]+[^.]{0,120}", False),
    # U.S. Bank: "Earn 20,000 bonus points. 1 Just spend $1,000 in Net Purchases in the first 90 days"
    ("just_spend", r"Earn\s+[\d,]+\s+bonus\s+(?:points|miles)\.?\s*\d?\s*Just spend \$[\d,]+[^.]{0,80}", False),
    # U.S. Bank business: "One-time $750 cash back will be awarded if eligible Net Purchases totaling $6,000 ..."
    ("one_time_bonus", r"One-time\s+(?:\$[\d,]+\s+(?:cash back|bonus)|[\d,]+\s+bonus\s+points)[^.]{0,200}?totaling\s+\$[\d,]+[^.]{0,120}", False),
    # Discover: a bonus with no fixed amount that doubles the first year's cash back or miles
    ("first_year_match", r"match\s+(?:all\s+)?(?:of\s+)?the\s+(?:cash\s+back|miles)[^.]{0,160}first\s+year[^.]{0,80}", False),
    # Bank of America: "Get 50,000 bonus points and a $99 Companion Fare (...) with this offer. To qualify, spend $1,500 or more ..."
    ("to_qualify_spend", r"Get\s+[\d,]+\s+bonus\s+points.{0,160}?To qualify,\s+spend\s+\$[\d,]+[^.]{0,100}", False),
    # Last resort, for offers whose lead-in sentence contains periods ("U.S."): start at the amount itself.
    ("amount_after_spend", rf"\d[\d,]*\s+(?:Bonus\s+)?(?:Miles|Points|Avios)[^.]{{0,80}}?{_AFTER_SPEND}[^.]{{0,220}}", False),
    # Bank of America terms page: "You will qualify for 25,000 bonus points if you use your new credit card account to
    # make any combination of purchase transactions totaling at least $1,000 ... within 90 days"
    ("terms_qualify", r"You will qualify for\s+[\d,]+\s+bonus\s+points\s+if\s+you\s+use\s+your\s+new\s+credit\s+card\s+account\s+to\s+make[^.]{0,200}?totaling\s+at\s+least\s+\$[\d,]+[^.]{0,200}?within\s+\d+\s+days", False),
    # Bank of America headline with no spend requirement in it: "25,000 online bonus points offer (a $250 value)"
    ("headline_bonus", r"[\d,]+\s+online\s+bonus\s+points\s+offer[^.]{0,60}?(?:value\))?", False),
]
_ADJACENT_NUMBERS = re.compile(r"\d{1,3},\d{3}\s+\d{1,3},\d{3}")


# Ongoing benefits that mention spending ("each cardmembership year", "in a calendar year") are not welcome offers.
_ONGOING_BENEFIT = re.compile(
    r"each\s+(?:cardmembership\s+|membership\s+|account\s+)?(?:year|anniversary)|in\s+a\s+calendar\s+year|per\s+calendar\s+year|every\s+year|in\s+a\s+year|"
    r"account\s+anniversary|anniversary\s+year",
    re.I)


_SECOND_TIER_LEAD = re.compile(r"^(?:Plus,?|Also,?|Then,?|And\s+also)\b", re.I)


# A standalone digit acting as a footnote marker before a new topic or dollar figure — the same signal
# extract_offer() already uses to trim the primary offer text at "... months 2 $95 Annual Fee". Without this,
# a page with no asterisks at all (numbered footnotes instead, e.g. Barclays) kept its entire unrelated
# "Benefits" section as full_text, which parse_offer then misread as part of the welcome bonus (real bug, caught
# live 2026-09-22: Barclays JetBlue Premier's "up to $300 in statement credits" ongoing perk, several sentences
# after the actual offer, was picked up as the welcome bonus's cash component and marked it a ceiling too).
_FOOTNOTE_BOUNDARY = re.compile(r"\s*\*(?:\s|$)|\s+\d\s+(?=\$|\d+X\b|(?!Just\b)[A-Z])")


def _following_text(tail):
    """Text after an offer, up to a footnote (an asterisk, or a numbered footnote marker), but reading on when a
    second tier follows it. Also cut at the first sign of ongoing-benefit language ("every year", "account
    anniversary", ...) wherever it falls, footnote or not — a recurring perk is never part of a one-time welcome
    bonus, not even a genuine second tier (real bug, caught live 2026-09-22: Capital One Venture X's recurring
    "$300 Annual Travel Credit... every year" was swept in as if it were part of the signup bonus)."""
    parts = _FOOTNOTE_BOUNDARY.split(tail)
    kept = parts[0]
    for nxt in parts[1:]:
        if not _SECOND_TIER_LEAD.match(nxt.strip()):
            break
        kept += " " + nxt
    benefit = _ONGOING_BENEFIT.search(kept)
    if benefit:
        kept = kept[:benefit.start()]
    return kept


def extract_offer(text):
    for method, pattern, ceiling in OFFER_PATTERNS:
        m = next((c for c in re.finditer(pattern, text, flags=re.I) if not _ONGOING_BENEFIT.search(c.group(0))), None)
        if m:
            found = re.sub(r"\s+", " ", m.group(0)).strip()
            found = re.split(r"\s*\*(?:\s|$)", found)[0].strip()   # footnote asterisks and bullets end the offer
            cut = re.split(r"\s+\d\s+(?=\$|\d+X\b|(?!Just\b)[A-Z])", found)[0].strip()   # a footnote number ("... months 2 $95 Annual Fee")
            # only cut once the offer's trigger has been seen ("Earn 75,000 bonus points 3 Up to a $750 value 1 after spending ...")
            found = cut if re.search(r"(?:after|when|once)\s|Just spend|totaling|To qualify|(?:on|upon)\s+approval", cut, re.I) else found
            lowered = found.lower()
            struck = ("strike through" in lowered or bool(_ADJACENT_NUMBERS.search(found))
                      or ("old bonus" in lowered and "new bonus" in lowered))
            tail = _following_text(text[m.end():m.end() + 300])
            return Offer(text=found, method=method, ceiling=ceiling, struck_through=struck, full_text=(found + tail).strip())
    return None


def _amount(s):
    return float(s.replace(",", ""))


# (pattern, first year waived, fixed amount). A fixed amount is used when the wording states no figure.
FEE_PATTERNS = [
    # Citi: "$99 Annual Fee, waived for the first year" and "Annual Fee 1 $99 Waived for the first year"
    (r"\$([\d,]+)\s+annual fee[^.]{0,20}waived\s+for\s+the\s+first\s+year", True, None),
    (r"annual fee\s*\d?\s*\$([\d,]+)\s+waived\s+for\s+the\s+first\s+year", True, None),
    # U.S. Bank: "$0 intro annual fee for the first year, $95 thereafter" / "... first year and $95 thereafter"
    (r"\$0\s+(?:intro|introductory)\s+annual fee\s+for\s+the\s+first\s+year\s*,?\s*(?:and\s+)?\$([\d,]+)\s+thereafter", True, None),
    # "$0 intro annual fee for the first year, then $95"
    (r"\$0\s+(?:intro|introductory)\s+annual fee[^.]{0,60}?then\s+\$([\d,]+)", True, None),
    # "The annual fee for the ... Card is $325"
    (r"annual fee for the [^?.]{0,100}? is \$([\d,]+)", False, None),
    # "$95 annual fee"
    (r"\$([\d,]+)(?:\.\d\d)?\s+annual fee", False, None),
    # "Annual Fee: $95", "Annual fee - $95", "Annual Fee $395", "ANNUAL FEE $149 applied to first billing statement"
    (r"annual fee[:\s\-\u2013\u2014]*\$([\d,]+)(?!\s+(?:intro|introductory)\b)", False, None),
    # "Annual Fee is $0"
    (r"annual fee is \$([\d,]+)", False, None),
    # No fee stated in words. Deliberately not "with No Annual Fee": that is a navigation menu heading.
    (r"does not charge an annual fee|there is no annual fee|enjoy (?:all the benefits )?with no annual fee|enjoy no annual fee(?!\s+(?:for|during)\s+the\s+first\s+year)", False, 0.0),
]
# Used only when nothing above matched. A bare "No annual fee" label sits next to the apply button on some
# pages; menu headings ("Credit Cards with No Annual Fee", "No Annual Fee Cards (19)") must not count.
FEE_FALLBACK_PATTERNS = [
    (r"(?<!with )\bno annual fee\b(?!\s+(?:business\s+)?(?:credit\s+)?cards?\b)(?!\s+(?:for|during)\s+the\s+first\s+year)", False, 0.0),
]


_NOT_THE_CARDS_OWN_FEE = re.compile(r"employee|additional|authorized|supplementary", re.I)


NAME_WINDOW = 120  # characters before a fee label searched for the card names


def _extract_fee_with(patterns, text, after=None, near=None, others=None, avoid=None):
    """The card's own annual fee: the earliest acceptable match.

    after  skip everything before this text (e.g. a page heading).
    near   the card's names; when given, a fee counts only if the nearest card name before it (after
           the previous fee on the page) is one of these. This drops fees listed for neighbouring cards.
    others names of the other cards, so that "nearest" can be judged (a Surpass fee is not Hilton Honors').
    avoid  extra words of sibling cards; a fee whose lead-in mentions one is skipped.
    Fees for employee, additional or authorized-user cards are always skipped.
    """
    region = text
    if after:
        i = text.find(after)
        if i >= 0:
            region = text[i:]
    raw = []   # (start, end, matched text, amount, waived)
    for pattern, waived, fixed in patterns:
        for m in re.finditer(pattern, region, flags=re.I):
            if _NOT_THE_CARDS_OWN_FEE.search(m.group(0)):
                continue
            amount = fixed if fixed is not None else _amount(m.group(1))
            raw.append((m.start(), m.end(), re.sub(r"\s+", " ", m.group(0)).strip(), amount, waived))
    waived_starts = [f[0] for f in raw if f[4]]
    # A plain "Annual Fee: $0" label right before "$0 intro annual fee ..., then $95" describes the same fee.
    raw = sorted((f for f in raw if f[4] or not any(0 <= w - f[0] <= 40 for w in waived_starts)), key=lambda f: f[0])
    if near:
        kept, prev_end = [], 0
        for start, end, matched, amount, waived in raw:
            lead = region[max(prev_end, start - NAME_WINDOW):start] + " " + matched
            prev_end = end
            mine = last_mention_end(lead, near)
            if mine < 0 or (others and last_mention_end(lead, others) > mine):
                continue
            if avoid and (avoid & normalize_tokens(lead)):
                continue
            kept.append((start, end, matched, amount, waived))
        raw = kept
    if not raw:
        return None
    _, _, matched, amount, waived = raw[0]
    return Fee(text=matched, amount=amount, first_year_waived=waived)


def extract_fee(text, after=None, near=None, others=None, avoid=None):
    """See _extract_fee_with. Falls back to a bare "No annual fee" label only when no fee was found."""
    return (_extract_fee_with(FEE_PATTERNS, text, after, near, others, avoid)
            or _extract_fee_with(FEE_FALLBACK_PATTERNS, text, after, near, others, avoid))


def main_heading(raw_html):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", raw_html, flags=re.I | re.S)
    if not m:
        return None
    return re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))).strip() or None


def from_main_heading(raw_html):
    """The page from its first <h1> tag onward, skipping the <title> and navigation menus before it."""
    m = re.search(r"<h1\b", raw_html, flags=re.I)
    return raw_html[m.start():] if m else raw_html


_ERROR_PAGE = re.compile(
    r"unable to load this page|loading error|access denied|verify you are (?:a )?human|unusual traffic|"
    r"temporarily unavailable|request (?:was )?blocked|too many requests",
    re.I,
)


ERROR_PAGE_MAX_CHARS = 6000   # real error and block pages are short; normal pages can hide an error template


def looks_like_error_page(text):
    """True for an issuer's error, block or bot-check page (which must not be read as 'no offer').

    Some normal pages carry a hidden "temporarily unavailable" template, so a phrase alone is not enough:
    the page must also be short.
    """
    return len(text) < ERROR_PAGE_MAX_CHARS and bool(_ERROR_PAGE.search(text))


def links(raw_html, base_url):
    """All (absolute url, link text) pairs on a page; entities unescaped, relative links resolved against base_url."""
    out = []
    for m in re.finditer(r"<a\b[^>]*?href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", raw_html, flags=re.I | re.S):
        text = re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
        out.append((urljoin(base_url, html_lib.unescape(m.group(1))), text))
    return out
