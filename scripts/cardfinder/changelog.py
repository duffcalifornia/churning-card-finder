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


# The fields of a parsed-offer record (cardfinder.build.build_parsed_offers) that represent an actual dollar
# value. Deliberately excludes `notes` (scraper commentary that can vary without the offer itself changing) and
# metadata like `seenOn`/`sourceText`/`needsReview`/`stale` - none of those affect what the site shows or ranks.
_VALUE_FIELDS = ("kind", "points", "cashBack", "freeNightAwards", "minSpend", "windowMonths", "additionalTiers", "ceiling", "displayedAsCash")


def _offer_value(record):
    """The comparable value of one parsed-offer record: None if the card has no recorded offer at all (so gaining
    or losing a recorded offer counts as a change), or a tuple of just the value-bearing fields otherwise."""
    if not record or not record.get("hasWelcomeOffer"):
        return None
    parsed = record.get("parsed") or {}
    return tuple(parsed.get(f) for f in _VALUE_FIELDS)


def offer_change_entry(old_records, new_records, card_names):
    """The changelog line for this run's actual offer-value changes, or None if nothing changed.

    old_records/new_records: {card_id: parsed-offer-record} (data/parsed-offers.json's shape, keyed by card id),
    before and after a refresh - not the raw last_known_offers.json text. Comparing the *parsed* offer, not the
    scraped page text byte-for-byte, matters because an issuer's own page can reformat between reads (an en dash
    swapped for a hyphen, "Annual Fee" recapitalized, unrelated marketing copy trimmed) with the actual points,
    minimum spend and fee never moving at all; comparing raw text flags that as a bonus change it never was.
    card_names: {card_id: display name}; an id missing from it (should not normally happen) falls back to the id
    itself rather than crashing or silently dropping the card from the list.
    """
    changed_ids = [
        cid for cid, new in new_records.items()
        if _offer_value(old_records.get(cid)) != _offer_value(new)
    ]
    if not changed_ids:
        return None
    names = sorted(card_names.get(cid, cid) for cid in changed_ids)
    return f"Updated the bonus offer for the following card(s): {format_list(names)}."


def fee_change_entry(old_fees, new_fees, old_waived, new_waived, card_names):
    """The changelog line for a run where a card's offer text was unchanged but its annual fee (the amount, or
    whether the first year is waived) moved — either one changes the net value ranking on its own. None if
    nothing did. Deliberately keeps "card" singular in the template even for more than one card (owner's call,
    2026-09-22: expected to be rare enough that singular reads fine regardless of count).
    """
    changed_ids = {cid for cid, amount in new_fees.items() if old_fees.get(cid) != amount}
    changed_ids |= set(old_waived) ^ set(new_waived)  # newly waived, or (not expected from an automated run) un-waived
    if not changed_ids:
        return None
    names = sorted(card_names.get(cid, cid) for cid in changed_ids)
    return f"Updated the net value rankings to reflect changes to the annual fee on the following card: {format_list(names)}."


def added_cards_entry(names):
    """The changelog line for cards newly tracked and shown on the site. A brand-new card also looks like an "offer
    changed" and "fee changed" to the daily diff (it goes from no recorded offer to one), so callers that add a card
    log this line instead of those two."""
    return f"Added the following card(s): {format_list(sorted(names))}."


def removed_cards_entry(names):
    """The changelog line for cards taken off the site because they can no longer be applied for (site owner,
    2026-09-29). Same one-phrasing-every-time rule as the offer and fee lines above."""
    return f"Removed the following card(s) because they can no longer be applied for: {format_list(sorted(names))}."


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
