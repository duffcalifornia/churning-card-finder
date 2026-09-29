"""Applying the owner's answer to a "card not found" review issue.

Two answers exist: "/discontinued" (the card can no longer be applied for) and "/still-active" (it can; the scraper
just cannot find it). Only the first changes any data, and it does so by adding the card to
discontinued_cards.json, which registry.py already treats like any other not-tracked card.

Kept free of gh calls and of the registry itself (callers pass in what they need) so it can be tested on temp files.
"""
import json
import re
import shlex
from urllib.parse import urlparse

from .changelog import added_cards_entry, prepend_changelog_entry, removed_cards_entry
from .newcards import normalize_url

COMMANDS = {"/discontinued": "discontinued", "/still-active": "still-active", "/track": "track", "/ignore": "ignore"}
OPTION_KEYS = ("kind", "name", "currency")
_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_command(comment_body):
    """"discontinued", "still-active" or None, from the first word of a comment. Anything after it is ignored, so
    "/discontinued thanks, checked the site" works; a command buried mid-comment does not."""
    words = (comment_body or "").split()
    return COMMANDS.get(words[0].lower()) if words else None


def _load(path):
    with open(path) as f:
        return json.load(f)


def discontinue(card_id, card_names, today, issue_number, paths):
    """Record a card as no longer available. Returns its display name, or None if it was already recorded.

    card_names: {card id: display name} for every tracked card; an id not in it is refused rather than guessed.
    paths: dict with discontinued, offers, fees, waived, changelog. Removes the card's cached offer and fee so no stale
    numbers linger, and adds the standard changelog line. The caller rebuilds data/ afterwards.
    """
    if card_id not in card_names:
        raise ValueError(f"unknown card id: {card_id}")
    discontinued = _load(paths["discontinued"])
    if card_id in discontinued:
        return None

    discontinued[card_id] = {
        "date": today,
        "note": f"No longer offered for new applications (confirmed by the site owner, {today}, review issue #{issue_number}).",
    }
    with open(paths["discontinued"], "w") as f:
        json.dump(discontinued, f, indent=1)
        f.write("\n")

    # Same file formats refresh_offers.py writes, so the diff is only this card's entries.
    offers = _load(paths["offers"])
    if offers.pop(card_id, None) is not None:
        with open(paths["offers"], "w") as f:
            json.dump(offers, f, indent=1)
            f.write("\n")
    fees = _load(paths["fees"])
    if fees.pop(card_id, None) is not None:
        with open(paths["fees"], "w") as f:
            json.dump(fees, f, indent=2)
            f.write("\n")
    waived = _load(paths["waived"])
    if card_id in waived:
        with open(paths["waived"], "w") as f:
            json.dump(sorted(set(waived) - {card_id}), f, indent=1)
            f.write("\n")

    prepend_changelog_entry(paths["changelog"], today, removed_cards_entry([card_names[card_id]]))
    return card_names[card_id]


def parse_options(comment_body):
    """key=value options after the command on a comment's first line, e.g. `/track kind=business name="Some Card"`.
    Only kind, name and currency are read; anything else on the line is ignored."""
    first = (comment_body or "").strip().split("\n")[0]
    unbalanced = False
    try:
        tokens = shlex.split(first)
    except ValueError:      # an unclosed quote: the one-word options are still clear, a half-quoted name is not
        tokens, unbalanced = first.split(), True
    options = {}
    for token in tokens[1:]:
        key, _, value = token.partition("=")
        if key.lower() in OPTION_KEYS and value.strip() and not (unbalanced and key.lower() == "name"):
            options[key.lower()] = value.strip()
    return options


def validate_proposal(p, issuer_hosts):
    """A proposal (decoded from an issue body) is only trusted after this: it drives a commit. Raises ValueError."""
    try:
        cid, name, issuer, kind, url = p["id"], p["name"], p["issuer"], p["kind"], p["url"]
    except (KeyError, TypeError):
        raise ValueError("the issue does not carry a readable card proposal")
    if not (isinstance(cid, str) and _ID.match(cid) and len(cid) <= 80):
        raise ValueError("the proposed card id is not valid")
    if not (isinstance(name, str) and 2 <= len(name) <= 120 and name.isprintable()):
        raise ValueError("the proposed card name is not valid")
    if issuer not in issuer_hosts:
        raise ValueError(f"unknown issuer {issuer!r}")
    if kind not in ("personal", "business"):
        raise ValueError("kind must be personal or business")
    parsed = urlparse(url) if isinstance(url, str) else None
    if not parsed or parsed.scheme != "https" or parsed.netloc.lower() not in issuer_hosts[issuer]:
        raise ValueError(f"the page address is not on a known {issuer} host")
    return p


