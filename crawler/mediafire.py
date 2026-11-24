"""MediaFire: tach link tu bai Blogger, mo thu muc/tep qua API cong khai (co sha256, dung luong, revision), tai tep co kiem tra sha256.
Lich su: moi yeu cau cach nhau >= delay giay; 429/503 thi dung (khong lach)."""
import hashlib, html, json, re, time, urllib.error, urllib.parse, urllib.request
from .common import UA, RateLimited

API = "https://www.mediafire.com/api/1.5"
KEY = r"([0-9a-z]{9,16})"
FILE_RE = re.compile(r"https?://(?:www\.|app\.)?mediafire\.com/(?:file(?:_premium)?|view|download)/" + KEY, re.I)
FILE_Q_RE = re.compile(r"https?://(?:www\.)?mediafire\.com/\?" + KEY, re.I)
FOLDER_RE = re.compile(r"https?://(?:www\.|app\.)?mediafire\.com/folder/" + KEY, re.I)
DIRECT_RE = re.compile(r"https?://download\d*\.mediafire\.com/[^\"'\s]+/" + KEY + r"/[^\"'\s]+", re.I)
BTN_RE = re.compile(r'id="downloadButton"[^>]*?href="([^"]+)"|href="([^"]+)"[^>]*?id="downloadButton"', re.I)
_last = [0.0]


def link_key(href):
    """-> ('file'|'folder', khoa) hoac None."""
    for kind, rx in (("folder", FOLDER_RE), ("file", FILE_RE), ("file", FILE_Q_RE), ("file", DIRECT_RE)):
        m = rx.search(href or "")
        if m:
            return kind, m.group(1).lower()
    return None


def _get(url, delay=1.0, timeout=60, binary=False):
    gap = time.time() - _last[0]
    if gap < delay:
        time.sleep(delay - gap)
    _last[0] = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout) as r:
            b = r.read()
            return b if binary else b.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code in (429, 503):
            ra = e.headers.get("Retry-After") if e.headers else None
            raise RateLimited(url, int(ra) if ra and ra.isdigit() else None)
        raise


def _api(path, delay=1.0, **q):
    q["response_format"] = "json"
    r = json.loads(_get(f"{API}/{path}.php?" + urllib.parse.urlencode(q), delay))["response"]
    if r.get("result") != "Success":
        raise ValueError(f"{r.get('error') or r.get('message') or 'loi API'} (ma {r.get('error')})")
    return r


def _rec(f):
    return {"qk": f["quickkey"], "fn": f["filename"], "size": int(f.get("size") or 0), "mf_sha": f.get("hash", ""),
            "rev": f.get("revision", ""), "created": (f.get("created_utc") or f.get("created") or "")[:10], "mime": f.get("mimetype", "")}


def file_info(qk, delay=1.0):
    return _rec(_api("file/get_info", delay, quick_key=qk)["file_info"])


def folder_files(fk, delay=1.0, depth=2):
    """Moi tep trong thu muc (di vao thu muc con toi `depth` cap)."""
    out = []
    for chunk in range(1, 20):
        r = _api("folder/get_content", delay, folder_key=fk, content_type="files", chunk_size=200, chunk=chunk)["folder_content"]
        out += [_rec(f) for f in r.get("files", [])]
        if r.get("more_chunks") != "yes":
            break
    if depth > 0:
        sub = _api("folder/get_content", delay, folder_key=fk, content_type="folders", chunk_size=100)["folder_content"].get("folders", [])
        for s in sub[:30]:
            out += folder_files(s["folderkey"], delay, depth - 1)
    return out


def direct_url(qk, delay=1.0):
    """Trang tep -> link tai truc tiep (nut Download). Tra None neu tep bi go/chua san sang."""
    page = _get(f"https://www.mediafire.com/file/{qk}/x/file", delay)
    m = BTN_RE.search(page)
    if not m:
        return None
    u = html.unescape(m.group(1) or m.group(2))
    return u if u.startswith("http") else None


def download(qk, delay=2.0, expect_sha=None):
    """-> bytes. Kiem tra sha256 neu co (lech thi thu lai 1 lan, van lech thi bao loi)."""
    for attempt in (0, 1):
        u = direct_url(qk, delay)
        if not u:
            raise ValueError("khong co nut tai (tep bi go hoac cho quet)")
        raw = _get(u, delay, timeout=180, binary=True)
        if raw[:15].lower().startswith(b"<!doctype html") or raw[:6].lower() == b"<html>":
            raise ValueError("MediaFire tra trang HTML thay vi tep")
        if not expect_sha or hashlib.sha256(raw).hexdigest() == expect_sha:
            return raw
    raise ValueError("sha256 lech so voi API MediaFire")
