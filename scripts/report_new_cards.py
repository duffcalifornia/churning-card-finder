#!/usr/bin/env python3
"""Raise a GitHub issue for each new card the daily refresh detected (run by .github/workflows/refresh-offers.yml).

Reads the file scripts/refresh_offers.py wrote with --new-cards-file. Each candidate gets one issue (label card-new)
asking whether to track it; the owner replies /track or /ignore (see .github/workflows/card-status.yml). A candidate
that already has an open issue is skipped, and at most a handful are opened per run. Needs the gh CLI and a
GH_TOKEN with issues: write.

Usage:  python3 scripts/report_new_cards.py new-cards.json [--dry-run]
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from cardfinder.catalog import bonus_currency_ids  # noqa: E402
from cardfinder.newcards import issue_body, issue_title, plan_new_reports  # noqa: E402

LABEL = "card-new"


def gh(args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def report(doc, run=gh, dry_run=False, currency_ids=None):
    """Open the issues that are needed; returns the titles opened."""
    issues = json.loads(run(["issue", "list", "--label", LABEL, "--state", "open", "--limit", "200", "--json", "number,body,state"]) or "[]")
    to_open = plan_new_reports(doc, issues)
    if dry_run or not to_open:
        return [issue_title(c["name"]) for c in to_open]
    run(["label", "create", LABEL, "--color", "1D76DB", "--description", "The daily refresh found a card that is not tracked yet", "--force"])
    currency_ids = currency_ids if currency_ids is not None else bonus_currency_ids()
    for c in to_open:
        run(["issue", "create", "--title", issue_title(c["name"]), "--body", issue_body(c, currency_ids), "--label", LABEL])
    return [issue_title(c["name"]) for c in to_open]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("new_cards_file")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.exists(args.new_cards_file):
        print("No new-cards file; nothing to report.")
        return 0
    with open(args.new_cards_file) as f:
        doc = json.load(f)
    try:
        opened = report(doc, dry_run=args.dry_run)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Could not talk to GitHub through the gh CLI ({getattr(e, 'stderr', '') or e}). Is gh installed and GH_TOKEN set?", file=sys.stderr)
        return 1
    print(f"Opened {len(opened)} new-card issue(s): {', '.join(opened) or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
