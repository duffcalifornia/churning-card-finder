"""Spot cards an issuer sells that we do not track yet, and turn each into a proposal for the owner to approve.

Nothing here adds a card to the site. It finds candidates and reads them the way the daily refresh reads a tracked
card; scripts/report_new_cards.py then opens a GitHub issue per candidate, and the owner replies "/track" or
"/ignore" (see status.py). A candidate is a link on the issuer's listing pages or sitemap that:
  - looks like the URLs of cards we already track: same host, same top folder, same depth, same .html-or-not style
    (so no per-issuer patterns to maintain; the registry itself is the pattern);
  - is not a known card, a discontinued one, one the owner already ignored, or a page we recently judged not a card;
  - turns out, when fetched, to be a credit card page with a readable offer or annual fee.

Only the I/O helpers touch the network (through the fetchers passed in); everything else is pure.
"""
import base64
import html as html_lib
import json
import re
from urllib.parse import urlparse

from .check import check_card
from .discovery import MAX_CHILD_SITEMAPS, _by_relevance, _sitemap_urls
from .extract import extract_offer, links, looks_like_error_page, page_text
from .matching import normalize_tokens
from .models import Card, FetchError
from .parse import parse_offer

MAX_CHECKS_PER_ISSUER = 8     # candidate pages fetched per issuer per run; the rest wait for tomorrow
REJECT_DAYS = 30              # a page judged "not a card" is not looked at again for this long

# Slug words that mark a page as something other than a card product page.
_NOT_A_CARD = {"compare", "comparison", "benefits", "faq", "faqs", "contact", "login", "signin", "apply", "sitemap", "offers",
               "calculator", "calculators", "search", "learn", "resources", "articles", "article", "blog", "help", "terms",
               "privacy", "security", "prequalify", "credit-score", "rates", "fees", "rewards-center", "insider", "news",
               "customer-service", "about", "careers", "legal", "disclosures", "tools", "how-it-works", "accept", "spend-management",
               "resource", "prepaid", "gift", "mail-offer", "education", "authorized-user", "browser", "smarts"}
_SLUG_SUFFIX = re.compile(r"(?:\.html?|-credit-cards?|-card)+$")


def normalize_url(url):
    """Host lowercased, no query, fragment or trailing slash: the form URLs are compared in."""
    p = urlparse(url.strip())
    return f"{p.scheme or 'https'}://{p.netloc.lower()}{p.path.rstrip('/')}"


def _parts(url):
    p = urlparse(normalize_url(url))
    segs = [s for s in p.path.split("/") if s]
    return p.netloc, segs, ("html" if segs and segs[-1].endswith(".html") else "plain")


def _dir_key(url):
    host, segs, style = _parts(url)
    return ("dir", host, "/".join(segs[:-1]), style) if len(segs) > 1 else None


def _top_key(url):
    host, segs, style = _parts(url)
    return ("top", host, segs[0] if len(segs) > 1 else None, len(segs), style) if segs else None


def known_shapes(known_urls):
    """What a card URL on this issuer looks like. A folder holding several known cards is matched exactly (so an
    "about-us" folder beside the card folder is not mistaken for cards); a card that stands alone in its folder
    (Chase's /freedom/flex) is matched by its top folder and depth instead."""
    parents = {}
    for u in known_urls:
        k = _dir_key(u)
        if k:
            parents[k] = parents.get(k, 0) + 1
    shapes = set()
    for u in known_urls:
        k = _dir_key(u)
        key = k if (k and parents[k] >= 2) else _top_key(u)
        if key:
            shapes.add(key)
    return shapes


def slug_of(url):
    last = [s for s in urlparse(normalize_url(url)).path.split("/") if s][-1].lower()
    return re.sub(r"[^a-z0-9]+", "-", _SLUG_SUFFIX.sub("", last)).strip("-")


