#!/usr/bin/env python3
"""Read live offers and fees, fold successful reads into the last-known cache, and rebuild the site's data.

Runs the same checker as card_offers.py, then (unless --dry-run) writes its successful reads into
cardfinder/last_known_offers.json, last_known_fees.json and last_known_fee_waived.json, and rebuilds
data/parsed-offers.json and data/cards.json from them, so a fresh run actually changes what the site shows.
Never touches a paused issuer (Amex) unless told --include-paused, same as card_offers.py.

A card this run could not read keeps its last known value: nothing is ever guessed. Cards flagged
needsReview in data/parsed-offers.json (an ambiguous parse, a struck-through pair, and so on) are still
built into data/cards.json as today's best reading, same as a manual run always has; that flag is there
for a person reviewing the diff to notice, not a gate that blocks the update.

Usage:
    python3 scripts/refresh_offers.py                        # full run, all non-paused issuers
    python3 scripts/refresh_offers.py --dry-run --delay 3     # check and report only, write nothing

Exit code: 0 if every expected card was found, 2 if any could not be (this is also what a circuit-breaker
trip from an issuer looks like: its remaining cards come back "skipped", which counts as not read, not
as a hard failure by itself, but genuinely expected cards going missing does; see cardfinder/cli.py).
Run the tests with: python3 -m unittest discover -s scripts/tests -t scripts
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from cardfinder.changelog import fee_change_entry, offer_change_entry, prepend_changelog_entry  # noqa: E402
from cardfinder.cli import exit_code, format_report, run, select_cards, split_paused  # noqa: E402
from cardfinder.fetchers import CachingFetcher, HttpFetcher, RenderedFetcher  # noqa: E402
from cardfinder.refresh import merge_last_known  # noqa: E402
from cardfinder.registry import CARDS, ISSUERS, LAST_KNOWN_FEE_WAIVED, LAST_KNOWN_FEES, LAST_KNOWN_OFFERS  # noqa: E402

OFFERS_PATH = os.path.join(HERE, "cardfinder", "last_known_offers.json")
FEES_PATH = os.path.join(HERE, "cardfinder", "last_known_fees.json")
WAIVED_PATH = os.path.join(HERE, "cardfinder", "last_known_fee_waived.json")
CHANGELOG_PATH = os.path.join(ROOT, "CHANGELOG.md")


def _write_cache_files(offers, fees, waived):
    # Deliberately NOT sort_keys: these files already happen to be alphabetical because every entry so far
    # was added that way, but sort_keys=True would re-sort and reorder every unchanged entry's own fields
    # (seen/text/full_text) on every write, turning a one-card update into a diff touching the whole file.
    # merge_last_known preserves each dict's existing order and only touches entries that actually changed.
    with open(OFFERS_PATH, "w") as f:
        json.dump(offers, f, indent=1)
        f.write("\n")
    with open(FEES_PATH, "w") as f:
        json.dump(fees, f, indent=2)
        f.write("\n")
    with open(WAIVED_PATH, "w") as f:
        json.dump(sorted(waived), f, indent=1)
        f.write("\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--issuer", default="all", choices=["all"] + sorted(ISSUERS))
    ap.add_argument("--card", help="only cards whose id or name contains this text")
    ap.add_argument("--delay", type=float, default=2.0, help="seconds between requests (default 2, politer than the manual default since this runs unattended)")
    ap.add_argument("--no-render", action="store_true", help="never use the headless browser")
    ap.add_argument("--include-paused", action="store_true", help="also request issuers marked paused (only when told the block has cleared)")
    ap.add_argument("--dry-run", action="store_true", help="check and report only; write nothing, rebuild nothing")
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
        results = run(cards, ISSUERS, http, rendered, all_cards=CARDS,
                      on_result=lambda r: print(format_report([r]).split("\n\nSummary")[0], flush=True))
    finally:
        if browser:
            browser.close()

    print("\n" + format_report(results).split("\n\n")[-1])

    if args.dry_run:
        print("Dry run: nothing written.")
        return exit_code(results)

    today = datetime.date.today().isoformat()
    new_offers, new_fees, new_waived = merge_last_known(results, LAST_KNOWN_OFFERS, LAST_KNOWN_FEES, LAST_KNOWN_FEE_WAIVED, today)
    _write_cache_files(new_offers, new_fees, new_waived)

    # Site owner's rule (2026-09-22): every offer or fee change gets logged this one consistent way each, since
    # these will be the most common changelog entries by far once the site is past its initial development
    # phase. The two are independent facts and both can fire for the same card in the same run.
    card_names = {c.id: c.names[0] for c in CARDS}
    for entry in (
        offer_change_entry(LAST_KNOWN_OFFERS, new_offers, card_names),
        fee_change_entry(LAST_KNOWN_FEES, new_fees, LAST_KNOWN_FEE_WAIVED, new_waived, card_names),
    ):
        if entry:
            prepend_changelog_entry(CHANGELOG_PATH, today, entry)
            print(f"Changelog: {entry}")
    print(f"Wrote {OFFERS_PATH}, {FEES_PATH}, {WAIVED_PATH}")

    # Rebuild the data the site actually reads, as real separate processes (not `import parse_offers` in this
    # same process): cardfinder.registry loads the cache files above into module-level constants at import
    # time, and this process already imported it once before writing them, so an in-process `import` here
    # would silently rebuild from the stale, pre-write data still cached in sys.modules. A fresh interpreter
    # per script reads the files as they are on disk right now, which is what a human running them by hand,
    # one at a time, has always gotten.
    subprocess.run([sys.executable, os.path.join(HERE, "parse_offers.py")], check=True)
    subprocess.run([sys.executable, os.path.join(HERE, "build_cards.py")], check=True)

    return exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
