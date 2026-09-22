"""Decide whether a URL, link text or fetched page is a given card.

Used by discovery to reject the wrong page (a redirect to an index page, a sibling card
with overlapping words) before any offer is read from it.
"""
import html as html_lib
import re

# Words that carry no information about which card it is.
STOPWORDS = {
    "the", "a", "an", "from", "by", "for", "of", "and", "with",
    "american", "express", "amex", "chase", "card", "cards", "credit",
    "com", "sm", "tm",   # "Chase.com" in titles; service-mark text in headings
    "u", "s", "bank",    # "U.S. Bank" prefix
}
MATCH_THRESHOLD = 0.7  # a sibling that adds one word (Disney Premier, Hilton Surpass) scores about 0.67


def normalize_tokens(text):
    text = html_lib.unescape(text).lower()
    text = re.sub(r"[®™℠©†‡]", "", text)
    words = re.findall(r"[a-z0-9]+", text)
    return {w for w in words if w not in STOPWORDS}


def ordered_words(text):
    """The meaningful words of text in reading order (same filtering as normalize_tokens)."""
    text = html_lib.unescape(text).lower()
    text = re.sub(r"[\u00ae\u2122\u2120\u00a9\u2020\u2021]", "", text)
    return [w for w in re.findall(r"[a-z0-9]+", text) if w not in STOPWORDS]


def mentions_name(text, names):
    """True if any of the names appears in text as consecutive words."""
    words = ordered_words(text)
    for name in names:
        target = ordered_words(name)
        n = len(target)
        if n and any(words[i:i + n] == target for i in range(len(words) - n + 1)):
            return True
    return False


def last_mention_end(text, names):
    """Index just past the last place any of the names appears in text (as consecutive words), or -1."""
    words = ordered_words(text)
    best = -1
    for name in names:
        target = ordered_words(name)
        n = len(target)
        for i in range(len(words) - n + 1):
            if n and words[i:i + n] == target:
                best = max(best, i + n)
    return best


def distinguishing_tokens(card, others):
    """Words that identify sibling cards whose names contain this card's name (Surpass, Aspire for Hilton Honors)."""
    mine = [normalize_tokens(n) for n in card.names]
    extra = set()
    for other in others:
        if other is card or other.kind != card.kind:
            continue
        for name in other.names:
            theirs = normalize_tokens(name)
            for m in mine:
                if m and m < theirs:
                    extra |= theirs - m
    return extra


def _score_one(card_tokens, candidate_tokens, kind):
    if not card_tokens or not candidate_tokens:
        return 0.0
    union = card_tokens | candidate_tokens
    score = len(card_tokens & candidate_tokens) / len(union)
    # A personal card must not match a business page (and the other way round).
    if kind == "personal" and "business" in candidate_tokens and "business" not in card_tokens:
        score *= 0.5
    if kind == "business" and "business" not in candidate_tokens:
        score *= 0.5
    return score


def match_score(card, candidate_text):
    """Best similarity, 0 to 1, between any of the card's names and the candidate text."""
    candidate_tokens = normalize_tokens(candidate_text)
    return max((_score_one(normalize_tokens(n), candidate_tokens, card.kind) for n in card.names), default=0.0)


def _apply_kind(score, kind, card_tokens, candidate_tokens):
    if kind == "personal" and "business" in candidate_tokens and "business" not in card_tokens:
        return score * 0.5
    if kind == "business" and "business" not in candidate_tokens:
        return score * 0.5
    return score


def link_score(card, candidate_text):
    """Looser score for shortlisting links and sitemap URLs (0 to 1).

    Rewards covering the card's name words and mildly penalises extra words, so
    "/travel-credit-cards/aircanada/aeroplan" still finds "Aeroplan". Candidates are always
    checked against the fetched page (page_matches_card) before being accepted.
    """
    candidate_tokens = normalize_tokens(candidate_text)
    best = 0.0
    for name in card.names:
        tokens = normalize_tokens(name)
        if not tokens:
            continue
        coverage = len(tokens & candidate_tokens) / len(tokens)
        score = coverage - 0.02 * len(candidate_tokens - tokens)
        best = max(best, _apply_kind(max(score, 0.0), card.kind, tokens, candidate_tokens))
    return best


def _first(pattern, markup):
    m = re.search(pattern, markup, flags=re.I | re.S)
    return re.sub(r"<[^>]+>", " ", m.group(1)) if m else ""


def _title_segments(title):
    """Split a page title at separators ("Card | Chase.com", "Card: Airline Rewards") into its parts."""
    return [part for part in re.split(r"\s+[|\u2013\u2014]\s+|\s+-\s+|:", title) if part.strip()]


def page_matches_card(card, page_html):
    """True if the page's title or main heading names the card.

    Any single title segment (or the heading) naming the card is enough; whether the page is a business
    or personal page is judged from all of them together ("Spark Cash | Cash Back Business Credit Card").
    """
    title = _first(r"<title[^>]*>(.*?)</title>", page_html)
    heading = _first(r"<h1[^>]*>(.*?)</h1>", page_html)
    texts = _title_segments(title) + [heading]
    page_tokens = set().union(*(normalize_tokens(t) for t in texts))
    best = 0.0
    for text in texts:
        candidate = normalize_tokens(text)
        for name in card.names:
            tokens = normalize_tokens(name)
            if tokens and candidate:
                best = max(best, _apply_kind(len(tokens & candidate) / len(tokens | candidate), card.kind, tokens, page_tokens))
    return best >= MATCH_THRESHOLD