def candidate_urls(found_links, known_urls, skip_urls=()):
    """Links that look like a card page on this issuer but are not one we already know or have ruled out."""
    known = {normalize_url(u) for u in known_urls}
    skip = {normalize_url(u) for u in skip_urls}
    shapes = known_shapes(known_urls)
    seen, out = set(), []
    for url in found_links:
        if not url.startswith("http"):
            continue
        n = normalize_url(url)
        if n in known or n in skip or n in seen or not ({_dir_key(n), _top_key(n)} & shapes):
            continue
        slug = slug_of(n)
        # Whole-word match on the entire path, so "/about-us/news-and-views/..." is out even though its last segment is bland.
        path_words = "-" + "-".join(re.split(r"[^a-z0-9]+", urlparse(n).path.lower())) + "-"
        if len(slug) < 4 or any(f"-{word}-" in path_words for word in _NOT_A_CARD):
            continue
        segs = _parts(n)[1]
        if len(segs) == 1 and "card" not in segs[0].lower():
            continue    # a one-level address is any page on the site; only ones naming a card are worth a look
        seen.add(n)
        out.append(n)
    # Pages whose address mentions a card are the likelier ones, so they are read first when the daily cap bites.
    return sorted(out, key=lambda u: (0 if "card" in u.lower() else 1, u))


def collect_links(issuer, http, rendered=None):
    """Every URL linked from the issuer's listing pages or listed in its sitemaps. A page that cannot be fetched is
    skipped: a partial list only means fewer candidates today."""
    found = []
    for lp in issuer.listing_pages:
        # Listing pages often list their cards only after scripts run (Wells Fargo's Active Cash is missing from the
        # plain HTML), so use the browser whenever there is one, and the plain fetch if it fails or is not available.
        for fetcher in ([rendered] if rendered is not None else []) + [http]:
            try:
                page = fetcher.fetch(lp)
            except FetchError:
                continue
            found += [u for u, _ in links(page.html, page.url)]
            break
    for sm in issuer.sitemaps:
        try:
            xml = http.fetch(sm).html
        except FetchError:
            continue
        if "<sitemapindex" in xml.lower():
            for child in _by_relevance(_sitemap_urls(xml))[:MAX_CHILD_SITEMAPS]:
                try:
                    found += _sitemap_urls(http.fetch(child).html)
                except FetchError:
                    continue
        else:
            found += _sitemap_urls(xml)
    return found


def _clean(raw):
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"[\u00ae\u2122\u2120\u00a9\u2020\u2021]", "", html_lib.unescape(text))
    return re.sub(r"\s+", " ", text).strip()


def page_headings(page_html):
    """(main heading, first title segment), each cleaned; either may be empty."""
    title = re.search(r"<title[^>]*>(.*?)</title>", page_html, flags=re.I | re.S)
    heading = re.search(r"<h1[^>]*>(.*?)</h1>", page_html, flags=re.I | re.S)
    first_title = re.split(r"\s+[|\u2013\u2014]\s+|\s+-\s+|:", _clean(title.group(1)) if title else "")[0].strip()
    return (_clean(heading.group(1)) if heading else ""), first_title


_CATEGORY_WORDS = re.compile(r"\b(?:cards|offers?|compare|comparison|best)\b", re.I)
_SINGULAR_CARD = re.compile(r"\bcard\b", re.I)


def is_card_page(h1, first_title):
    """True when the headings read like one card's page. A category page ("Cash back credit cards", "Compare Chase
    Freedom Credit Cards", "Balance Transfer Credit Card Offers") is plural or talks about offers; a card's own page
    says "Card" once. (Counting how many known cards a page links to does not work: real card pages link to their
    siblings too.)"""
    if _CATEGORY_WORDS.search(h1) or _CATEGORY_WORDS.search(first_title):
        return False
    return bool(_SINGULAR_CARD.search(h1 + " " + first_title))


def page_name(page_html):
    """The card's name: the main heading when it reads like one card, else the title's first segment."""
    h1, first_title = page_headings(page_html)
    return h1 if h1 and _SINGULAR_CARD.search(h1) and not _CATEGORY_WORDS.search(h1) else (first_title or h1)


def is_known_card(names, all_cards):
    """True if a page named `names` (its heading and title) is a card we already have. Deliberately stricter than
    matching.page_matches_card, which is built to find a *given* card's page: it scores "Business Essentials Plus
    Visa Card" as a match for the plain Business Essentials card. Here a page is known only if its name adds no word
    beyond one of a known card's names, or is nearly identical to one."""
    for name in names:
        mine = normalize_tokens(name)
        if not mine:
            continue
        for card in all_cards:
            for alias in card.names:
                theirs = normalize_tokens(alias)
                if theirs and (mine <= theirs or len(mine & theirs) / len(mine | theirs) >= 0.8):
                    return True
    return False


