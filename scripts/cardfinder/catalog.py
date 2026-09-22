"""Assemble data/cards.json from the registry, the parsed offers and the confirmed rules.

Everything here is derived from recorded, owner-confirmed facts (docs/rule-audit.md): nothing is guessed at
build time, and a card that cannot be valued is marked unranked instead of being given a made-up value.
"""
import json
import os

from .registry import (CARDS, CARD_CURRENCY, FREE_NIGHT_CERTIFICATE, LAST_KNOWN_FEES, LAST_KNOWN_FEE_WAIVED,
                       OWNER_FEES, UNVALUED)

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
FEES_VERIFIED_ON = "2026-09-20"     # the issuer fee reads
RULES_CONFIRMED_ON = "2026-09-21"   # history-only cards exist only because a confirmed rule names them


def _load(*parts):
    with open(os.path.join(ROOT, *parts)) as f:
        return json.load(f)


# Cards that are in the catalog only because a rule refers to them (history list), not to be recommended.
# (id, name, issuer, kind)
HISTORY_ONLY = [
    ("chase-ritz-carlton", "Chase Ritz-Carlton Rewards Credit Card", "chase", "personal"),
    ("chase-marriott-bonvoy-45", "Chase Marriott Bonvoy Credit Card ($45)", "chase", "personal"),
    ("chase-marriott-premier", "Chase Marriott Bonvoy Premier Credit Card", "chase", "personal"),
    ("chase-marriott-business-45", "Chase Marriott Bonvoy Business Credit Card ($45)", "chase", "business"),
    ("chase-marriott-premier-plus-business", "Chase Marriott Bonvoy Premier Plus Business Credit Card", "chase", "business"),
    ("amex-marriott-bonvoy", "Marriott Bonvoy American Express Card", "amex", "personal"),
    ("citi-premier", "Citi Premier Card", "citi", "personal"),
    ("citi-strata-student", "Citi Strata Student Card", "citi", "personal"),
    ("amex-delta-options", "Delta SkyMiles Options American Express Card", "amex", "personal"),
    ("amex-hilton-ascend", "Hilton Honors American Express Ascend Card", "amex", "personal"),
]
# Cards the registry marks as not offered, kept because a family rule refers to them.
KEEP_AS_HISTORY_ONLY = {"amex-cash-magnet"}

# Family tiers, lowest first (docs/rule-audit.md Section J for Amex, K8 for Capital One).
FAMILIES = {
    "mr-personal": {"amex-gold": 1, "amex-platinum": 2, "schwab-platinum": 2, "morganstanley-platinum": 2},
    "cash": {"amex-blue-cash-everyday": 1, "amex-cash-magnet": 2, "amex-blue-cash-preferred": 2,
             "morganstanley-blue-cash-preferred": 2},
    "delta-personal": {"amex-delta-blue": 1, "amex-delta-options": 2, "amex-delta-gold": 3,
                       "amex-delta-platinum": 4, "amex-delta-reserve": 5},
    "delta-business": {"amex-delta-gold-business": 1, "amex-delta-platinum-business": 2,
                       "amex-delta-reserve-business": 3},
    "hilton": {"amex-hilton-surpass": 1, "amex-hilton-ascend": 2},
    "venture": {"capone-ventureone": 1, "capone-venture": 2, "capone-venture-x": 3},
}
FAMILY_OF = {cid: {"id": fam, "tier": tier} for fam, cards in FAMILIES.items() for cid, tier in cards.items()}

# Amex cards that are charge cards (count toward the 10 charge card limit). List confirmed by the site owner, 2026-09-21.
CHARGE_CARDS = {"amex-platinum", "amex-gold", "amex-business-platinum", "amex-business-gold", "amex-business-green",
                "schwab-platinum", "morganstanley-platinum"}

# Business cards that do not report to personal credit even though the issuer's others do (A2, A21).
BUSINESS_NOT_REPORTING = {"capone-spark-cash-plus", "capone-venture-x-business"}
REPORTING_BUSINESS_ISSUERS = {"capone", "discover"}

