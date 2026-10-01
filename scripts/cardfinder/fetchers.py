"""Ways to get a page: plain HTTP, or a real browser for pages that need their scripts to run."""
import time
import urllib.error
import urllib.request

from .models import FetchError, Page

USER_AGENT = "churning-card-finder-maintainer/0.1 (personal use, low volume)"
# Hotel sites (IHG's, for one) refuse the maintainer user agent and Playwright's default headless build outright, and
# serve the page to an ordinary Chrome user agent in Chromium's "new" headless mode. Used only for those sites.
BROWSER_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
RETRYABLE = lambda code: code == 429 or code >= 500


class HttpFetcher:
    """Polite plain HTTP: a pause between requests, retries with backoff for transient failures.

    A 404 (or any other client error) is a real answer and is not retried.
    """

    def __init__(self, delay=1.0, retries=2, timeout=30, opener=urllib.request.urlopen, sleep=time.sleep):
        self.delay, self.retries, self.timeout = delay, retries, timeout
        self.opener, self.sleep = opener, sleep
        self._first = True

    def fetch(self, url):
        if not self._first:
            self.sleep(self.delay)
        self._first = False
        last = None
        for attempt in range(self.retries + 1):
            if attempt:
                self.sleep(self.delay * 2 ** (attempt - 1))
            try:
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with self.opener(request, timeout=self.timeout) as resp:
                    return Page(url=resp.geturl(), html=resp.read().decode("utf-8", errors="replace"))
            except urllib.error.HTTPError as e:
                last = FetchError(e.code, f"HTTP {e.code} for {url}")
                if not RETRYABLE(e.code):
                    raise last
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last = FetchError(None, f"{type(e).__name__}: {e}")
        raise last


class RenderedFetcher:
    """Loads a page in a headless browser (Playwright) and returns the HTML after scripts ran.

    Optional: use available() first. Keeps one browser open across calls; call close() when done.
    """

    def __init__(self, wait_ms=3500, timeout_ms=60000, user_agent=USER_AGENT, channel=None):
        self.wait_ms, self.timeout_ms = wait_ms, timeout_ms
        self.user_agent, self.channel = user_agent, channel
        self._pw = self._browser = None

    @staticmethod
    def available():
        try:
            import playwright.sync_api  # noqa: F401
            return True
        except ImportError:
            return False

    def _start(self):
        if self._browser is None:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True, **({"channel": self.channel} if self.channel else {}))

    def fetch(self, url):
        try:
            self._start()
            page = self._browser.new_page(user_agent=self.user_agent)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                page.wait_for_timeout(self.wait_ms)
                return Page(url=page.url, html=page.content())
            finally:
                page.close()
        except Exception as e:  # browser missing, navigation failure, timeout
            raise FetchError(None, f"render failed: {type(e).__name__}: {e}")

    def close(self):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._pw = self._browser = None


class CachingFetcher:
    """Remembers every result, including failures, so a sitemap or listing page is fetched once per run
    however many cards need it."""

    def __init__(self, inner):
        self.inner = inner
        self._cache = {}

    def fetch(self, url):
        if url not in self._cache:
            try:
                self._cache[url] = self.inner.fetch(url)
            except FetchError as e:
                self._cache[url] = e
        result = self._cache[url]
        if isinstance(result, FetchError):
            raise result
        return result
