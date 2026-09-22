#!/usr/bin/env python3
"""Write data/cards.json from the registry, parsed offers and confirmed rules. No network."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cardfinder.catalog import build_catalog  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    catalog = build_catalog()
    with open(os.path.join(ROOT, "data", "cards.json"), "w") as f:
        json.dump(catalog, f, indent=1)
        f.write("\n")
    ranked = sum(1 for c in catalog if c["recommendable"] and "unrankedReason" not in c)
    unranked = [c["id"] for c in catalog if c.get("unrankedReason")]
    print(f"{len(catalog)} cards: {ranked} value-ranked, {len(unranked)} unranked, "
          f"{sum(1 for c in catalog if not c['recommendable'])} history-only")
    print("unranked:", ", ".join(unranked))


if __name__ == "__main__":
    main()
