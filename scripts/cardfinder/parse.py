"""Turn a welcome-offer sentence into numbers: bonus points, cash, free nights, minimum spend, time window.

Rules (from the site owner, 2026-09-20):
  - authorized-user and employee-card bonuses do not count;
  - "spend X for Y, then earn 2 points per dollar on the next $Z" counts only the first part;
  - "spend A in B for C, then spend X in Y for an additional Z" keeps Z as a separate tier, so the engine can
    include it when the household's spending meets the first threshold;
  - gift cards and statement credits count as cash at face value;
  - free night awards are counted, not valued (the catalog assigns their value);
  - PQP and other perks are not valued; an old/new pair uses the second number and is flagged for review.
Anything the parser cannot read is left empty and explained in `notes`; it never guesses.
"""
import re
from dataclasses import dataclass, field, asdict
from typing import List, Optional

_NUM = r"\d{1,3}(?:,\d{3})+"
_UNIT = r"(?:[A-Za-z]*[Pp]oints?|[Mm]iles|Avios)"
_WORDS = r"(?:[A-Za-z-]+\s+)"


def _n(s):
    return float(s.replace(",", ""))


def _months(amount, unit):
    n = int(amount)
    return max(1, round(n / 30)) if unit.lower().startswith("day") else n


@dataclass
class Tier:
    points: Optional[float] = None
    cash_back: Optional[float] = None
    min_spend: Optional[float] = None
    window_months: Optional[int] = None
    note: str = ""


@dataclass
class ParsedOffer:
    kind: str = "standard"                     # standard, match (no fixed amount), unparsed
    points: Optional[float] = None
    cash_back: Optional[float] = None
    free_night_awards: int = 0
    min_spend: Optional[float] = None
    window_months: Optional[int] = None
    additional_tiers: List[Tier] = field(default_factory=list)
    ceiling: bool = False                      # "as high as" / "up to": a maximum, not what everyone gets
    notes: List[str] = field(default_factory=list)   # anything a person should look at

    def to_dict(self):
        return asdict(self)


_STRUCK = re.compile(rf"({_NUM})\s+(?:strike\s+through\s+|old\s+bonus\s+)?({_NUM})\s+(?:new\s+bonus\s+)?(?:bonus\s+)?{_UNIT}", re.I)
_POINTS = re.compile(rf"(?<![\d$,.])({_NUM})\s+(?:[A-Za-z]+\s+){{0,4}}?{_UNIT}\b", re.I)
_CASH = re.compile(
    rf"\$({_NUM}|\d+)\s+{_WORDS}{{0,3}}?(?:cash\s*back|cash\s+bonus|cash\s+rewards|statement\s+credits?|gift\s+card|egift|bonus|credits?|rewards|cash)\b", re.I)
_BEFORE_A_SPEND_AMOUNT = re.compile(
    r"(?:spend|spending|spent|after|totaling|least|make|makes|making|when|once|than|of|for|"
    r"redeemed\s+for(?:\s+an?)?|equal\s+to|worth|value\s+of|toward|that(?:'s|\s+is))\s*$", re.I)
_REDEMPTION_VALUE = re.compile(r"\s*(?:redemption\s+)?value\b", re.I)
_FREE_NIGHT = re.compile(r"\b(\d+|an?|one|two|three|four|five)\s+Free\s+Night\s+(?:Award|Reward|Certificate)s?", re.I)
_WORD_NUMBERS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
_SPEND = [
    re.compile(r"(?:after|when|once)\s+(?:you\s+)?(?:spend|spending|make|making|use\s+your\s+new\s+card\s+to\s+make)\s+(?:at\s+least\s+)?\$(" + _NUM + r"|\d+)", re.I),
    re.compile(r"after\s+\$(" + _NUM + r"|\d+)\s+in\s+(?:net\s+)?purchases", re.I),
    re.compile(r"Just\s+spend\s+\$(" + _NUM + r"|\d+)", re.I),
    re.compile(r"To\s+qualify,\s+spend\s+\$(" + _NUM + r"|\d+)", re.I),
    re.compile(r"totaling\s+(?:at\s+least\s+)?\$(" + _NUM + r"|\d+)", re.I),
]
_WINDOW = [
    re.compile(r"(?:in|within)\s+(?:the\s+|your\s+)?first\s+(\d+)\s+(months?|days?)", re.I),
    re.compile(r"within\s+(\d+)\s+(months?|days?)", re.I),
]
_SECOND_TIER = re.compile(
    rf"(?:Plus,?|and\s+also\s+earn|also\s+earn|then\s+earn)\s+({_NUM})\s+(?:[A-Za-z]+\s+){{0,3}}?{_UNIT}\s+after\s+(?:you\s+)?(?:spend|spending)\s+\$({_NUM}|\d+)"
    rf"(?P<tail>[^.]{{0,100}})", re.I)