LIFETIME_CARDS = {"chase-sapphire-preferred", "chase-sapphire-reserve", "chase-sapphire-reserve-business",
                  "chase-ink-unlimited", "chase-ink-premier", "chase-ink-cash", "chase-ink-preferred",
                  "citi-strata", "citi-strata-premier", "citi-strata-elite"}
LIFETIME_ALSO_BLOCKED_BY = {"citi-strata": ["citi-strata-student"], "citi-strata-premier": ["citi-premier"]}
SOUTHWEST_PERSONAL = {"chase-southwest-plus", "chase-southwest-premier", "chase-southwest-priority"}
IHG_PERSONAL = {"chase-ihg-premier", "chase-ihg-traveler"}

_CURRENCY_BONUS_TYPES = {"default-bank-points": ["cashback"], "frontier-bonus-miles": ["airline"],
                         "miles-and-more": ["airline"]}


def reports_to_personal(card_id, issuer, kind):
    if kind == "personal":
        return True
    return issuer in REPORTING_BUSINESS_ISSUERS and card_id not in BUSINESS_NOT_REPORTING


def bonus_rules(card_id, issuer, kind, matrix_wanted):
    r = {}
    if card_id in matrix_wanted:
        r["marriottMatrixKey"] = card_id
    if card_id in LIFETIME_CARDS or issuer in ("amex", "schwab", "morganstanley"):
        # every Amex card carries lifetime language by default (owner, 2026-09-21), Marriott ones too
        r["onceInLifetime"] = True
        if card_id in LIFETIME_ALSO_BLOCKED_BY:
            r["lifetimeAlsoBlockedBy"] = LIFETIME_ALSO_BLOCKED_BY[card_id]
    elif card_id in matrix_wanted:
        pass   # Chase Marriott cards follow the matrix alone
    elif card_id in SOUTHWEST_PERSONAL:
        r.update(cooldownMonths=24, cooldownBasis="bonus", cooldownFamily="southwest-personal", blockedWhileHeld=True)
    elif card_id in IHG_PERSONAL:
        r.update(cooldownMonths=24, cooldownBasis="bonus", cooldownFamily="ihg-personal", blockedWhileHeld=True)
    elif issuer == "chase":
        r.update(cooldownMonths=24, cooldownBasis="bonus", blockedWhileHeld=True)
    elif issuer == "citi":
        r.update(cooldownMonths=48, cooldownBasis="bonus")
    elif issuer == "capone" and kind == "personal":
        r.update(cooldownMonths=48, cooldownBasis="bonus")
    elif issuer == "boa" and kind == "personal":
        r.update(cooldownMonths=24, cooldownBasis="held")
    elif issuer == "barclays":
        r["blockedWhileHeld"] = True   # US Bank's "exact card already open" rule is outdated or YMMV (owner, 2026-09-21)
    return r


def _bonus_types(currency, programs, currencies):
    if currency == "cash":
        return ["cashback"]
    if currency in programs:
        return [programs[currency]["kind"]]
    if currency in currencies:
        return ["transferable"] + (["cashback"] if currencies[currency].get("cashBackRedemption") == "good" else [])
    return list(_CURRENCY_BONUS_TYPES[currency])


def _welcome_bonus(parsed, fnc_values, card_id):
    b = {}
    if parsed.get("points"):
        b["points"] = parsed["points"]
    if parsed.get("cashBack"):
        b["cashBack"] = parsed["cashBack"]
    if parsed.get("displayedAsCash"):
        b["displayedAsCash"] = parsed["displayedAsCash"]
    if parsed.get("freeNightAwards"):
        b["freeNights"] = parsed["freeNightAwards"]
        b["otherValue"] = parsed["freeNightAwards"] * fnc_values[FREE_NIGHT_CERTIFICATE[card_id]]
    tiers = [{k: v for k, v in {"points": t["points"], "cashBack": t["cashBack"], "minSpend": t["minSpend"],
                                "windowMonths": t["windowMonths"]}.items() if v is not None}
             for t in parsed.get("additionalTiers") or []]
    if tiers:
        b["additionalTiers"] = tiers
    if parsed.get("ceiling"):
        b["ceiling"] = True
    return b