def propose_id(issuer, url, taken):
    base = f"{issuer}-{slug_of(url)}"
    cid, n = base, 2
    while cid in taken:
        cid, n = f"{base}-{n}", n + 1
    return cid


def evaluate_candidate(url, issuer_name, issuer_cfg, all_cards, http, rendered, taken_ids):
    """("candidate", proposal) for a real, untracked card page; ("reject", reason) for a page that is not one;
    ("unsure", reason) when a fetch failed or the issuer served an error page (nothing learned: try again later)."""
    try:
        page = http.fetch(url)
    except FetchError as e:
        return "unsure", f"fetch failed ({e.status or e})"
    text = page_text(page.html)
    if looks_like_error_page(text):
        return "unsure", "error page"
    h1, first_title = page_headings(page.html)
    if not is_card_page(h1, first_title):
        return "reject", "not a single card's page (a category page, offer page or article)"
    name = page_name(page.html)
    if is_known_card([n for n in (h1, first_title) if n], all_cards):
        return "reject", "same card as one already known"

    kind = "business" if "business" in (url + " " + name).lower() else "personal"
    cid = propose_id(issuer_name, url, taken_ids)
    provisional = Card(id=cid, issuer=issuer_name, names=[name], kind=kind, urls=[url])
    result = check_card(provisional, issuer_cfg, http, rendered=rendered, siblings=all_cards)
    if result.status not in ("found", "found_via_fallback") or not result.fee:
        return "reject", "no annual fee found on the page (a card's own page states one)"

    proposal = {"id": cid, "name": name, "issuer": issuer_name, "kind": kind, "url": url, "flags": list(result.flags),
                "offer": None, "fee": None}
    if result.offer:
        proposal["offer"] = {"text": result.offer.text}
        if result.offer.full_text and result.offer.full_text != result.offer.text:
            proposal["offer"]["full_text"] = result.offer.full_text
        p = parse_offer(result.offer.full_text or result.offer.text)
        proposal["reads_as"] = {"points": p.points, "cashBack": p.cash_back, "freeNightAwards": p.free_night_awards,
                                "minSpend": p.min_spend, "windowMonths": p.window_months}
    if result.fee:
        proposal["fee"] = {"amount": result.fee.amount, "firstYearWaived": bool(result.fee.first_year_waived)}
    return "candidate", proposal


def find_new_cards(issuers, all_cards, http, rendered, ignored_urls, rejects, today, taken_ids=None, log=print):
    """Look for untracked cards across the given issuers.

    issuers: {issuer name: IssuerConfig} to scan (callers leave out paused ones). all_cards: every card the registry
    knows, tracked or not. ignored_urls: URLs the owner said "/ignore" to. rejects: {url: date} pages recently judged
    not a card. Returns (proposals, new_rejects {url: today}).
    """
    taken = set(taken_ids or {c.id for c in all_cards})
    proposals, new_rejects = [], {}
    recent_rejects = {u for u, d in rejects.items() if _days_between(d, today) < REJECT_DAYS}
    for name, cfg in issuers.items():
        cards = [c for c in all_cards if c.issuer == name]
        known_urls = [u for c in cards for u in c.urls]
        if not known_urls:
            continue
        try:
            found = collect_links(cfg, http, rendered)
        except Exception as e:      # discovery of new cards must never take the daily run down
            log(f"New-card scan skipped for {name}: {e}")
            continue
        candidates = candidate_urls(found, known_urls, set(ignored_urls) | recent_rejects | set(new_rejects))
        for url in candidates[:MAX_CHECKS_PER_ISSUER]:
            try:
                verdict, detail = evaluate_candidate(url, name, cfg, all_cards, http, rendered, taken)
            except Exception as e:
                log(f"New-card check failed for {url}: {e}")
                continue
            if verdict == "candidate":
                taken.add(detail["id"])
                proposals.append(detail)
                log(f"[NEW CARD?] {detail['name']}  {url}")
            elif verdict == "reject":
                new_rejects[url] = today
            else:
                log(f"New-card check unsure for {url}: {detail}")
    return proposals, new_rejects


