"""Watch Frequent Miler's Reasonable Redemption Values page for changes.

The signal that counts as "changed" is a hash of the visible text of every `<table>` on the page (the RRV tables
themselves). That catches an edit that does not bump the article's `dateModified`. A `dateModified` bump with
identical tables is only noted, not flagged: the values are what matter, and the date moves for unrelated edits.
A given change is flagged once (the baseline records which version it flagged), not on every daily run until acked.

The table text is also kept row by row so a flagged change can print exactly which rows moved.

If the page cannot be read at all (a redesign, an error page), that is its own outcome, never reported as
"unchanged": guessing there that nothing changed would be the one thing worse than not checking at all.
"""
import difflib
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
    rows: tuple = ()      # one normalized line per table row, for showing what changed; not used in comparisons


def _table_text(html):
    tables = re.findall(r"<table.*?</table>", html, flags=re.S | re.I)
    text = " ".join(re.sub(r"<[^>]+>", " ", t) for t in tables)
    return re.sub(r"\s+", " ", text).strip()


def _table_rows(html):
    """One normalized line per `<tr>` across all tables, so a diff points at the row that moved."""
    rows = []
    for t in re.findall(r"<table.*?</table>", html, flags=re.S | re.I):
        for tr in re.findall(r"<tr.*?</tr>", t, flags=re.S | re.I):
            line = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", tr)).strip()
            if line:
                rows.append(line)
    return tuple(rows)


def diff_rows(old_rows, new_rows, limit=60):
    """Unified diff lines (changed rows only, no context) between two lists of rows, capped at `limit` lines."""
    lines = [l for l in difflib.unified_diff(old_rows, new_rows, "saved", "today", n=0, lineterm="")
             if not l.startswith(("---", "+++", "@@"))]
    if len(lines) > limit:
        lines = lines[:limit] + [f"... and {len(lines) - limit} more changed rows"]
    return lines


def read_rrv_snapshot(html):
    """Pure: reads dateModified and hashes the table text. Never fetches anything."""
    m = re.search(r'"dateModified"\s*:\s*"([^"]+)"', html)
    date_modified = m.group(1) if m else None

    text = _table_text(html)
    readable = len(text) >= _MIN_TABLE_TEXT
    values_hash = hashlib.sha256(text.encode()).hexdigest() if readable else None
    return RrvSnapshot(date_modified=date_modified, values_hash=values_hash, value_count=len(text), readable=readable,
                       rows=_table_rows(html) if readable else ())


def decide(previous, snapshot):
    """(outcome, exit_code) from the last saved state (a dict, or None on the first run) and today's snapshot.

    outcome is one of: first_run, unchanged, date_only, changed, already_flagged, unreadable. Exit codes are
    cron-friendly: 0 means nothing new needs attention, 1 means the tables moved and the owner should compare them
    to data/valuations.json (reported once per distinct change), 2 means the check itself failed and needs a look
    before it can say anything about the values.
    """
    if not snapshot.readable:
        return "unreadable", 2
    if previous is None:
        return "first_run", 0
    if previous.get("values_hash") != snapshot.values_hash:
        if previous.get("flagged_hash") == snapshot.values_hash:
            return "already_flagged", 0
        return "changed", 1
    if previous.get("date_modified") != snapshot.date_modified:
        return "date_only", 0
    return "unchanged", 0
