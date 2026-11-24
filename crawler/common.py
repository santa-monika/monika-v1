"""Tai trang HTTP lich su: gioi han toc do, thu lai, khong in noi dung ra log."""
import time, urllib.request, urllib.error

UA = "Mozilla/5.0 (compatible; MonikaIndexBot/0.1)"


class RateLimited(RuntimeError):
    """Server tra 429: dung ngay, khong thu lai (ton trong gioi han cua site). retry_after tinh bang giay."""
    def __init__(self, url, retry_after):
        super().__init__(f"429 rate limited: {url} (retry-after {retry_after}s)")
        self.retry_after = retry_after


class Fetcher:
    def __init__(self, delay=2.0, retries=3, timeout=30):
        self.delay, self.retries, self.timeout = delay, retries, timeout
        self._last = 0.0
        self.requests = 0

    def _wait(self):
        gap = time.time() - self._last
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self._last = time.time()

    def get(self, url, data=None, binary=False):
        err = None
        for attempt in range(self.retries):
            self._wait()
            self.requests += 1
            try:
                req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    body = r.read()
                    return body if binary else body.decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                err = e
                if e.code == 429:
                    ra = e.headers.get("Retry-After") if e.headers else None
                    raise RateLimited(url, int(ra) if ra and ra.isdigit() else None)
                if e.code in (404, 410):
                    raise
                time.sleep(5 * (attempt + 1))
            except Exception as e:  # mang, timeout
                err = e
                time.sleep(5 * (attempt + 1))
        raise RuntimeError(f"fetch failed after {self.retries} tries: {url}: {err}")
