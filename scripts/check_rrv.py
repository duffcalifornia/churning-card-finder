#!/usr/bin/env python3
"""Check Frequent Miler's Reasonable Redemption Values page for changes, once a day.

Maintainer tool, not part of the site. A single polite fetch of one page; nothing else is touched.

Usage:
    python3 scripts/check_rrv.py            # check, report, exit nonzero if something needs a look
    python3 scripts/check_rrv.py --ack       # after reviewing data/valuations.json, accept the current
                                              # page as the new baseline so it stops being reported

Exit codes (meant for a daily cron job): 0 nothing needs attention (or --ack succeeded), 1 the page changed
and data/valuations.json should be compared against it by hand, 2 the page could not be read (a redesign or
an error page; never treated as "unchanged").

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
from cardfinder.rrv_check import decide, read_rrv_snapshot  # noqa: E402

URL = "https://frequentmiler.com/reasonable-redemption-values-rrvs/"
STATE_PATH = os.path.join(HERE, "cardfinder", "rrv_check_state.json")
# A copy of data/valuations.json's `values` as of the last ack, so --ack can tell *which* programs' cents-per-
# point actually changed (rrv_check_state.json only knows the RRV *page* changed, not which values on it did).
VALUES_SNAPSHOT_PATH = os.path.join(HERE, "cardfinder", "last_known_values.json")
VALUATIONS_PATH = os.path.join(ROOT, "data", "valuations.json")
CHANGELOG_PATH = os.path.join(ROOT, "CHANGELOG.md")


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


def save_state(snapshot, checked_on, first_saved_on):
    state = {
        "date_modified": snapshot.date_modified, "values_hash": snapshot.values_hash,
        "value_count": snapshot.value_count, "checked_on": checked_on, "first_saved_on": first_saved_on,
    }
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
        page = HttpFetcher().fetch(URL)
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
        save_values_snapshot(current_valuations())  # seeds the baseline so a later --ack can diff against it
        print(f"No baseline yet: saved today's version as the starting point ({snapshot.value_count} characters "
              f"across its tables, dateModified={snapshot.date_modified}).")
        return code

    if outcome == "unchanged":
        save_state(snapshot, checked_on=today, first_saved_on=previous.get("first_saved_on", today))
        print(f"No change since it was last saved on {previous.get('first_saved_on', 'unknown')}.")
        return code

    # changed
    print(f"The RRV page looks different from the saved baseline (saved {previous.get('first_saved_on', 'unknown')}):")
    print(f"  dateModified: {previous.get('date_modified')!r} -> {snapshot.date_modified!r}")
    if previous.get("values_hash") != snapshot.values_hash:
        print("  the table values changed (hash differs)")
    print(f"Compare it against data/valuations.json by hand, then rerun with --ack once reviewed. {URL}")
    if opts.ack:
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
        print("Acknowledged: saved the current page as the new baseline.")
        return 0
    return code


if __name__ == "__main__":
    sys.exit(main())
