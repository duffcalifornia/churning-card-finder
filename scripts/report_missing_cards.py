#!/usr/bin/env python3
"""Raise a GitHub issue for each card the daily refresh could not find (run by .github/workflows/refresh-offers.yml).

Reads the file scripts/refresh_offers.py wrote with --missing-file. For each missing card it opens one issue asking
whether the card is discontinued (the owner answers with a comment; see .github/workflows/card-status.yml), unless
one is already open or the owner recently answered "/still-active". An open issue whose card was read fine this run is
closed as resolved. Needs the gh CLI and a GH_TOKEN with issues: write.

Usage:  python3 scripts/report_missing_cards.py missing-cards.json [--dry-run]
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from cardfinder.missing import (LABEL_MISSING, LABEL_STILL_ACTIVE, issue_body, issue_title, plan_reports)  # noqa: E402


def gh(args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def report(doc, today, run=gh, dry_run=False):
    """Open and close issues as planned; returns (opened titles, closed issue numbers)."""
    issues = json.loads(run(["issue", "list", "--label", LABEL_MISSING, "--state", "all", "--limit", "200",
                             "--json", "number,body,state,labels,closedAt"]) or "[]")
    for issue in issues:
        issue["labels"] = [label["name"] for label in issue["labels"]]
    to_open, to_close = plan_reports(doc, issues, today)
    if dry_run:
        return [issue_title(m["name"]) for m in to_open], [n for n, _ in to_close]

    if to_open:
        run(["label", "create", LABEL_MISSING, "--color", "D93F0B", "--description", "The daily refresh could not find this card", "--force"])
        run(["label", "create", LABEL_STILL_ACTIVE, "--color", "0E8A16", "--description", "Owner confirmed the card can still be applied for", "--force"])
    for m in to_open:
        run(["issue", "create", "--title", issue_title(m["name"]), "--body", issue_body(m), "--label", LABEL_MISSING])
    for number, cid in to_close:
        run(["issue", "close", str(number), "--comment", f"`{cid}` was found again on {today}, so nothing needs deciding."])
    return [issue_title(m["name"]) for m in to_open], [n for n, _ in to_close]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("missing_file")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.exists(args.missing_file):
        print("No missing-cards file; nothing to report.")
        return 0
    with open(args.missing_file) as f:
        doc = json.load(f)
    try:
        opened, closed = report(doc, datetime.date.today().isoformat(), dry_run=args.dry_run)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Could not talk to GitHub through the gh CLI ({getattr(e, 'stderr', '') or e}). Is gh installed and GH_TOKEN set?", file=sys.stderr)
        return 1
    print(f"Opened {len(opened)} issue(s): {', '.join(opened) or '-'}; closed {len(closed)} resolved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
