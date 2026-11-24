"""Crawl quangninhwap.com (wap portal tren xtgem): chi metadata + danh sach link tai (jar/jad/sis/apk/zip) tro sang host ngoai.
Chi di theo link noi bo thuoc cac muc game/ung dung/thu thuat/truyen; bo qua game online, kqxs, xem boi, bong da, anh girl...
Ghi data/quangninhwap/pages/<slug>.json (ban nho), crawl lai duoc (trang da co bo qua neu --resume)."""
import argparse, html, json, os, re, sys, urllib.parse
from .common import Fetcher, RateLimited

BASE = "http://quangninhwap.com"
ALLOW = ("tai-game", "game-viet-hoa", "game-", "tai-ung-dung", "ban-do-dien-thoai", "android", "tai-theme", "tai-hinh-nen",
         "thu-thuat-dien-thoai", "meo-vat", "tien-ich", "tai-nhac-chuong", "tai-opera-mini", "truyen-cuoi", "truyen-tinh-yeu",
         "Ung20dung20hay", "hinh-nen", "anh-", "icon-dep", "tai-flash-dep", "tao-hinh-nen")
DENY = ("online", "kqxs", "xemboi", "xem-phim", "bong-da", "girl", "gioitinh", "iwin", "bigkool", "avatar", "gopet", "hoang-de",
        "dieu-khoan", "chinh-sach", "su-dung", "gioi-thieu", "lien-ket", "huong-dan-lam-wap", "tin-nhan", "old", "van-mau",
        "nhac-mp3", "me-hai-ola")
FILE_EXT = ("jar", "jad", "sis", "sisx", "apk", "zip", "rar", "thm", "nth", "mp3", "swf")


def norm(u, cur=BASE + "/"):
    u = urllib.parse.urljoin(cur, html.unescape(u.strip()))
    p = urllib.parse.urlsplit(u)
    if p.netloc.replace("www.", "") != "quangninhwap.com":
        return None
    path = p.path.rstrip("/") or "/"
    return BASE + path


def wanted(path):
    seg = path.strip("/")
    if not seg or any(d in seg.lower() for d in DENY):
        return False
    return seg.startswith(ALLOW)


def parse(page_html, url):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", page_html, flags=re.S)
    title = html.unescape(re.sub(r"<[^>]+>", "", (re.search(r"<title>(.*?)</title>", t, re.S) or [0, ""])[1])).strip()
    i = t.find("<body")
    body = t[i:] if i >= 0 else t
    links, files, imgs = [], [], []
    for m in re.finditer(r'<a\b[^>]*?href="([^"]*)"[^>]*>(.*?)</a>', body, re.S):
        href, label = m.group(1), html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        full = urllib.parse.urljoin(url, html.unescape(href))
        path = urllib.parse.urlsplit(full).path
        ext = path.rsplit(".", 1)[-1].lower() if "." in path.rsplit("/", 1)[-1] else ""
        if ext in FILE_EXT or re.search(r"\.(jar|zip|rar|sis)\b", full, re.I):
            files.append({"url": full, "label": label, "ext": ext})
        else:
            links.append({"url": full, "label": label})
    for m in re.finditer(r'<img\b[^>]*?src="([^"]+)"', body):
        imgs.append(urllib.parse.urljoin(url, html.unescape(m.group(1))))
    text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))).strip()
    return {"url": url, "title": title, "text": text[:4000], "files": files, "links": links, "images": imgs[:10]}


def slug(url):
    return re.sub(r"[^A-Za-z0-9._-]", "_", urllib.parse.urlsplit(url).path.strip("/") or "home")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--max-pages", type=int, default=800)
    ap.add_argument("--seeds", default="/tai-game,/tai-ung-dung,/tai-theme,/tai-hinh-nen,/thu-thuat-dien-thoai,/truyen-cuoi,/truyen-tinh-yeu,/game-viet-hoa,/ban-do-dien-thoai,/android,/meo-vat/cuoc-song,/tien-ich")
    a = ap.parse_args(argv)
    d = os.path.join(a.out, "quangninhwap", "pages")
    os.makedirs(d, exist_ok=True)
    f = Fetcher(delay=a.delay)
    queue = [BASE + s for s in a.seeds.split(",")]
    seen, done = set(queue), 0
    while queue and done < a.max_pages:
        u = queue.pop(0)
        path = os.path.join(d, slug(u) + ".json")
        if os.path.exists(path):
            rec = json.load(open(path, encoding="utf-8"))
        else:
            try:
                rec = parse(f.get(u), u)
            except RateLimited as e:
                print("429, dung:", e, file=sys.stderr)
                return 3
            except Exception as e:
                print("loi", u, type(e).__name__, e, file=sys.stderr)
                continue
            json.dump(rec, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        done += 1
        for l in rec["links"]:
            n = norm(l["url"])
            if n and n not in seen and wanted(urllib.parse.urlsplit(n).path):
                seen.add(n)
                queue.append(n)
        if done % 25 == 0:
            print(f"{done} trang, hang doi {len(queue)}", flush=True)
    print(f"xong: {done} trang, con {len(queue)} trong hang doi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
