"""Bonus value: points x cents-per-point, plus cash, plus free night certificates, minus the annual fee.

The site ranks on the first-year fee (a waived first year costs nothing); this module subtracts whatever fee it is given."""


def _cents_per_point(valuations, currency, unlocked):
    entry = valuations["values"][currency]          # KeyError for a currency with no value: never guessed
    if isinstance(entry, dict):
        return entry["withUnlocker"] if unlocked else entry["withoutUnlocker"]
    return entry


def bonus_value(offer, currency, valuations, unlocked=True, certificate=None, include_tiers=False):
    """Dollar value of a parsed offer (a record's `parsed` dict).

    currency     id of the points currency the offer pays in (a key of valuations["values"]).
    unlocked     whether the household can transfer the currency (matters for two-rate currencies).
    certificate  free night certificate type (key of valuations["freeNightCertificates"]); required when the offer has free nights.
    include_tiers  add the extra tiers (the engine does this when the household's spending meets the first threshold).
    """
    def points_value(points):
        return (points or 0) * _cents_per_point(valuations, currency, unlocked) / 100 if points else 0.0

    total = points_value(offer.get("points")) + (offer.get("cashBack") or 0)
    nights = offer.get("freeNightAwards") or 0
    if nights:
        if certificate is None:
            raise ValueError("this offer has free night awards; say which certificate type values them")
        total += nights * valuations["freeNightCertificates"][certificate]
    if include_tiers:
        for tier in offer.get("additionalTiers") or []:
            total += points_value(tier.get("points")) + (tier.get("cashBack") or 0)
    return total


def net_value(offer, currency, valuations, annual_fee, **kw):
    """Bonus value minus the annual fee given (the site passes the first-year fee)."""
    return bonus_value(offer, currency, valuations, **kw) - annual_fee
