"""Cards the daily refresh could not find: which are worth a human look, and what the review issue says.

A card that is simply gone from the issuer's site (every page it tried was a 404 or the wrong page) should not
fail the whole run: the site keeps its last known data for it, and a GitHub issue asks the owner one question, "is
it discontinued?". Anything that looks like a block, an outage or a site redesign is different, and still fails
the run, because guessing wrong there would quietly hide real breakage.

Pure functions only (the gh calls live in scripts/report_missing_cards.py).
"""
import datetime
import re

LABEL_MISSING = "card-missing"
LABEL_STILL_ACTIVE = "still-active"
SNOOZE_DAYS = 30            # after "/still-active", don't raise the same card again for this long
SURGE = 4                   # this many missing cards from one issuer in a run looks like a redesign or block, not retirements

# An attempt outcome that says "the page is not there", as opposed to "we could not tell" (403, 429, 5xx, timeouts).
CONCLUSIVE = ("http_404", "http_410", "wrong_page", "no_candidates")

_MARKER = re.compile(r"<!--\s*card-id:\s*([a-z0-9-]+)\s*-->")


def split_not_found(results, issuer_of, surge=SURGE):
    """(reviewable, unreadable) from a run's not_found results.

    reviewable: every attempt conclusively said "not there", and the issuer has fewer than `surge` such cards this run.
    unreadable: everything else (an attempt that errored or was refused, no attempts at all, or a whole issuer going
    missing at once). Only these should fail the run.
    """
    not_found = [r for r in results if r.status == "not_found"]
    conclusive = [r for r in not_found if r.attempts and all(a.outcome in CONCLUSIVE for a in r.attempts)]
    per_issuer = {}
    for r in conclusive:
        per_issuer[issuer_of[r.card_id]] = per_issuer.get(issuer_of[r.card_id], 0) + 1
    surged = {issuer for issuer, n in per_issuer.items() if n >= surge}
    reviewable = [r for r in conclusive if issuer_of[r.card_id] not in surged]
    unreadable = [r for r in not_found if r not in reviewable]
    return reviewable, unreadable


def missing_document(reviewable, found_ids, issuer_of, url_of, today):
    """What the refresh writes for scripts/report_missing_cards.py."""
    return {
        "date": today,
        "missing": [{"id": r.card_id, "name": r.name, "issuer": issuer_of[r.card_id], "url": url_of.get(r.card_id),
                     "tried": [{"strategy": a.strategy, "url": a.url, "outcome": a.outcome} for a in r.attempts]}
                    for r in reviewable],
        "found": sorted(found_ids),
    }


def card_id_from_body(body):
    m = _MARKER.search(body or "")
    return m.group(1) if m else None


def issue_title(name):
    return f"Card not found: {name}"


def issue_body(entry):
    tried = "\n".join(f"- {a['strategy']}: {a['url'] or '(nothing to try)'} -> {a['outcome']}" for a in entry["tried"])
    page = f"Its last known page: {entry['url']}\n\n" if entry.get("url") else ""
    return (
        f"The daily refresh could not find **{entry['name']}** (`{entry['id']}`, {entry['issuer']}) on the issuer's site.\n\n"
        f"{page}What it tried:\n{tried}\n\n"
        "**Check whether the card can still be applied for, then reply to this issue with one of:**\n\n"
        "- `/discontinued` - it can no longer be applied for. It is removed from the site, a changelog line is added, "
        "and this issue closes.\n"
        f"- `/still-active` - it can still be applied for (the scraper just can't find it). Its last known offer stays on "
        f"the site and this is not raised again for {SNOOZE_DAYS} days.\n\n"
        "This works from the GitHub mobile app. Only replies from someone with write access are acted on.\n\n"
        f"<!-- card-id: {entry['id']} -->\n"
    )


def _day(timestamp):
    return datetime.date.fromisoformat(timestamp[:10])


def plan_reports(doc, issues, today, snooze_days=SNOOZE_DAYS):
    """(to_open, to_close) for this run.

    doc: the missing-cards document. issues: card-missing issues, open and closed, as dicts with number, body, state
    ("OPEN"/"CLOSED"), labels (names) and closedAt.
    to_open: missing entries with no open issue and no recent "/still-active" answer.
    to_close: (issue number, card id) for open issues whose card was read fine this run.
    """
    open_ids, snoozed = {}, set()
    cutoff = _day(today) - datetime.timedelta(days=snooze_days)
    for issue in issues:
        cid = card_id_from_body(issue.get("body"))
        if not cid:
            continue
        if issue["state"] == "OPEN":
            open_ids[cid] = issue["number"]
        elif LABEL_STILL_ACTIVE in issue.get("labels", []) and issue.get("closedAt") and _day(issue["closedAt"]) > cutoff:
            snoozed.add(cid)
    to_open = [m for m in doc["missing"] if m["id"] not in open_ids and m["id"] not in snoozed]
    found = set(doc.get("found", []))
    to_close = [(number, cid) for cid, number in open_ids.items() if cid in found]
    return to_open, to_close
