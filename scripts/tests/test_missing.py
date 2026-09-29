import json
import unittest

from cardfinder.check import CardResult
from cardfinder.discovery import Attempt
from cardfinder.missing import (SURGE, card_id_from_body, issue_body, issue_title, missing_document, plan_reports,
                                split_not_found)

ISSUER_OF = {"a": "usbank", "b": "usbank", "c": "usbank", "d": "usbank", "e": "chase", "f": "chase"}


def gone(cid):
    return CardResult(cid, f"Card {cid}", "not_found", attempts=[Attempt("known_url", f"https://x/{cid}", "wrong_page"),
                                                                Attempt("variant", f"https://x/{cid}/", "http_404"),
                                                                Attempt("sitemap", "", "no_candidates")])


def refused(cid):
    return CardResult(cid, f"Card {cid}", "not_found", attempts=[Attempt("known_url", f"https://x/{cid}", "http_403")])


class SplitNotFound(unittest.TestCase):
    def test_a_card_whose_every_attempt_said_not_there_is_reviewable(self):
        reviewable, unreadable = split_not_found([gone("a")], ISSUER_OF)
        self.assertEqual(([r.card_id for r in reviewable], unreadable), (["a"], []))

    def test_a_refused_or_errored_attempt_makes_it_unreadable_not_missing(self):
        for bad in (refused("a"), CardResult("a", "A", "not_found", attempts=[Attempt("known_url", "u", "error: timed out")])):
            reviewable, unreadable = split_not_found([bad], ISSUER_OF)
            self.assertEqual((reviewable, [r.card_id for r in unreadable]), ([], ["a"]))

    def test_no_attempts_at_all_is_not_evidence_the_card_is_gone(self):
        reviewable, unreadable = split_not_found([CardResult("a", "A", "not_found")], ISSUER_OF)
        self.assertEqual((reviewable, len(unreadable)), ([], 1))

    def test_found_and_skipped_cards_are_ignored(self):
        results = [CardResult("a", "A", "found"), CardResult("b", "B", "skipped")]
        self.assertEqual(split_not_found(results, ISSUER_OF), ([], []))

    def test_a_whole_issuer_going_missing_at_once_looks_like_a_redesign_or_block(self):
        many = [gone(c) for c in ("a", "b", "c", "d")]
        self.assertEqual(SURGE, 4)
        reviewable, unreadable = split_not_found(many + [gone("e")], ISSUER_OF)
        self.assertEqual([r.card_id for r in reviewable], ["e"])          # another issuer's single miss is still reviewable
        self.assertEqual(sorted(r.card_id for r in unreadable), ["a", "b", "c", "d"])

    def test_one_less_than_the_surge_is_still_reviewable(self):
        reviewable, unreadable = split_not_found([gone(c) for c in ("a", "b", "c")], ISSUER_OF)
        self.assertEqual((len(reviewable), unreadable), (3, []))


class IssueText(unittest.TestCase):
    ENTRY = {"id": "usbank-business-leverage", "name": "Business Leverage Visa Signature Card", "issuer": "usbank",
             "url": "https://www.usbank.com/x.html", "tried": [{"strategy": "known_url", "url": "https://www.usbank.com/x.html", "outcome": "wrong_page"}]}

    def test_body_carries_the_card_id_so_a_reply_can_be_tied_back_to_it(self):
        self.assertEqual(card_id_from_body(issue_body(self.ENTRY)), "usbank-business-leverage")

    def test_body_names_both_answers_and_what_was_tried(self):
        body = issue_body(self.ENTRY)
        for text in ("/discontinued", "/still-active", "known_url: https://www.usbank.com/x.html -> wrong_page", "mobile app"):
            self.assertIn(text, body)

    def test_title_names_the_card(self):
        self.assertEqual(issue_title("Business Leverage"), "Card not found: Business Leverage")

    def test_no_marker_means_no_card_id(self):
        self.assertIsNone(card_id_from_body("just a comment"))
        self.assertIsNone(card_id_from_body(None))


def issue(number, cid, state="OPEN", labels=(), closed_at=None):
    return {"number": number, "body": f"text\n<!-- card-id: {cid} -->\n", "state": state, "labels": list(labels), "closedAt": closed_at}


