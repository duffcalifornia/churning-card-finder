#!/usr/bin/env python3
"""Act on the owner's reply to a review issue (run by .github/workflows/card-status.yml).

Two kinds of issue, both opened by the daily refresh:
  "Card not found: X"  (label card-missing)  reply /discontinued or /still-active
  "New card found: X"  (label card-new)      reply /track [kind=... name="..." currency=...] or /ignore

Reads the issue body and the comment from the environment (never the command line: both are user-written text) and
writes what the workflow's later steps need to $GITHUB_OUTPUT, one line each:
    command       what was asked (or "none")
    changed       true if data files changed and must be tested and committed
    message       the commit message, when changed
    reply         the comment to post on the issue, if any
    close_reason  completed | not planned | (empty: leave the issue open)
    label         a label to add to the issue, if any
When data changed it also rebuilds data/parsed-offers.json and data/cards.json.

Usage (by hand, to try it on a card):
    COMMENT_BODY=/discontinued ISSUE_BODY='<!-- card-id: usbank-split -->' ISSUE_NUMBER=0 python3 scripts/apply_card_status.py
"""
import datetime
import os
import subprocess
import sys
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from cardfinder.catalog import bonus_currency_ids  # noqa: E402
from cardfinder.missing import card_id_from_body  # noqa: E402
from cardfinder.newcards import decode_proposal  # noqa: E402
from cardfinder.registry import CARDS, ISSUERS  # noqa: E402
from cardfinder.status import discontinue, ignore, parse_command, parse_options, track  # noqa: E402

CF = os.path.join(HERE, "cardfinder")
PATHS = {
    "discontinued": os.path.join(CF, "discontinued_cards.json"),
    "tracked": os.path.join(CF, "tracked_cards.json"),
    "ignored": os.path.join(CF, "ignored_cards.json"),
    "offers": os.path.join(CF, "last_known_offers.json"),
    "fees": os.path.join(CF, "last_known_fees.json"),
    "waived": os.path.join(CF, "last_known_fee_waived.json"),
    "changelog": os.path.join(ROOT, "CHANGELOG.md"),
}


def _output(**values):
    line = "".join(f"{k}={str(v).replace(chr(10), ' ')}\n" for k, v in values.items())
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(line)
    print(line, end="")


def _issuer_hosts():
    """The web hosts each issuer's own pages live on, taken from the registry: a proposal's page must be on one."""
    hosts = {}
    for c in CARDS:
        for u in c.urls:
            hosts.setdefault(c.issuer, set()).add(urlparse(u).netloc.lower())
    for name, cfg in ISSUERS.items():
        for u in cfg.listing_pages + cfg.sitemaps:
            hosts.setdefault(name, set()).add(urlparse(u).netloc.lower())
    return hosts


def _rebuild():
    # Fresh interpreters, like refresh_offers.py: this process already loaded the old data files.
    subprocess.run([sys.executable, os.path.join(HERE, "parse_offers.py")], check=True)
    subprocess.run([sys.executable, os.path.join(HERE, "build_cards.py")], check=True)


def _missing_flow(command, card_id, today, issue_number):
    names = {c.id: c.names[0] for c in CARDS}
    if card_id not in names:
        return dict(changed="false", reply=f"I do not recognise the card id `{card_id}` any more, so nothing was changed.")
    if command == "still-active":
        return dict(changed="false", label="still-active", close_reason="not planned",
                    reply=f"Noted: {names[card_id]} is still available. Its last known offer stays on the site, and it will not be raised again for 30 days.")
    done = discontinue(card_id, names, today, issue_number, PATHS)
    if not done:
        return dict(changed="false", close_reason="completed", reply="Nothing to change: this card is already removed.")
    return dict(changed="true", message=f"Remove {done}: can no longer be applied for", close_reason="completed",
                reply=f"Done. {done} is removed from the site and the changelog has a line for it. The site updates once the change deploys.")


def _new_card_flow(command, proposal, options, comment_body, today, issue_number):
    hosts = _issuer_hosts()
    if command == "ignore":
        name = ignore(proposal, today, PATHS, hosts)
        return dict(changed="true", message=f"Ignore {name}: not a card to track", close_reason="not planned",
                    reply=f"Okay, {name} will not be raised again.")
    known = {c.id for c in CARDS}
    outcome, name = track(proposal, options, today, issue_number, PATHS, known, hosts, set(bonus_currency_ids()))
    if outcome == "unchanged":
        return dict(changed="false", close_reason="completed", reply=f"Nothing to change: {name} is already tracked.")
    if outcome == "updated":
        return dict(changed="true", message=f"Set the points currency for {name}", close_reason="completed",
                    reply=f"Done. {name} now uses that points currency, so it can be ranked.")
    return dict(changed="true", message=f"Add {name}", close_reason="completed",
                reply=f"Done. {name} is now tracked, shown on the site with the offer and fee read today, and read every day from now on. "
                      "Any family, lifetime or cooldown rules for it still need adding by hand.")


def main():
    body = os.environ.get("COMMENT_BODY", "")
    command = parse_command(body)
    issue_body = os.environ.get("ISSUE_BODY", "")
    issue_number = os.environ.get("ISSUE_NUMBER", "?")
    today = datetime.date.today().isoformat()
    result = dict(command=command or "none", changed="false", message="", reply="", close_reason="", label="")

    card_id = card_id_from_body(issue_body)
    proposal = decode_proposal(issue_body)
    try:
        if not command:
            pass
        elif card_id and command in ("discontinued", "still-active"):
            result.update(_missing_flow(command, card_id, today, issue_number))
        elif proposal and command in ("track", "ignore"):
            result.update(_new_card_flow(command, proposal, parse_options(body), body, today, issue_number))
        elif card_id or proposal:
            valid = "`/discontinued` or `/still-active`" if card_id else "`/track` or `/ignore`"
            result.update(reply=f"`/{command}` does not apply to this issue. Reply with {valid}.")
        if result["changed"] == "true":
            _rebuild()
    except ValueError as e:
        result.update(changed="false", message="", label="", close_reason="", reply=f"Could not do that: {e}. Nothing was changed.")
    _output(**result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