def build_catalog():
    currencies = {c["id"]: c for c in _load("data", "currencies.json")}
    programs = {p["id"]: p for p in _load("data", "programs.json")}
    valuations = _load("data", "valuations.json")
    offers = {r["cardId"]: r for r in _load("data", "parsed-offers.json")}
    matrix = _load("data", "marriott-matrix.json")
    matrix_wanted = {c["id"] for c in matrix["cards"] if c["canBeWanted"]}
    unlockers = {cid for cur in currencies.values() for cid in cur["unlockerCards"]}

    catalog = []
    for card in CARDS:
        if not card.expected and card.id not in KEEP_AS_HISTORY_ONLY:
            continue
        offer = offers.get(card.id)
        has_offer = bool(offer and offer.get("hasWelcomeOffer"))
        entry = {"id": card.id, "name": card.names[0], "issuer": card.issuer, "kind": card.kind,
                 "recommendable": has_offer}
        fee = LAST_KNOWN_FEES.get(card.id)
        if fee is None and card.id in OWNER_FEES:
            fee = OWNER_FEES[card.id][0]
        if fee is not None:
            entry["annualFee"] = fee
        if card.id in LAST_KNOWN_FEE_WAIVED or (card.id in OWNER_FEES and OWNER_FEES[card.id][1]):
            entry["firstYearFeeWaived"] = True
        entry["reportsToPersonal"] = reports_to_personal(card.id, card.issuer, card.kind)
        if card.id in CHARGE_CARDS:
            entry["chargeCard"] = True
        if has_offer:
            parsed = offer["parsed"]
            if card.id in UNVALUED:
                entry["unrankedReason"] = UNVALUED[card.id]
            elif parsed["kind"] != "standard":
                entry["unrankedReason"] = "; ".join(parsed["notes"]) or "The offer has no fixed amount."
            else:
                currency = CARD_CURRENCY[card.id] if parsed.get("points") else "cash"
                entry["currency"] = currency
                if currency in programs:
                    entry["coBrandedProgram"] = currency
                entry["bonusTypes"] = _bonus_types(currency, programs, currencies)
            if parsed["kind"] == "standard":
                entry["welcomeBonus"] = _welcome_bonus(parsed, valuations["freeNightCertificates"], card.id)
                if parsed.get("minSpend") and parsed.get("windowMonths"):
                    entry["typicalMinSpend"] = {"amount": parsed["minSpend"], "months": parsed["windowMonths"]}
        if card.id in unlockers:
            entry["unlocksTransfers"] = True
        if card.id.startswith("citi-aadvantage"):
            entry["requiresAAAccess"] = True
        if card.id in FAMILY_OF:
            entry["family"] = FAMILY_OF[card.id]
        rules = bonus_rules(card.id, card.issuer, card.kind, matrix_wanted)
        if rules:
            entry["bonusRules"] = rules
        if card.urls:
            entry["sourceUrl"] = card.urls[0]
        entry["verifiedOn"] = offer["seenOn"] if has_offer else FEES_VERIFIED_ON
        catalog.append(entry)

    for cid, name, issuer, kind in HISTORY_ONLY:
        entry = {"id": cid, "name": name, "issuer": issuer, "kind": kind, "recommendable": False,
                 "reportsToPersonal": reports_to_personal(cid, issuer, kind), "verifiedOn": RULES_CONFIRMED_ON}
        if cid in FAMILY_OF:
            entry["family"] = FAMILY_OF[cid]
        catalog.append(entry)

    # The history-only Cash Magnet is in the registry as not offered; give it the same shape.
    for entry in catalog:
        if entry["id"] in KEEP_AS_HISTORY_ONLY:
            entry["recommendable"] = False
    return catalog
