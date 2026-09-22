import json
import os
import unittest

from cardfinder.registry import CARDS

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def load(*parts):
    return json.load(open(os.path.join(ROOT, *parts)))


DATA = load("data", "marriott-matrix.json")
CARD_IDS = {c.id for c in CARDS}


class MarriottMatrix(unittest.TestCase):
    def test_matches_schema(self):
        import jsonschema
        jsonschema.validate(DATA, load("data", "schema", "marriott-matrix.schema.json"))

    def test_every_cell_uses_a_defined_rule(self):
        for prior, row in DATA["matrix"].items():
            for wanted, rule in row.items():
                self.assertIn(rule, DATA["rules"], (prior, wanted))

    def test_rows_are_the_prior_cards_and_columns_the_wanted_cards(self):
        priors = [c["id"] for c in DATA["cards"]]
        wanted = [c["id"] for c in DATA["cards"] if c["canBeWanted"]]
        self.assertEqual(list(DATA["matrix"]), priors)
        for row in DATA["matrix"].values():
            self.assertEqual(set(row), set(wanted))

    def test_wanted_cards_are_tracked_cards(self):
        for c in DATA["cards"]:
            if c["canBeWanted"]:
                self.assertIn(c["id"], CARD_IDS)

    def test_lifetime_blocks_are_only_the_amex_repeats(self):
        ever = {(p, w) for p, row in DATA["matrix"].items() for w, r in row.items() if r == "EVER"}
        self.assertEqual(ever, {
            ("amex-marriott-business", "amex-marriott-business"),
            ("amex-marriott-bevy", "amex-marriott-bevy"),
            ("amex-marriott-brilliant", "amex-marriott-brilliant"),
            ("amex-marriott-brilliant", "amex-marriott-bevy"),
        })

    def test_spot_checks_from_the_source(self):
        m = DATA["matrix"]
        self.assertEqual(m["chase-marriott-boundless"]["amex-marriott-bevy"], "30+90+24")
        self.assertEqual(m["amex-marriott-bonvoy"]["chase-marriott-bountiful"], "30+90+24")
        self.assertEqual(m["chase-marriott-bountiful"]["chase-marriott-bold"], "OK")
        self.assertEqual(m["chase-marriott-premier"]["chase-marriott-boundless"], "24")


if __name__ == "__main__":
    unittest.main()
