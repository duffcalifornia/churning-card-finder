"""Auto-generated CHANGELOG.md entries for the two things that change every day once the site is live: a card's
welcome offer, and a points program's cents-per-point value. Site owner's rule (2026-09-22): these get one
consistent phrasing each, every time, rather than a one-off sentence per run.

Pure functions only: no file or network access except prepend_changelog_entry, which does the one file write.
"""
import os
import re

# The few currencies with a real display name on file (data/currencies.json); a bank-transferable currency, not
# every program valuations.json prices. Anything else falls back to title-casing its id (see currency_label).
_KNOWN_CURRENCY_NAMES = {
    "cash": "Cash",
    "ultimate-rewards": "Chase Ultimate Rewards",
    "citi-thankyou": "Citi ThankYou Points",
    "capital-one-miles": "Capital One Miles",
    "amex-membership-rewards": "Amex Membership Rewards",
    "wells-fargo-rewards": "Wells Fargo Rewards",
    "bilt": "Bilt Rewards",
    "aeroplan": "Air Canada Aeroplan",
    "american-aadvantage": "American Airlines AAdvantage",
    "atmos-rewards": "Atmos Rewards",
    "air-france-klm-flying-blue": "Air France-KLM Flying Blue",
    "avianca-lifemiles": "Avianca LifeMiles",
    "avios": "Avios",
    "cathay-pacific-asia-miles": "Cathay Pacific Asia Miles",
    "delta-skymiles": "Delta SkyMiles",
    "frontier-bonus-miles": "Frontier Airlines Miles",
    "jetblue-trueblue": "JetBlue TrueBlue",
    "korean-skypass": "Korean Air SKYPASS",
    "miles-and-more": "Miles & More",
    "qantas-frequent-flyer": "Qantas Frequent Flyer",
    "southwest-rapid-rewards": "Southwest Rapid Rewards",
    "united-mileageplus": "United MileagePlus",
    "virgin-atlantic-flying-club": "Virgin Atlantic Flying Club",
    "best-western-rewards": "Best Western Rewards",
    "choice-privileges": "Choice Privileges",
    "hilton-honors": "Hilton Honors",
    "ihg-one-rewards": "IHG One Rewards",
    "marriott-bonvoy": "Marriott Bonvoy",
    "one-key": "Expedia One Key",
    "sonesta-travel-pass": "Sonesta Travel Pass",
    "world-of-hyatt": "World of Hyatt",
    "wyndham-rewards": "Wyndham Rewards",
    "amtrak-guest-rewards": "Amtrak Guest Rewards",
    "uber-cash": "Uber Cash",
    "default-bank-points": "the issuer's own generic travel points",
}


def currency_label(currency_id):
    """A display name for a valuations.json key. Known ones read correctly; an unmapped one (new to
    valuations.json) falls back to title-casing its id rather than blocking on a name nobody supplied yet —
    add it to _KNOWN_CURRENCY_NAMES above once you know the real one."""
    if currency_id in _KNOWN_CURRENCY_NAMES:
        return _KNOWN_CURRENCY_NAMES[currency_id]
    return currency_id.replace("-", " ").title()


def format_list(items):
    """"A", "A and B", or "A, B, and C" (Oxford comma). Caller sorts if order matters."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def offer_change_entry(old_offers, new_offers, card_names):
    """The changelog line for this run's offer-text changes, or None if nothing changed.

    old_offers/new_offers: the last_known_offers.json shape ({card_id: {"text": ..., ...}}), before and after
    a refresh. card_names: {card_id: display name}; an id missing from it (should not normally happen) falls
    back to the id itself rather than crashing or silently dropping the card from the list.
    """
    changed_ids = [
        cid for cid, entry in new_offers.items()
        if old_offers.get(cid, {}).get("text") != entry.get("text")
    ]
    if not changed_ids:
        return None
    names = sorted(card_names.get(cid, cid) for cid in changed_ids)
    return f"Updated the bonus offer for the following card(s): {format_list(names)}."


def valuation_change_entry(old_values, new_values):
    """The changelog line for a change in data/valuations.json's `values`, or None if nothing changed.

    Compares whole values (a flat cents-per-point number, or the {withUnlocker, withoutUnlocker} shape) so a
    change to either side of an unlocker-dependent currency is still caught. A program present in only one of
    the two snapshots (added or removed) counts as changed.
    """
    changed_ids = [cid for cid, v in new_values.items() if old_values.get(cid) != v]
    changed_ids += [cid for cid in old_values if cid not in new_values]
    if not changed_ids:
        return None
    names = sorted(set(currency_label(cid) for cid in changed_ids))
    return f"Updated the rankings to reflect changes to the value of {format_list(names)}."


_DATE_HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2})\s*$", re.M)


def prepend_changelog_entry(path, date_iso, line):
    """Add one bullet to CHANGELOG.md under today's date heading, creating that heading (at the top, since the
    file is newest-first) if today doesn't have one yet. A second call for the same date adds a second bullet
    to the same section instead of a duplicate heading.
    """
    with open(path) as f:
        content = f.read()

    heading = f"## {date_iso}"
    m = _DATE_HEADING.search(content)
    if m and m.group(1) == date_iso:
        # Today's section already exists (and is the first one, since the file is newest-first): add a bullet
        # at the end of it, i.e. right before the next "## " heading or end of file.
        section_start = m.end()
        next_heading = _DATE_HEADING.search(content, section_start)
        insert_at = next_heading.start() if next_heading else len(content)
        section = content[section_start:insert_at]
        new_section = section.rstrip("\n") + f"\n- {line}\n\n"
        content = content[:section_start] + new_section + content[insert_at:]
    else:
        # No section for today yet: insert a new one at the very top of the dated entries, i.e. right before
        # the first existing "## " heading (or at the end of the file if there are none yet).
        insert_at = m.start() if m else len(content)
        content = content[:insert_at] + f"{heading}\n- {line}\n\n" + content[insert_at:]

    with open(path, "w") as f:
        f.write(content)
