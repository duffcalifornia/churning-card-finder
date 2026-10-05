import sys
import unittest

from cardfinder.rrv_check import decide, read_rrv_snapshot

JSONLD = '<script type="application/ld+json">{"@type":"Article","dateModified":"2026-09-02T20:56:43+00:00"}</script>'


def page(date_modified_block=JSONLD, tables="<table><tr><td>Ultimate Rewards</td><td>1.5</td></tr></table>" * 15):
    return f"<html><head>{date_modified_block}</head><body>{tables}</body></html>"


class ReadRrvSnapshot(unittest.TestCase):
    def test_reads_the_dateModified_field_from_the_jsonld_block(self):
        snap = read_rrv_snapshot(page())
        self.assertEqual(snap.date_modified, "2026-09-02T20:56:43+00:00")
        self.assertTrue(snap.readable)

    def test_hashes_the_visible_text_of_every_table_on_the_page(self):
        a = read_rrv_snapshot(page(tables="<table><tr><td>Ultimate Rewards</td><td>1.5</td></tr></table>" * 15))
        b = read_rrv_snapshot(page(tables="<table><tr><td>Ultimate Rewards</td><td>1.5</td></tr></table>" * 15))
        self.assertEqual(a.values_hash, b.values_hash)
        self.assertIsNotNone(a.values_hash)

    def test_a_changed_number_changes_the_hash(self):
        a = read_rrv_snapshot(page(tables="<table><tr><td>Ultimate Rewards</td><td>1.5</td></tr></table>" * 15))
        b = read_rrv_snapshot(page(tables="<table><tr><td>Ultimate Rewards</td><td>1.6</td></tr></table>" * 15))
        self.assertNotEqual(a.values_hash, b.values_hash)

    def test_whitespace_and_markup_differences_alone_do_not_change_the_hash(self):
        a = read_rrv_snapshot(page(tables="<table><tr><td>Ultimate Rewards</td><td>1.5</td></tr></table>" * 15))
        b = read_rrv_snapshot(page(tables="<table>\n<tr>  <td>Ultimate   Rewards</td>\n<td>1.5</td></tr>\n</table>" * 15))
        self.assertEqual(a.values_hash, b.values_hash)

    def test_a_page_with_no_tables_or_very_little_table_text_is_marked_unreadable(self):
        snap = read_rrv_snapshot(page(tables="<table><tr><td>hi</td></tr></table>"))
        self.assertFalse(snap.readable)
        self.assertIsNone(snap.values_hash)

    def test_missing_dateModified_does_not_make_the_page_unreadable_on_its_own(self):
        snap = read_rrv_snapshot(page(date_modified_block=""))
        self.assertIsNone(snap.date_modified)
        self.assertTrue(snap.readable)  # the table hash alone is still a usable signal

    def test_totally_empty_page_is_unreadable(self):
        snap = read_rrv_snapshot("<html><body>nothing here</body></html>")
        self.assertFalse(snap.readable)


class Decide(unittest.TestCase):
    def test_no_previous_state_is_a_first_run(self):
        from cardfinder.rrv_check import RrvSnapshot
        outcome, code = decide(None, RrvSnapshot(date_modified="2026-09-02", values_hash="abc", value_count=30, readable=True))
        self.assertEqual((outcome, code), ("first_run", 0))

    def test_same_date_and_hash_is_unchanged(self):
        from cardfinder.rrv_check import RrvSnapshot
        prev = {"date_modified": "2026-09-02", "values_hash": "abc"}
        outcome, code = decide(prev, RrvSnapshot(date_modified="2026-09-02", values_hash="abc", value_count=30, readable=True))
        self.assertEqual((outcome, code), ("unchanged", 0))

    def test_a_different_hash_is_changed_even_if_the_date_did_not_move(self):
        from cardfinder.rrv_check import RrvSnapshot
        prev = {"date_modified": "2026-09-02", "values_hash": "abc"}
        outcome, code = decide(prev, RrvSnapshot(date_modified="2026-09-02", values_hash="xyz", value_count=30, readable=True))
        self.assertEqual((outcome, code), ("changed", 1))

    def test_a_different_date_alone_is_noted_but_does_not_fail(self):
        from cardfinder.rrv_check import RrvSnapshot
        prev = {"date_modified": "2026-09-02", "values_hash": "abc"}
        outcome, code = decide(prev, RrvSnapshot(date_modified="2026-09-03", values_hash="abc", value_count=30, readable=True))
        self.assertEqual((outcome, code), ("date_only", 0))

    def test_a_change_already_flagged_does_not_fail_again(self):
        from cardfinder.rrv_check import RrvSnapshot
        prev = {"date_modified": "2026-09-02", "values_hash": "abc", "flagged_hash": "xyz"}
        outcome, code = decide(prev, RrvSnapshot(date_modified="2026-09-02", values_hash="xyz", value_count=30, readable=True))
        self.assertEqual((outcome, code), ("already_flagged", 0))

    def test_a_further_change_after_a_flag_is_flagged_again(self):
        from cardfinder.rrv_check import RrvSnapshot
        prev = {"date_modified": "2026-09-02", "values_hash": "abc", "flagged_hash": "xyz"}
        outcome, code = decide(prev, RrvSnapshot(date_modified="2026-09-02", values_hash="new", value_count=30, readable=True))
        self.assertEqual((outcome, code), ("changed", 1))

    def test_an_unreadable_page_is_its_own_outcome_never_reported_as_unchanged(self):
        from cardfinder.rrv_check import RrvSnapshot
        prev = {"date_modified": "2026-09-02", "values_hash": "abc"}
        outcome, code = decide(prev, RrvSnapshot(date_modified=None, values_hash=None, value_count=0, readable=False))
        self.assertEqual((outcome, code), ("unreadable", 2))


