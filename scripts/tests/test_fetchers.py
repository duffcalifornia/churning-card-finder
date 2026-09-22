import unittest
import urllib.error

from cardfinder.fetchers import HttpFetcher, CachingFetcher
from cardfinder.models import FetchError


class Response:
    def __init__(self, body, url):
        self.body, self.url = body, url

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self.body.encode()

    def geturl(self):
        return self.url


class ScriptedOpener:
    """Returns or raises the next scripted outcome for each call."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def __call__(self, request, timeout=None):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return Response(outcome, request.full_url)


def http_error(code):
    return urllib.error.HTTPError("https://ex.com/x", code, "err", {}, None)


class HttpFetcherTests(unittest.TestCase):
    def make(self, *outcomes, **kw):
        self.sleeps = []
        self.opener = ScriptedOpener(*outcomes)
        return HttpFetcher(opener=self.opener, sleep=self.sleeps.append, **kw)

    def test_returns_the_page(self):
        page = self.make("<html>hi</html>").fetch("https://ex.com/a")
        self.assertEqual((page.url, page.html), ("https://ex.com/a", "<html>hi</html>"))

    def test_404_is_not_retried(self):
        f = self.make(http_error(404))
        with self.assertRaises(FetchError) as cm:
            f.fetch("https://ex.com/a")
        self.assertEqual(cm.exception.status, 404)
        self.assertEqual(self.opener.calls, 1)

    def test_transient_server_error_is_retried_then_succeeds(self):
        f = self.make(http_error(503), "<html>ok</html>", retries=2)
        self.assertEqual(f.fetch("https://ex.com/a").html, "<html>ok</html>")
        self.assertEqual(self.opener.calls, 2)

    def test_rate_limit_is_retried(self):
        f = self.make(http_error(429), "<html>ok</html>", retries=1)
        self.assertEqual(f.fetch("https://ex.com/a").html, "<html>ok</html>")

    def test_network_error_is_retried(self):
        f = self.make(urllib.error.URLError("dns"), "<html>ok</html>", retries=1)
        self.assertEqual(f.fetch("https://ex.com/a").html, "<html>ok</html>")

    def test_gives_up_after_the_configured_retries(self):
        f = self.make(http_error(500), http_error(500), http_error(500), retries=2)
        with self.assertRaises(FetchError) as cm:
            f.fetch("https://ex.com/a")
        self.assertEqual(cm.exception.status, 500)
        self.assertEqual(self.opener.calls, 3)

    def test_waits_between_successive_requests(self):
        f = self.make("<a/>", "<b/>", delay=1.5)
        f.fetch("https://ex.com/a")
        f.fetch("https://ex.com/b")
        self.assertIn(1.5, self.sleeps)

    def test_backoff_grows_between_retries(self):
        f = self.make(http_error(500), http_error(500), "<ok/>", retries=2, delay=1.0)
        f.fetch("https://ex.com/a")
        waits = [s for s in self.sleeps if s > 0]
        self.assertEqual(waits, sorted(waits))
        self.assertGreater(max(waits), min(waits))


class CountingInner:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def fetch(self, url):
        self.calls.append(url)
        v = self.pages.get(url)
        if v is None:
            raise FetchError(404, "404")
        return v if not isinstance(v, str) else __import__("cardfinder.models", fromlist=["Page"]).Page(url, v)


class CachingFetcherTests(unittest.TestCase):
    def test_second_request_for_the_same_url_is_served_from_the_cache(self):
        inner = CountingInner({"https://ex.com/a": "<a/>"})
        c = CachingFetcher(inner)
        self.assertEqual(c.fetch("https://ex.com/a").html, "<a/>")
        self.assertEqual(c.fetch("https://ex.com/a").html, "<a/>")
        self.assertEqual(inner.calls, ["https://ex.com/a"])

    def test_failures_are_cached_too_so_a_dead_sitemap_is_not_retried_per_card(self):
        inner = CountingInner({})
        c = CachingFetcher(inner)
        for _ in range(3):
            with self.assertRaises(FetchError):
                c.fetch("https://ex.com/gone")
        self.assertEqual(len(inner.calls), 1)

    def test_different_urls_are_fetched_separately(self):
        inner = CountingInner({"https://ex.com/a": "a", "https://ex.com/b": "b"})
        c = CachingFetcher(inner)
        c.fetch("https://ex.com/a")
        c.fetch("https://ex.com/b")
        self.assertEqual(len(inner.calls), 2)


if __name__ == "__main__":
    unittest.main()
