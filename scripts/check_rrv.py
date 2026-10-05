#!/usr/bin/env python3
"""Check Frequent Miler's Reasonable Redemption Values page for changes, once a day.

Maintainer tool, not part of the site. A single polite fetch of one page; nothing else is touched.

Usage:
    python3 scripts/check_rrv.py            # check, report, exit nonzero if something needs a look
    python3 scripts/check_rrv.py --ack       # after reviewing data/valuations.json, accept the current
                                              # page as the new baseline so it stops being reported

Exit codes (meant for a daily cron job): 0 nothing new needs attention (or --ack succeeded), 1 the page's tables
changed and data/valuations.json should be compared against them by hand (reported once per distinct change,
with the changed rows printed), 2 the page could not be read (a redesign or an error page; never treated as
"unchanged").

Scheduling it yourself (macOS cron), once a day at 8am:
    0 8 * * * cd /path/to/churning-card-finder && /usr/bin/python3 scripts/check_rrv.py >> /tmp/rrv-check.log 2>&1
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from cardfinder.changelog import prepend_changelog_entry, valuation_change_entry  # noqa: E402
from cardfinder.fetchers import HttpFetcher  # noqa: E402
from cardfinder.rrv_check import decide, diff_rows, read_rrv_snapshot  # noqa: E402

URL = "https://frequentmiler.com/reasonable-redemption-values-rrvs/"
STATE_PATH = os.path.join(HERE, "cardfinder", "rrv_check_state.json")
# A copy of data/valuations.json's `values` as of the last ack, so --ack can tell *which* programs' cents-per-
# point actually changed (rrv_check_state.json only knows the RRV *page* changed, not which values on it did).
VALUES_SNAPSHOT_PATH = os.path.join(HERE, "cardfinder", "last_known_values.json")
VALUATIONS_PATH = os.path.join(ROOT, "data", "valuations.json")
CHANGELOG_PATH = os.path.join(ROOT, "CHANGELOG.md")
# The saved table rows (one per line) as of the baseline, so a change can be shown as a diff.
ROWS_PATH = os.path.join(HERE, "cardfinder", "rrv_check_rows.txt")
FETCH_ATTEMPTS = 3
FETCH_RETRY_SECONDS = 20


def load_values_snapshot():
    if not os.path.exists(VALUES_SNAPSHOT_PATH):
        return {}
    with open(VALUES_SNAPSHOT_PATH) as f:
        return json.load(f)


def save_values_snapshot(values):
    with open(VALUES_SNAPSHOT_PATH, "w") as f:
        json.dump(values, f, indent=1, sort_keys=True)
        f.write("\n")


def current_valuations():
    with open(VALUATIONS_PATH) as f:
        return json.load(f)["values"]


def load_state():
    if not os.path.exists(STATE_PATH):
        return None
    with open(STATE_PATH) as f:
        return json.load(f)


def load_rows():
    if not os.path.exists(ROWS_PATH):
        return None
    with open(ROWS_PATH) as f:
        return f.read().splitlines()


def save_rows(snapshot):
    with open(ROWS_PATH, "w") as f:
        f.write("\n".join(snapshot.rows) + "\n")


def fetch_with_retries():
    """A transient blip (timeout, 5xx) should not fail the daily job; only a failure that survives retries does."""
    import time
    for attempt in range(1, FETCH_ATTEMPTS + 1):
        try:
            return HttpFetcher().fetch(URL)
        except Exception:  # noqa: BLE001
            if attempt == FETCH_ATTEMPTS:
                raise
            time.sleep(FETCH_RETRY_SECONDS)


def save_state(snapshot, checked_on, first_saved_on, flagged_hash=None):
    state = {
        "date_modified": snapshot.date_modified, "values_hash": snapshot.values_hash,
        "value_count": snapshot.value_count, "checked_on": checked_on, "first_saved_on": first_saved_on,
    }
    if flagged_hash:
        state["flagged_hash"] = flagged_hash
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=1)
        f.write("\n")


def main(argv=None):
    args = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    args.add_argument("--ack", action="store_true", help="accept the current page as the new baseline")
    opts = args.parse_args(argv)

    import datetime
    today = datetime.date.today().isoformat()

    try:
        page = fetch_with_retries()
    except Exception as e:  # noqa: BLE001 -- any fetch failure is reported the same way, never silently ignored
        print(f"Could not fetch the RRV page: {e}")
        return 2

    snapshot = read_rrv_snapshot(page.html)
    previous = load_state()
    outcome, code = decide(previous, snapshot)

    if outcome == "unreadable":
        print(f"Could not read the RRV page's tables (got {snapshot.value_count} characters of table text; "
              f"the page may have been redesigned). Not touching the saved baseline. {URL}")
        return code

    if outcome == "first_run":
        save_state(snapshot, checked_on=today, first_saved_on=today)
        save_rows(snapshot)
        save_values_snapshot(current_valuations())  # seeds the baseline so a later --ack can diff against it
        print(f"No baseline yet: saved today's version as the starting point ({snapshot.value_count} characters "
              f"across its tables, dateModified={snapshot.date_modified}).")
        return code

    first_saved = previous.get("first_saved_on", today)
    if outcome in ("unchanged", "date_only"):
        # Same tables: refresh the baseline's date, and (re)save the rows if an older baseline predates them.
        save_state(snapshot, checked_on=today, first_saved_on=first_saved)
        if load_rows() is None:
            save_rows(snapshot)
        if outcome == "date_only":
            print(f"Tables unchanged, but dateModified moved: {previous.get('date_modified')!r} -> "
                  f"{snapshot.date_modified!r}. Not flagged; the values are what matter.")
        else:
            print(f"No change since it was last saved on {first_saved}.")
        return code

    if outcome == "already_flagged" and not opts.ack:
        print(f"Still waiting on an earlier flagged change (saved baseline {first_saved}); not flagging it again. "
              f"Compare data/valuations.json to the page, then rerun with --ack. {URL}")
        return code

    # changed
    print(f"The RRV tables look different from the saved baseline (saved {first_saved}):")
    print(f"  dateModified: {previous.get('date_modified')!r} -> {snapshot.date_modified!r}")
    old_rows = load_rows()
    if old_rows is None:
        print("  no saved rows to diff against (the baseline predates them); they will be saved on --ack.")
    else:
        for line in diff_rows(old_rows, snapshot.rows):
            print(f"  {line}")
    print(f"Compare it against data/valuations.json by hand, then rerun with --ack once reviewed. {URL}")
    if not opts.ack:
        # Remember which version was flagged so the same change does not fail the job again tomorrow.
        flagged = dict(previous, flagged_hash=snapshot.values_hash, checked_on=today)
        with open(STATE_PATH, "w") as f:
            json.dump(flagged, f, indent=1)
            f.write("\n")
        return code

    # Site owner's rule (2026-09-22): whichever programs' values actually changed in data/valuations.json
    # since the last ack get one consistent changelog line — this is a maintainer confirming a real,
    # already-made edit, not something guessed from the RRV page itself (rrv_check never parses values).
    new_values = current_valuations()
    entry = valuation_change_entry(load_values_snapshot(), new_values)
    if entry:
        prepend_changelog_entry(CHANGELOG_PATH, today, entry)
        print(f"Changelog: {entry}")
    save_values_snapshot(new_values)
    save_state(snapshot, checked_on=today, first_saved_on=today)
    save_rows(snapshot)
    print("Acknowledged: saved the current page as the new baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