class DiffRows(unittest.TestCase):
    def test_rows_are_read_one_per_tr_and_only_changed_rows_are_diffed(self):
        from cardfinder.rrv_check import diff_rows
        html = lambda v: f"<table><tr><td>Avios</td><td>{v}</td></tr><tr><td>Hyatt</td><td>2.0</td></tr></table>" * 15
        old = read_rrv_snapshot(page(tables=html("1.5"))).rows
        new = read_rrv_snapshot(page(tables=html("1.6"))).rows
        self.assertEqual(old[0], "Avios 1.5")
        self.assertIn("-Avios 1.5", diff_rows(old, new))
        self.assertIn("+Avios 1.6", diff_rows(old, new))
        self.assertNotIn("-Hyatt 2.0", diff_rows(old, new))

    def test_a_long_diff_is_capped(self):
        from cardfinder.rrv_check import diff_rows
        out = diff_rows([f"a{i}" for i in range(200)], [f"b{i}" for i in range(200)], limit=10)
        self.assertEqual(len(out), 11)
        self.assertIn("more changed rows", out[-1])


class StateFileRoundTrip(unittest.TestCase):
    """save_state/load_state in check_rrv.py must write exactly the keys decide() reads from cardfinder/rrv_check.py."""

    def setUp(self):
        import importlib
        import os
        import tempfile

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        import check_rrv
        importlib.reload(check_rrv)
        self.check_rrv = check_rrv
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        os.unlink(self.tmp.name)  # save_state/load_state must create it fresh
        self._orig_path = check_rrv.STATE_PATH
        check_rrv.STATE_PATH = self.tmp.name

    def tearDown(self):
        import os

        self.check_rrv.STATE_PATH = self._orig_path
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_a_saved_snapshot_round_trips_into_a_dict_decide_understands(self):
        from cardfinder.rrv_check import RrvSnapshot

        snap = RrvSnapshot(date_modified="2026-09-02T20:56:43+00:00", values_hash="abc123", value_count=999, readable=True)
        self.check_rrv.save_state(snap, checked_on="2026-09-21", first_saved_on="2026-09-21")

        loaded = self.check_rrv.load_state()
        self.assertEqual(loaded["date_modified"], snap.date_modified)
        self.assertEqual(loaded["values_hash"], snap.values_hash)
        self.assertEqual(loaded["checked_on"], "2026-09-21")
        self.assertEqual(loaded["first_saved_on"], "2026-09-21")

        # and it plugs straight into decide() as the "previous" state, unchanged when the snapshot repeats
        outcome, code = decide(loaded, snap)
        self.assertEqual((outcome, code), ("unchanged", 0))

    def test_no_saved_file_yet_loads_as_none(self):
        self.assertIsNone(self.check_rrv.load_state())