def _days_between(earlier, later):
    import datetime
    return (datetime.date.fromisoformat(later) - datetime.date.fromisoformat(earlier)).days


def encode_proposal(proposal):
    """The proposal as base64 JSON, safe to hide in an HTML comment in the issue body (offer text can hold "--")."""
    return base64.b64encode(json.dumps(proposal, sort_keys=True).encode()).decode()


_MARKER = re.compile(r"<!--\s*new-card:\s*([A-Za-z0-9+/=]+)\s*-->")


def decode_proposal(body):
    """The proposal hidden in an issue body, or None if there is none or it is unreadable."""
    m = _MARKER.search(body or "")
    if not m:
        return None
    try:
        data = json.loads(base64.b64decode(m.group(1)).decode())
    except (ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def issue_title(name):
    return f"New card found: {name}"


def _money(x):
    return f"${x:,.0f}"


def _reads_as(r):
    parts = []
    if r.get("points"):
        parts.append(f"{r['points']:,.0f} points")
    if r.get("cashBack"):
        parts.append(f"{_money(r['cashBack'])} cash back")
    if r.get("freeNightAwards"):
        parts.append(f"{r['freeNightAwards']} free night award(s)")
    if r.get("minSpend"):
        parts.append(f"after {_money(r['minSpend'])} spend" + (f" in {r['windowMonths']} months" if r.get("windowMonths") else ""))
    return ", ".join(parts) or "nothing the parser could count"


def issue_body(proposal, currency_ids):
    offer = proposal.get("offer")
    fee = proposal.get("fee")
    lines = [
        f"The daily refresh found a card on {proposal['issuer']}'s site that this site does not track yet: **{proposal['name']}**.",
        "",
        proposal["url"],
        "",
        "What it read:",
        f"- Offer: {offer['text'] if offer else '(none found)'}",
    ]
    if proposal.get("reads_as"):
        lines.append(f"- The site would count that as: {_reads_as(proposal['reads_as'])}")
    lines += [
        f"- Annual fee: {_money(fee['amount']) if fee else '(not found)'}" + (", waived the first year" if fee and fee.get("firstYearWaived") else ""),
        f"- Looks like a **{proposal['kind']}** card (proposed id `{proposal['id']}`).",
        "",
        "**Reply to this issue with one of:**",
        "",
        "- `/track` - start tracking it. It goes on the site with this offer and fee, is read every day from now on, and a "
        "changelog line is added. Options, all optional: `kind=business`, `name=\"Exact Card Name\"`, `currency=<id>`.",
        "- `/ignore` - never raise this page again (retail store cards, cards you do not want, and so on).",
        "",
        "If its offer is paid in points or miles, you must give the currency: `/track currency=ultimate-rewards`. (A card "
        "whose offer is free night awards cannot be tracked from a reply yet: it needs a certificate value added by hand.) "
        "It will not have any family, lifetime or cooldown rules until those are added by hand.",
        "",
        "<details><summary>Currency ids</summary>",
        "",
        ", ".join(f"`{c}`" for c in currency_ids),
        "",
        "</details>",
        "",
        "This works from the GitHub mobile app. Only replies from someone with write access are acted on.",
        "",
        f"<!-- new-card: {encode_proposal(proposal)} -->",
        "",
    ]
    return "\n".join(lines)


MAX_NEW_ISSUES_PER_RUN = 5     # a flood on the first day (a whole issuer's untracked cards) is spread over days


def plan_new_reports(doc, issues, limit=MAX_NEW_ISSUES_PER_RUN):
    """The proposals in doc that have no open issue yet, at most `limit` of them (the rest surface on later runs)."""
    open_urls = set()
    for issue in issues:
        p = decode_proposal(issue.get("body")) if issue.get("state") == "OPEN" else None
        if p and p.get("url"):
            open_urls.add(normalize_url(p["url"]))
    fresh = [c for c in doc.get("candidates", []) if normalize_url(c["url"]) not in open_urls]
    return fresh[:limit]