# "If you spend a total of $X within/in the first Y months, earn/get an additional Z <unit>": the spend clause comes
# before the earn amount, and "a total of" marks the spend as cumulative from account opening, not on top of the
# first tier's spend (contrast _SECOND_TIER's "Plus, Z after you spend $X", where X is on top of the first tier).
_SECOND_TIER_TOTAL = re.compile(
    rf"(?:if\s+you\s+)?spend(?:ing)?\s+a\s+total\s+of\s+\$({_NUM}|\d+)\s+(?:within|in)\s+(?:the\s+)?(?:first\s+)?(\d+)\s+(months?|days?)"
    rf"[^.]{{0,30}}?,?\s*(?:earn|get)\s+(?:an\s+additional\s+)?({_NUM})\s+(?:[A-Za-z]+\s+){{0,3}}?{_UNIT}", re.I)
_MATCH = re.compile(r"match\s+(?:all\s+)?(?:of\s+)?the\s+(?:cash\s+back|miles)", re.I)
_COMPANION = re.compile(r"Companion\s+(?:Fare|Award|Certificate)|Comfort\s+Flight\s+Certificate", re.I)


# A statement credit counts only when it is general. This is the clause that earns it, e.g.
# "... after you spend $500 on eligible airline purchases": what follows "on/in/at" says what must be bought.
_CREDIT_TRIGGER = re.compile(
    r"(?:after|when|once)\s+(?:you\s+)?(?:spend|spending|make|making|use\s+your\s+new\s+card\s+to\s+make)\s+(?:at\s+least\s+)?\$\d[\d,]*\s+(?:on|in|at|with)\s+([^.,;]{0,70})", re.I)
_GENERAL_SPEND = re.compile(
    r"^(?:(?:your\s+new\s+card|your\s+card|the\s+card|eligible|qualifying|new|net|everyday)\s+)*(?:purchases?|the\s+card)\b|^(?:the|your)\s+first\b", re.I)


def _credit_is_specific(primary, match):
    trigger = _CREDIT_TRIGGER.search(primary[match.end():match.end() + 160])
    return bool(trigger) and not _GENERAL_SPEND.match(trigger.group(1).strip())


def _earliest(patterns, text):
    hits = [(m.start(), m) for p in patterns for m in [p.search(text)] if m]
    return min(hits, key=lambda h: h[0])[1] if hits else None


