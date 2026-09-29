#!/usr/bin/env python3
"""Act on the owner's reply to a "Card not found" issue (run by .github/workflows/card-status.yml).

Reads the issue body and the comment from the environment (never from the command line, since both are
user-written text), and writes what it decided to $GITHUB_OUTPUT for the workflow's later steps:
    command    discontinued | still-active | none
    card_id    the card the issue is about
    card_name  its display name
    changed    true if data files were changed (only for a new /discontinued)

For /discontinued it edits scripts/cardfinder/discontinued_cards.json, the cached offer/fee files and CHANGELOG.md,
then rebuilds data/parsed-offers.json and data/cards.json. For /still-active it changes nothing; the workflow labels
and closes the issue.

Usage (by hand, to try it on a card):
    COMMENT_BODY=/discontinued ISSUE_BODY='<!-- card-id: usbank-split -->' ISSUE_NUMBER=0 python3 scripts/apply_card_status.py
"""
import datetime
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from cardfinder.missing import card_id_from_body  # noqa: E402
from cardfinder.registry import CARDS  # noqa: E402
from cardfinder.status import discontinue, parse_command  # noqa: E402

CF = os.path.join(HERE, "cardfinder")
PATHS = {
    "discontinued": os.path.join(CF, "discontinued_cards.json"),
    "offers": os.path.join(CF, "last_known_offers.json"),
    "fees": os.path.join(CF, "last_known_fees.json"),
    "waived": os.path.join(CF, "last_known_fee_waived.json"),
    "changelog": os.path.join(ROOT, "CHANGELOG.md"),
}


def _output(**values):
    line = "".join(f"{k}={v}\n" for k, v in values.items())
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(line)
    print(line, end="")


def main():
    command = parse_command(os.environ.get("COMMENT_BODY", ""))
    card_id = card_id_from_body(os.environ.get("ISSUE_BODY", ""))
    names = {c.id: c.names[0] for c in CARDS}
    if not command or not card_id or card_id not in names:
        _output(command="none", card_id=card_id or "", card_name="", changed="false")
        return 0
    if command == "still-active":
        _output(command=command, card_id=card_id, card_name=names[card_id], changed="false")
        return 0

    today = datetime.date.today().isoformat()
    done = discontinue(card_id, names, today, os.environ.get("ISSUE_NUMBER", "?"), PATHS)
    if done:
        # Fresh interpreters, like refresh_offers.py: the registry already loaded the old discontinued list here.
        subprocess.run([sys.executable, os.path.join(HERE, "parse_offers.py")], check=True)
        subprocess.run([sys.executable, os.path.join(HERE, "build_cards.py")], check=True)
    _output(command=command, card_id=card_id, card_name=names[card_id], changed="true" if done else "false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