DOC = {"missing": [{"id": "a", "name": "A", "issuer": "usbank", "url": None, "tried": []},
                   {"id": "b", "name": "B", "issuer": "usbank", "url": None, "tried": []}], "found": ["z"]}


class PlanReports(unittest.TestCase):
    def test_every_missing_card_without_an_issue_gets_one(self):
        to_open, to_close = plan_reports(DOC, [], "2026-09-29")
        self.assertEqual(([m["id"] for m in to_open], to_close), (["a", "b"], []))

    def test_a_card_with_an_open_issue_is_not_raised_again_each_day(self):
        to_open, _ = plan_reports(DOC, [issue(7, "a")], "2026-09-29")
        self.assertEqual([m["id"] for m in to_open], ["b"])

    def test_still_active_snoozes_the_card_for_30_days_then_it_is_raised_again(self):
        answered = issue(7, "a", "CLOSED", ["card-missing", "still-active"], "2026-09-10T12:00:00Z")
        self.assertEqual([m["id"] for m in plan_reports(DOC, [answered], "2026-09-29")[0]], ["b"])
        self.assertEqual([m["id"] for m in plan_reports(DOC, [answered], "2026-10-15")[0]], ["a", "b"])

    def test_a_closed_issue_without_the_still_active_label_does_not_snooze(self):
        closed = issue(7, "a", "CLOSED", ["card-missing"], "2026-09-28T12:00:00Z")
        self.assertEqual([m["id"] for m in plan_reports(DOC, [closed], "2026-09-29")[0]], ["a", "b"])

    def test_an_open_issue_for_a_card_that_read_fine_this_run_is_closed_as_resolved(self):
        _, to_close = plan_reports(DOC, [issue(9, "z"), issue(7, "a")], "2026-09-29")
        self.assertEqual(to_close, [(9, "z")])

    def test_issues_with_no_marker_are_ignored(self):
        odd = {"number": 3, "body": "hand written", "state": "OPEN", "labels": [], "closedAt": None}
        self.assertEqual(len(plan_reports(DOC, [odd], "2026-09-29")[0]), 2)


class MissingDocument(unittest.TestCase):
    def test_shape(self):
        doc = missing_document([gone("a")], ["z", "y"], ISSUER_OF, {"a": "https://x/a"}, "2026-09-29")
        self.assertEqual(doc["found"], ["y", "z"])
        self.assertEqual(doc["missing"][0]["id"], "a")
        self.assertEqual(doc["missing"][0]["url"], "https://x/a")
        self.assertEqual(doc["missing"][0]["tried"][0], {"strategy": "known_url", "url": "https://x/a", "outcome": "wrong_page"})
        json.dumps(doc)


class ReportUsesGh(unittest.TestCase):
    """report_missing_cards.report() with a fake gh: no network, and it shows which commands would run."""

    def setUp(self):
        import os
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        import report_missing_cards
        self.mod = report_missing_cards
        self.calls = []

    def fake_gh(self, existing):
        def run(args):
            self.calls.append(args)
            return json.dumps(existing) if args[:2] == ["issue", "list"] else ""
        return run

    def test_opens_one_labelled_issue_per_missing_card(self):
        opened, closed = self.mod.report(DOC, "2026-09-29", run=self.fake_gh([]))
        self.assertEqual((opened, closed), (["Card not found: A", "Card not found: B"], []))
        creates = [c for c in self.calls if c[:2] == ["issue", "create"]]
        self.assertEqual(len(creates), 2)
        self.assertIn("card-missing", creates[0])

    def test_dry_run_only_lists_and_changes_nothing(self):
        opened, _ = self.mod.report(DOC, "2026-09-29", run=self.fake_gh([]), dry_run=True)
        self.assertEqual(len(opened), 2)
        self.assertTrue(all(c[:2] == ["issue", "list"] for c in self.calls))

    def test_closes_an_issue_whose_card_was_found_again(self):
        existing = [{"number": 9, "body": "<!-- card-id: z -->", "state": "OPEN", "labels": [{"name": "card-missing"}], "closedAt": None}]
        _, closed = self.mod.report(DOC, "2026-09-29", run=self.fake_gh(existing))
        self.assertEqual(closed, [9])
        self.assertTrue(any(c[:3] == ["issue", "close", "9"] for c in self.calls))


if __name__ == "__main__":
    unittest.main()
