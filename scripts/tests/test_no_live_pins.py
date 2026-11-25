"""Guard: tests must not pin what the daily refresh reads from issuer pages.

Every failure of the "Refresh card offers" job since 2026-10-20 (and the 2026-11-05/06 pair, and every daily failure
from 2026-11-12) was a test asserting a specific card's live offer, fee or fee waiver, e.g. "Aeroplan has a second
spend tier", which the issuer then changed. The refresh rebuilds data/ from the live pages and runs the suite against
it, so such a test fails the job the day the offer moves, and because a failing suite blocks the data commit the stale
data and the failure then repeat daily until someone edits the test.

Tests may check the code against a fixed offer (build it inline), or check every card against its own parsed offer.
They may not name a single card and a scraped field. If this test fails, rewrite the flagged line that way. Static
registry facts (bonusRules, family, currency, bonusTypes, reportsToPersonal, chargeCard) are not scraped and are fine.
"""
import glob
import os
import re
import unittest

HERE = os.path.dirname(__file__)

# Fields filled in from issuer pages on every run.
SCRAPED = ("welcomeBonus", "typicalMinSpend", "annualFee", "firstYearFeeWaived", "recommendable", "additionalTiers")
FIELDS = "|".join(SCRAPED)
PATTERNS = [
    re.compile(r'BY_ID\["[a-z0-9-]+"\](?:\.get\()?\s*\[?\(?\s*"(?:%s)"' % FIELDS),   # BY_ID["card"]["welcomeBonus"]
    re.compile(r'"(?:%s)"\s*,\s*BY_ID\["[a-z0-9-]+"\]' % FIELDS),                     # assertNotIn("typicalMinSpend", BY_ID["card"])
    re.compile(r'\b(?:OFFERS|offers)\["[a-z0-9-]+"\]\["(?:parsed|sourceText)"\]'),    # OFFERS["card"]["parsed"]
]
# Tests that name a card on purpose, with the reason. Keep this empty if at all possible.
ALLOWED = {}


class NoLivePins(unittest.TestCase):
    def test_no_test_names_one_card_and_a_scraped_field(self):
        found = []
        for path in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
            name = os.path.basename(path)
            if name == os.path.basename(__file__):
                continue
            for n, line in enumerate(open(path, encoding="utf-8"), 1):
                if line.lstrip().startswith("#"):
                    continue
                if any(p.search(line) for p in PATTERNS) and (name, line.strip()) not in ALLOWED:
                    found.append(f"{name}:{n}: {line.strip()}")
        self.assertEqual(found, [], "These lines pin a live, scraped value to one card; use a fixed offer or check every "
                                    "card against its own parsed offer (see this file's docstring):\n" + "\n".join(found))


if __name__ == "__main__":
    unittest.main()
