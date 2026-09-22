"""Find a card's page even when its URL has changed.

Strategies run in order and stop at the first page that really is the card:
  1. known_url  the URLs we already have
  2. variant    trailing-slash and path-suffix variants of those URLs
  3. sitemap    URLs in the issuer's sitemap (following a sitemap index)
  4. listing    links on the issuer's card listing pages
Every request is recorded, so a card that cannot be found comes with the full list of
what was tried. A URL is never fetched twice.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from .matching import link_score, page_matches_card
from .models import FetchError

MAX_CANDIDATES = 5          # candidates fetched per sitemap or listing search
MAX_CHILD_SITEMAPS = 10     # children followed from one sitemap index
CANDIDATE_MIN_SCORE = 0.4


@dataclass
class Attempt:
    strategy: str
    url: str
    outcome: str  # ok, http_<status>, error: <msg>, wrong_page, no_candidates


@dataclass
class Discovery:
    url: Optional[str]
    html: Optional[str]
    strategy: Optional[str]
    attempts: List[Attempt] = field(default_factory=list)


def _variants(url, suffixes):
    base = url.rstrip("/")
    out = [base + "/"] if url != base + "/" else [base]
    for s in suffixes:
        out.append(base + "/" + s.lstrip("/"))
    return [u for u in out if u != url]


_CARD_SITEMAP = re.compile(r"credit|card|small-?business|business", re.I)


def _by_relevance(child_urls):
    """Card-related child sitemaps first, so a large index cannot push them past the limit."""
    return sorted(child_urls, key=lambda u: 0 if _CARD_SITEMAP.search(urlparse(u).path) else 1)


def _sitemap_urls(xml):
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)


def _anchors(markup, base_url):
    out = []
    for m in re.finditer(r"<a\b[^>]*?href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", markup, flags=re.I | re.S):
        out.append((urljoin(base_url, m.group(1)), re.sub(r"<[^>]+>", " ", m.group(2))))
    return out


def find_card(card, issuer, fetcher):
    attempts = []
    tried = set()

    def get(strategy, url):
        """Fetch url once. Return the page only if it is the right card."""
        if url in tried:
            return None
        tried.add(url)
        try:
            page = fetcher.fetch(url)
        except FetchError as e:
            attempts.append(Attempt(strategy, url, f"http_{e.status}" if e.status else f"error: {e}"))
            return None
        if not page_matches_card(card, page.html):
            attempts.append(Attempt(strategy, url, "wrong_page"))
            return None
        attempts.append(Attempt(strategy, url, "ok"))
        return page

    def fetch_raw(strategy, url):
        """Fetch a helper page (sitemap, listing) without checking that it is a card. Returns the Page."""
        tried.add(url)
        try:
            return fetcher.fetch(url)
        except FetchError as e:
            attempts.append(Attempt(strategy, url, f"http_{e.status}" if e.status else f"error: {e}"))
            return None

    def done(page, strategy):
        return Discovery(url=page.url, html=page.html, strategy=strategy, attempts=attempts)

    def best(scored):
        # Best score first; on a tie prefer the deeper path (a product page over its family landing page).
        ranked = sorted((s for s in scored if s[0] >= CANDIDATE_MIN_SCORE),
                        key=lambda s: (-round(s[0], 3), -urlparse(s[1]).path.strip("/").count("/")))
        seen, urls = set(), []
        for _, u in ranked:
            if u not in seen:
                seen.add(u)
                urls.append(u)
        return urls[:MAX_CANDIDATES]

    def try_candidates(strategy, urls):
        if not urls:
            attempts.append(Attempt(strategy, "", "no_candidates"))
        for u in urls:
            page = get(strategy, u)
            if page:
                return page
        return None

    # 1. known URLs
    for url in card.urls:
        page = get("known_url", url)
        if page:
            return done(page, "known_url")

    # 2. variants of the known URLs
    variant_urls = [v for url in card.urls for v in _variants(url, issuer.variant_suffixes)]
    for url in variant_urls:
        page = get("variant", url)
        if page:
            return done(page, "variant")
    if not variant_urls:
        attempts.append(Attempt("variant", "", "no_candidates"))

    # 3. sitemaps
    scored = []
    for sm_url in issuer.sitemaps:
        sm_page = fetch_raw("sitemap", sm_url)
        if sm_page is None:
            continue
        xml = sm_page.html
        locs = _sitemap_urls(xml)
        if "<sitemapindex" in xml.lower():
            for child in _by_relevance(locs)[:MAX_CHILD_SITEMAPS]:
                child_page = fetch_raw("sitemap", child)
                if child_page:
                    locs_child = _sitemap_urls(child_page.html)
                    scored += [(link_score(card, urlparse(u).path), u) for u in locs_child]
        else:
            scored += [(link_score(card, urlparse(u).path), u) for u in locs]
    page = try_candidates("sitemap", best(scored))
    if page:
        return done(page, "sitemap")

    # 4. listing pages
    scored = []
    for lp in issuer.listing_pages:
        lp_page = fetch_raw("listing", lp)
        if lp_page is None:
            continue
        # Relative links resolve against where the fetch actually landed (listing pages may redirect to another host).
        for href, text in _anchors(lp_page.html, lp_page.url):
            scored.append((max(link_score(card, text), link_score(card, urlparse(href).path)), href))
    page = try_candidates("listing", best(scored))
    if page:
        return done(page, "listing")

    return Discovery(url=None, html=None, strategy=None, attempts=attempts)
