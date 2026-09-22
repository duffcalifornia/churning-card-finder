"""Watch Frequent Miler's Reasonable Redemption Values page for changes.

Two independent signals, either one enough to call it "changed": the article's `dateModified` (from the page's
JSON-LD, when present) and a hash of the visible text of every `<table>` on the page (the RRV tables themselves).
Relying on the hash too, not just the date, protects against an edit that does not bump the modified date.

If the page cannot be read at all (a redesign, an error page), that is its own outcome, never reported as
"unchanged": guessing there that nothing changed would be the one thing worse than not checking at all.
"""
import hashlib
import re
from dataclasses import dataclass
from typing import Optional

# Below this many characters of combined table text, the page is treated as unreadable rather than trusted.
_MIN_TABLE_TEXT = 200


@dataclass
class RrvSnapshot:
    date_modified: Optional[str]
    values_hash: Optional[str]
    value_count: int      # length of the combined table text; kept for the report, not used in comparisons
    readable: bool


def _table_text(html):
    tables = re.findall(r"<table.*?</table>", html, flags=re.S | re.I)
    text = " ".join(re.sub(r"<[^>]+>", " ", t) for t in tables)
    return re.sub(r"\s+", " ", text).strip()


def read_rrv_snapshot(html):
    """Pure: reads dateModified and hashes the table text. Never fetches anything."""
    m = re.search(r'"dateModified"\s*:\s*"([^"]+)"', html)
    date_modified = m.group(1) if m else None

    text = _table_text(html)
    readable = len(text) >= _MIN_TABLE_TEXT
    values_hash = hashlib.sha256(text.encode()).hexdigest() if readable else None
    return RrvSnapshot(date_modified=date_modified, values_hash=values_hash, value_count=len(text), readable=readable)


def decide(previous, snapshot):
    """(outcome, exit_code) from the last saved state (a dict, or None on the first run) and today's snapshot.

    outcome is one of: first_run, unchanged, changed, unreadable. Exit codes are cron-friendly: 0 means nothing
    needs attention, 1 means the page moved and the owner should compare it to data/valuations.json, 2 means the
    check itself failed and needs a look before it can say anything about the values.
    """
    if not snapshot.readable:
        return "unreadable", 2
    if previous is None:
        return "first_run", 0
    changed = previous.get("date_modified") != snapshot.date_modified or previous.get("values_hash") != snapshot.values_hash
    return ("changed", 1) if changed else ("unchanged", 0)