def parse_offer(raw):
    text = re.sub(r"[®™℠]", "", raw)
    text = re.sub(r"\s+", " ", text).strip()
    out = ParsedOffer()

    if _MATCH.search(text):
        out.kind = "match"
        out.notes.append("first-year match of what is earned; no fixed bonus amount")
        return out

    # second tier (kept separately); the first tier's spend and window come from the text before it
    tier_match = _SECOND_TIER.search(text)
    total_match = _SECOND_TIER_TOTAL.search(text)
    if total_match and (not tier_match or total_match.start() < tier_match.start()):
        tier_match, primary = None, text[:total_match.start()]
        tier = Tier(points=_n(total_match.group(4)), min_spend=_n(total_match.group(1)),
                    window_months=_months(total_match.group(2), total_match.group(3)),
                    note="spend is a total from account opening, not on top of the first tier's spend")
        out.additional_tiers.append(tier)
    else:
        primary = text[:tier_match.start()] if tier_match else text
    if tier_match:
        tail = tier_match.group("tail")
        w = _WINDOW[0].search(tail) or _WINDOW[1].search(tail)
        tier = Tier(points=_n(tier_match.group(1)), min_spend=_n(tier_match.group(2)),
                    window_months=_months(w.group(1), w.group(2)) if w else None)
        if re.search(r"\bat\s+[A-Z]", tail):
            tier.note = "the spend must be at a specific merchant"
        out.additional_tiers.append(tier)

    # points
    struck = _STRUCK.search(primary)
    points = list(_POINTS.finditer(primary))
    if struck:
        out.points = _n(struck.group(2))
        out.notes.append(f"struck-through pair (old and new figures); used the second, {struck.group(2)}; please check")
    elif len(points) >= 2 and re.search(r"up\s+to\s*$", primary[:points[0].start()], re.I) and points[1].start() - points[0].end() <= 2:
        out.points = _n(points[1].group(1))
        out.notes.append("counted the first part only (the rest depends on further bonus spending)")
    elif points:
        out.points = _n(points[0].group(1))

    # cash: gift cards and statement credits at face value; a repeated amount is one item
    amounts, cash_ceiling = [], False
    for m in _CASH.finditer(primary):
        if _BEFORE_A_SPEND_AMOUNT.search(primary[max(0, m.start() - 30):m.start()]):
            continue
        if _REDEMPTION_VALUE.match(primary, m.end()):
            continue   # "that's a $200 cash redemption value" restates the points' worth, it is not a second bonus
        if re.search(r"annual\s+fee|\bfee\b", m.group(0), re.I) or _n(m.group(1)) == 0:
            continue   # a fee, not a bonus
        if re.search(r"credits?$", m.group(0), re.I) and _credit_is_specific(primary, m):
            out.notes.append(f"a statement credit tied to specific spending is not counted (${_n(m.group(1)):,.0f})")
            continue
        amounts.append(_n(m.group(1)))
        cash_ceiling = cash_ceiling or bool(re.search(r"up\s+to\s+$", primary[max(0, m.start() - 12):m.start()], re.I))
    if amounts:
        distinct = list(dict.fromkeys(amounts))
        if len(distinct) < len(amounts):
            out.notes.append("a repeated amount was merged into one")
        out.cash_back = sum(distinct)

    nights = _FREE_NIGHT.search(primary)
    if nights:
        word = nights.group(1).lower()
        out.free_night_awards = int(word) if word.isdigit() else _WORD_NUMBERS[word]

    if _COMPANION.search(primary):
        out.notes.append("also includes a companion fare, certificate or award (not valued)")
    if re.search(r"authorized\s+user|employee\s+card", text, re.I):
        out.notes.append("an authorized-user or employee-card bonus is excluded")
    points_ceiling = bool(points) and not any("first part" in n for n in out.notes) and bool(
        re.search(r"up\s+to\s*$", primary[:points[0].start()], re.I))
    if re.search(r"as\s+high\s+as", primary, re.I) or cash_ceiling or points_ceiling:
        out.ceiling = True

    spend = _earliest(_SPEND, primary)
    if spend:
        out.min_spend = _n(spend.group(1))
    window = _earliest(_WINDOW, primary)
    if window:
        out.window_months = _months(window.group(1), window.group(2))

    if out.points is None and out.cash_back is None and not out.free_night_awards:
        out.kind = "unparsed"
        out.notes.append("no bonus amount recognised; read the offer text")
        return out
    if out.min_spend is None:
        out.notes.append("awarded on approval, no spend requirement" if re.search(r"(?:on|upon)\s+approval", primary, re.I)
                         else "no spend requirement found")
    if out.window_months is None and out.min_spend is not None:
        out.notes.append("no time window found")
    return out