class AckWritesTheChangelogTests(unittest.TestCase):
    """--ack, on a genuinely changed page, diffs data/valuations.json against the last-acked snapshot and adds
    one changelog line for whichever programs' values actually moved — the owner's rule (2026-09-22)."""

    NEW_HTML = (
        '<html><head><script type="application/ld+json">{"@type":"Article","dateModified":"2026-09-23"}</script>'
        "</head><body>" + ("<table><tr><td>British Airways Executive Club Avios</td><td>1.2 cents</td></tr></table>" * 15) + "</body></html>"
    )

    def setUp(self):
        import importlib
        import json
        import os
        import tempfile

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        import check_rrv
        importlib.reload(check_rrv)
        self.check_rrv = check_rrv

        def _mktemp():
            f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            f.close()
            os.unlink(f.name)
            return f.name

        self._orig = {
            "STATE_PATH": check_rrv.STATE_PATH,
            "VALUES_SNAPSHOT_PATH": check_rrv.VALUES_SNAPSHOT_PATH,
            "VALUATIONS_PATH": check_rrv.VALUATIONS_PATH,
            "CHANGELOG_PATH": check_rrv.CHANGELOG_PATH,
            "ROWS_PATH": check_rrv.ROWS_PATH,
        }
        check_rrv.STATE_PATH = _mktemp()
        check_rrv.VALUES_SNAPSHOT_PATH = _mktemp()
        check_rrv.VALUATIONS_PATH = _mktemp()
        check_rrv.CHANGELOG_PATH = _mktemp()
        check_rrv.ROWS_PATH = _mktemp()
        with open(check_rrv.ROWS_PATH, "w") as f:
            f.write("British Airways Executive Club Avios 1.1 cents\n")

        # An old baseline that will look "changed" against NEW_HTML's dateModified/table text.
        with open(check_rrv.STATE_PATH, "w") as f:
            json.dump({"date_modified": "2026-09-01", "values_hash": "old-hash", "value_count": 999,
                       "checked_on": "2026-09-01", "first_saved_on": "2026-09-01"}, f)
        with open(check_rrv.VALUES_SNAPSHOT_PATH, "w") as f:
            json.dump({"avios": 1.1, "cash": 1}, f)
        with open(check_rrv.VALUATIONS_PATH, "w") as f:
            json.dump({"values": {"avios": 1.2, "cash": 1}}, f)  # avios moved 1.1 -> 1.2; cash unchanged
        with open(check_rrv.CHANGELOG_PATH, "w") as f:
            f.write("What changed. Newest first.\n\n## 2026-09-20\n- An older entry.\n")

        class FakeHttpFetcher:
            def __init__(_self, *a, **k):
                pass

            def fetch(_self, url):
                from cardfinder.models import Page
                return Page(url=url, html=AckWritesTheChangelogTests.NEW_HTML)

        self._orig_fetcher = check_rrv.HttpFetcher
        check_rrv.HttpFetcher = FakeHttpFetcher

    def tearDown(self):
        import os

        for name, value in self._orig.items():
            path = getattr(self.check_rrv, name)
            setattr(self.check_rrv, name, value)
            if os.path.exists(path):
                os.unlink(path)
        self.check_rrv.HttpFetcher = self._orig_fetcher

    def test_ack_on_a_changed_page_logs_only_the_programs_that_actually_moved(self):
        import datetime
        import json

        exit_code = self.check_rrv.main(["--ack"])
        self.assertEqual(exit_code, 0)

        changelog = open(self.check_rrv.CHANGELOG_PATH).read()
        today = datetime.date.today().isoformat()
        self.assertIn(f"## {today}", changelog)
        self.assertIn("Updated the rankings to reflect changes to the value of Avios.", changelog)
        self.assertIn("## 2026-09-20\n- An older entry.", changelog)  # the old section is preserved, not overwritten

        snapshot = json.load(open(self.check_rrv.VALUES_SNAPSHOT_PATH))
        self.assertEqual(snapshot, {"avios": 1.2, "cash": 1})  # snapshot now matches valuations.json for next time

    def test_a_change_fails_once_with_the_changed_rows_then_stays_green_until_acked(self):
        import contextlib
        import io

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            first = self.check_rrv.main([])
        self.assertEqual(first, 1)
        self.assertIn("-British Airways Executive Club Avios 1.1 cents", out.getvalue())
        self.assertIn("+British Airways Executive Club Avios 1.2 cents", out.getvalue())

        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.check_rrv.main([]), 0)  # same page again: already flagged, not failed again
            self.assertEqual(self.check_rrv.main(["--ack"]), 0)
            self.assertEqual(self.check_rrv.main([]), 0)  # acked: now the baseline

    def test_ack_when_nothing_in_valuations_json_actually_changed_logs_nothing(self):
        import json

        with open(self.check_rrv.VALUATIONS_PATH, "w") as f:
            json.dump({"values": {"avios": 1.1, "cash": 1}}, f)  # matches the snapshot exactly

        self.check_rrv.main(["--ack"])

        changelog = open(self.check_rrv.CHANGELOG_PATH).read()
        self.assertNotIn("Updated the rankings", changelog)


if __name__ == "__main__":
    unittest.main()
