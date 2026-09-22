#!/usr/bin/env python3
"""Find each tracked card's welcome offer and annual fee on the issuer's own site.

Maintainer tool, not part of the website. It never edits the catalog: review the report
and update the catalog by hand. Public pages show the public offer, not elevated or
targeted ones, and "as high as" figures are ceilings.

Defensive by design: if a card's URL has moved it is searched for in the issuer's
sitemap and listing pages before being reported missing, and every attempt is listed.
Issuers whose offers only appear after scripts run (Amex) use a headless browser
(Playwright) when installed; otherwise their offers are reported as unavailable, never
guessed from stale page data.

Usage:
    python3 scripts/card_offers.py --issuer chase
    python3 scripts/card_offers.py --issuer amex --card platinum --json out.json
    python3 scripts/card_offers.py --issuer all --no-render --delay 2

Exit code: 0 if every expected card was found, 2 if any could not be found.
Run the tests with: python3 -m unittest discover -s scripts/tests -t scripts
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cardfinder.cli import exit_code, format_report, run, select_cards, split_paused, to_json  # noqa: E402
from cardfinder.fetchers import CachingFetcher, HttpFetcher, RenderedFetcher  # noqa: E402
from cardfinder.registry import CARDS, ISSUERS  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--issuer", default="all", choices=["all"] + sorted(ISSUERS))
    ap.add_argument("--card", help="only cards whose id or name contains this text")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests (default 1)")
    ap.add_argument("--no-render", action="store_true", help="never use the headless browser")
    ap.add_argument("--json", metavar="PATH", help="also write results as JSON")
    ap.add_argument("--include-paused", action="store_true", help="also request issuers marked paused (only when told the block has cleared)")
    args = ap.parse_args(argv)

    cards = select_cards(CARDS, args.issuer, args.card)
    if not cards:
        sys.exit("No cards match.")
    if not args.include_paused:
        cards, paused = split_paused(cards, ISSUERS)
        for issuer, reason in paused.items():
            print(f"Skipping {issuer}: {reason}", file=sys.stderr)
        if not cards:
            sys.exit("Nothing to check: every selected issuer is paused (see above).")

    http = CachingFetcher(HttpFetcher(delay=args.delay))
    browser = rendered = None
    if not args.no_render and RenderedFetcher.available() and any(ISSUERS[c.issuer].render for c in cards):
        browser = RenderedFetcher()
        rendered = CachingFetcher(browser)
    try:
        results = run(cards, ISSUERS, http, rendered, all_cards=CARDS, on_result=lambda r: print(format_report([r]).split("\n\nSummary")[0], flush=True))
    finally:
        if browser:
            browser.close()

    print("\n" + format_report(results).split("\n\n")[-1])
    if args.json:
        with open(args.json, "w") as f:
            f.write(to_json(results))
        print(f"Wrote {args.json}")
    return exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
