#!/usr/bin/env python3
"""Build data/parsed-offers.json and docs/parsed-offers-review.md from the recorded offer texts.

Makes no network requests: it reads cardfinder/last_known_offers.json (written by card_offers.py) and
cardfinder/last_known_hotel_offers.json, and keeps the better offer of the two for each card (cardfinder/choose.py).
    python3 scripts/parse_offers.py
"""
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from cardfinder.build import build_parsed_offers  # noqa: E402
from cardfinder.effective import effective_offers  # noqa: E402
from cardfinder.registry import (CARDS, CASH_PAID_AS_POINTS, ISSUERS, LAST_KNOWN_HOTEL_OFFERS, LAST_KNOWN_OFFERS,  # noqa: E402
                                 NO_OFFER_CONFIRMED, REVIEWED_OK)


def money(x):
    return "-" if x is None else f"${x:,.0f}"


def main():
    offers = effective_offers(LAST_KNOWN_OFFERS, LAST_KNOWN_HOTEL_OFFERS, datetime.date.today())
    records = build_parsed_offers(CARDS, offers, confirmed_none=NO_OFFER_CONFIRMED, reviewed=REVIEWED_OK,
                                  cash_paid_as_points=CASH_PAID_AS_POINTS,
                                  stale_issuers={k: v.paused for k, v in ISSUERS.items() if v.paused},
                                  stale_since="2026-09-21")  # Amex was re-read on this date
    with open(os.path.join(ROOT, "data", "parsed-offers.json"), "w") as f:
        json.dump(records, f, indent=1)
    lines = ["# Parsed welcome offers (review)", "",
             "Built by scripts/parse_offers.py from the offer texts read on issuer pages. Rows marked REVIEW need a person to look.", "",
             "| Card | Points | Cash | Free nights | Min spend | Months | Extra tiers | Ceiling | Notes |", "|---|---|---|---|---|---|---|---|---|"]
    for r in records:
        if not r["hasWelcomeOffer"]:
            continue
        p = r["parsed"]
        tiers = "; ".join(f"{t['points']:,.0f} pts after {money(t['minSpend'])} in {t['windowMonths']} mo" for t in p["additionalTiers"] if t["points"]) or "-"
        pts = "-" if p["points"] is None else f"{p['points']:,.0f}"
        flag = ("REVIEW: " if r["needsReview"] else "") + ("STALE (issuer paused): " if r.get("stale") else "")
        lines.append(f"| {r['name']} | {pts} | {money(p['cashBack'])} | {p['freeNightAwards'] or '-'} | {money(p['minSpend'])} | {p['windowMonths'] or '-'} | {tiers} | {'yes' if p['ceiling'] else '-'} | {flag}{'; '.join(p['notes'])} |")
    none = [r["name"] for r in records if r["hasWelcomeOffer"] is False]
    unknown = [r["name"] for r in records if r["hasWelcomeOffer"] is None]
    lines += ["", f"## Cards with no welcome offer, confirmed by the site owner ({len(none)})", "", ", ".join(none),
              "", f"## Offer unknown: page never read ({len(unknown)})", "", ", ".join(unknown) or "none"]
    with open(os.path.join(ROOT, "docs", "parsed-offers-review.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{len(records)} cards: {sum(r['hasWelcomeOffer'] is True for r in records)} with offers, {len(none)} confirmed without, "
          f"{len(unknown)} unknown, {sum(r['needsReview'] for r in records)} need review")


if __name__ == "__main__":
    main()