def _write(path, value, indent=1):
    with open(path, "w") as f:
        json.dump(value, f, indent=indent)
        f.write("\n")


def track(proposal, options, today, issue_number, paths, known_ids, issuer_hosts, currency_ids):
    """Start tracking a proposed card. Returns ("tracked", name), ("updated", name) or ("unchanged", name).

    options: the reply's key=value pairs (kind, name, currency), which override the proposal. A card already tracked
    is not added twice; a reply that gives a currency for one just sets it (a way to correct one). A card paid in points
    must be given a currency, and one paying free night awards cannot be tracked this way. Seeds the cached offer and fee from what the daily refresh read, so the card shows on the site
    complete right away, and adds the standard changelog line. The caller rebuilds data/ afterwards.
    """
    p = validate_proposal(dict(proposal), issuer_hosts)
    if options.get("kind"):
        p["kind"] = options["kind"].lower()
    if options.get("name"):
        p["name"] = options["name"]
    validate_proposal(p, issuer_hosts)
    currency = options.get("currency")
    if currency and currency not in currency_ids:
        raise ValueError(f"currency {currency!r} is not one this site can value (see the list in the issue)")

    tracked = _load(paths["tracked"])
    if p["id"] in tracked:
        if currency and tracked[p["id"]].get("currency") != currency:
            tracked[p["id"]]["currency"] = currency
            _write(paths["tracked"], tracked)
            return "updated", tracked[p["id"]]["name"]
        return "unchanged", tracked[p["id"]]["name"]
    if p["id"] in known_ids:
        raise ValueError(f"{p['id']} is already a card this site knows")
    # The catalog build (and a test that guards it) require these, so refuse now rather than commit something that fails.
    reads = p.get("reads_as") or {}
    if reads.get("freeNightAwards"):
        raise ValueError("this card's offer includes free night awards, which need a certificate value added by hand "
                         "(FREE_NIGHT_CERTIFICATE in registry.py), so it cannot be tracked from a reply yet")
    if reads.get("points") and not (currency or options.get("currency")):
        raise ValueError("this card's offer is paid in points or miles, so say which currency, for example "
                         "`/track currency=ultimate-rewards` (the ids are listed in the issue)")

    entry = {"issuer": p["issuer"], "name": p["name"], "kind": p["kind"], "url": normalize_url(p["url"]), "added": today}
    if currency:
        entry["currency"] = currency
    tracked[p["id"]] = entry
    _write(paths["tracked"], tracked)

    offer = p.get("offer")
    if offer and offer.get("text"):
        offers = _load(paths["offers"])
        offers[p["id"]] = {"seen": today, "text": offer["text"], **({"full_text": offer["full_text"]} if offer.get("full_text") else {})}
        _write(paths["offers"], offers)
    fee = p.get("fee")
    if fee and fee.get("amount") is not None:
        fees = _load(paths["fees"])
        fees[p["id"]] = float(fee["amount"])
        _write(paths["fees"], fees, indent=2)
        if fee.get("firstYearWaived"):
            waived = _load(paths["waived"])
            _write(paths["waived"], sorted(set(waived) | {p["id"]}))

    prepend_changelog_entry(paths["changelog"], today, added_cards_entry([p["name"]]))
    return "tracked", p["name"]


def ignore(proposal, today, paths, issuer_hosts):
    """Remember a candidate page the owner does not want, so detection never raises it again. Returns its name."""
    p = validate_proposal(dict(proposal), issuer_hosts)
    ignored = _load(paths["ignored"])
    ignored[normalize_url(p["url"])] = {"name": p["name"], "date": today}
    _write(paths["ignored"], ignored)
    return p["name"]
