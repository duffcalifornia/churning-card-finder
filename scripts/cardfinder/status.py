"""Applying the owner's answer to a "card not found" review issue.

Two answers exist: "/discontinued" (the card can no longer be applied for) and "/still-active" (it can; the scraper
just cannot find it). Only the first changes any data, and it does so by adding the card to
discontinued_cards.json, which registry.py already treats like any other not-tracked card.

Kept free of gh calls and of the registry itself (callers pass in what they need) so it can be tested on temp files.
"""
import json

from .changelog import prepend_changelog_entry, removed_cards_entry

COMMANDS = {"/discontinued": "discontinued", "/still-active": "still-active"}


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
