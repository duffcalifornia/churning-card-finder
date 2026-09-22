"""Selecting cards, running checks and reporting results."""
import dataclasses
import json

from .check import CardResult, check_card


def select_cards(cards, issuer, name_filter):
    chosen = [c for c in cards if issuer == "all" or c.issuer == issuer]
    if name_filter:
        needle = name_filter.lower()
        chosen = [c for c in chosen if needle in c.id.lower() or any(needle in n.lower() for n in c.names)]
    return chosen


def split_paused(cards, issuers):
    """Separate cards whose issuer is paused. Returns (cards to check, {issuer: reason} for paused issuers that had cards)."""
    active, paused = [], {}
    for c in cards:
        reason = issuers[c.issuer].paused
        if reason:
            paused[c.issuer] = reason
        else:
            active.append(c)
    return active, paused


def exit_code(results):
    return 2 if any(r.status == "not_found" for r in results) else 0


def _fee_text(fee):
    if fee is None:
        return "(none found)"
    return f"${fee.amount:,.0f}" + (", waived the first year" if fee.first_year_waived else "")


def format_report(results):
    lines = []
    for r in results:
        if r.status == "skipped":
            lines.append(f"[SKIPPED] {r.name}: {r.note}")
            continue
        if r.status == "not_found":
            lines.append(f"[NOT FOUND] {r.name}")
            for a in r.attempts:
                lines.append(f"    tried {a.strategy}: {a.url or '(nothing to try)'} -> {a.outcome}")
            continue
        tag = "FOUND" if r.status == "found" else "FOUND (moved)"
        lines.append(f"[{tag}] {r.name}  via {r.strategy}  {r.url}")
        lines.append(f"    offer: {r.offer.text if r.offer else '(none)'}")
        lines.append(f"    fee:   {_fee_text(r.fee)}")
        if r.flags:
            lines.append(f"    flags: {', '.join(r.flags)}")
    found = sum(1 for r in results if r.status in ("found", "found_via_fallback"))
    moved = sum(1 for r in results if r.status == "found_via_fallback")
    lines.append(f"\nSummary: {found} found ({moved} via fallback), "
                 f"{sum(1 for r in results if r.status == 'not_found')} not found, "
                 f"{sum(1 for r in results if r.status == 'skipped')} skipped")
    return "\n".join(lines)


def to_json(results):
    return json.dumps([dataclasses.asdict(r) for r in results], indent=2)


MAX_CONSECUTIVE_ERROR_PAGES = 3


def run(cards, issuers, http, rendered=None, on_result=None, all_cards=None):
    """Check each card. After a few error pages in a row from one issuer, stop asking it (it is likely
    throttling or blocking us) and report the remaining cards as not checked."""
    results, streak, stopped = [], {}, set()
    for card in cards:
        if card.issuer in stopped:
            result = CardResult(card.id, card.names[0], "skipped",
                                note="Stopped after repeated error pages from this issuer; run again later.")
        else:
            result = check_card(card, issuers[card.issuer], http, rendered=rendered, siblings=all_cards or cards)
            streak[card.issuer] = streak.get(card.issuer, 0) + 1 if "page_error" in result.flags else 0
            if streak[card.issuer] >= MAX_CONSECUTIVE_ERROR_PAGES:
                stopped.add(card.issuer)
        results.append(result)
        if on_result:
            on_result(result)
    # Two cards resolving to one page means at least one is wrong (a listing link led to a sibling's page).
    by_url = {}
    for r in results:
        if r.url and r.status in ("found", "found_via_fallback"):
            by_url.setdefault(r.url.split("?")[0].rstrip("/"), []).append(r)
    for group in by_url.values():
        if len(group) > 1:
            for r in group:
                if "same_page_as_another_card" not in r.flags:
                    r.flags.append("same_page_as_another_card")
    return results
