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

    def test_a_different_date_alone_is_also_changed(self):
        from cardfinder.rrv_check import RrvSnapshot
        prev = {"date_modified": "2026-09-02", "values_hash": "abc"}
        outcome, code = decide(prev, RrvSnapshot(date_modified="2026-09-03", values_hash="abc", value_count=30, readable=True))
        self.assertEqual((outcome, code), ("changed", 1))

    def test_an_unreadable_page_is_its_own_outcome_never_reported_as_unchanged(self):
        from cardfinder.rrv_check import RrvSnapshot
        prev = {"date_modified": "2026-09-02", "values_hash": "abc"}
        outcome, code = decide(prev, RrvSnapshot(date_modified=None, values_hash=None, value_count=0, readable=False))
        self.assertEqual((outcome, code), ("unreadable", 2))


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


if __name__ == "__main__":
    unittest.main()
