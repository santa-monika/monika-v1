"""Crawler metadata java.waptai.com qua WordPress REST API (/wp-json/wp/v2/posts), ~10 yeu cau cho ~950 bai.
Khong tai file game o buoc nay (tai + go muc nhung la crawler.jarclean). Moi bai -> 1 JSON. Chay lai duoc:
bai khong doi (modified giong) thi giu nguyen."""
import argparse, html, json, os, re, sys
from urllib.parse import urlparse
from .common import Fetcher
from .filters import classify_vi
from .normalize import norm_title, resolution, strip_accents, variant_kind

BASE = "https://java.waptai.com"
API = BASE + "/wp-json/wp/v2/posts"
FIELDS = "id,date,modified,slug,link,title,content,excerpt,categories,tags"
OWN_HOST = "up.waptai.com"
FILE_EXT = {"jar", "jad", "apk", "sis", "sisx", "zip", "rar", "auto", "ipa", "cab", "exe"}

# id danh muc cua site -> (ten, loai noi dung Monika)
CATS = {
    58: ("Ảnh Girl Xinh", "hinh_nen"), 94: ("Hình nền", "hinh_nen"),
    12: ("Truyện Đôrêmon Chế", "truyen"),
    7: ("Phần Mềm Điện Thoại", "phan_mem"),
    124: ("Mẹo - Hướng dẫn", "meo"), 113: ("Tin Tức", "tin"),
    4: ("Game Online Mobile", "game_online"),
    5: ("Game Việt Hóa", "game"), 6: ("Game Điện Thoại", "game"), 28: ("Trò Chơi Di Động", "game"),
    14: ("GameLoft Tiếng Việt", "game"), 1: ("Game Mobile", "game"), 109: ("Featured", None),
    8: ("Game Hành Động", "game"), 9: ("Game Vui Nhộn", "game"), 10: ("Game Chiến Thuật", "game"),
    11: ("Game Thể Thao", "game"), 143: ("Game Phiêu Lưu", "game"), 144: ("Game Nhập Vai", "game"),
    145: ("Game Giải Đố", "game"), 146: ("Game Đua Xe", "game"), 147: ("Game Sinh Tồn", "game"),
}
# thu tu uu tien khi bai thuoc nhieu danh muc
KIND_ORDER = ["game_online", "truyen", "hinh_nen", "phan_mem", "meo", "tin", "game"]
GENRE_CATS = {8, 9, 10, 11, 143, 144, 145, 146, 147}

ONLINE_TITLE = re.compile(r"\bonline\b|\bmmo\b|\bmu\s*online\b", re.I)
HACKMOD = re.compile(r"\b(hack|hacked|mod|cheat|crack(ed)?)\b", re.I)
ONLINE_TEXT = re.compile(r"game\s*online|choi\s*online\s*(voi|cung)\s*nguoi|can\s*(ket\s*noi\s*)?(mang|internet|gprs|3g)|server\b|may\s*chu", re.I)


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def kind_of(cat_ids):
    ks = {CATS[c][1] for c in cat_ids if c in CATS and CATS[c][1]}
    for k in KIND_ORDER:
        if k in ks:
            return k
    return "game"


def parse_size_kb(txt):
    """'(1836.25 KB)' | '(2,7M)' | '(1.2 MB)' -> KB (int) hoac None."""
    m = re.search(r"\(\s*([\d.,]+)\s*(KB|kB|MB|M|Mb|mb)\b", txt or "")
    if not m:
        return None
    v = float(m.group(1).replace(",", "."))
    return int(round(v * (1024 if m.group(2).lower() in ("mb", "m") else 1)))


def parse_info(content):
    info = {}
    for li in re.findall(r"<li>(.*?)</li>", content, re.S):
        t = clean(li)
        k, sep, v = t.partition(":")
        if sep and len(k) < 30:
            info[k.strip()] = v.strip()
    return info


def parse_downloads(content):
    """Moi <a href> tro toi file (jar/jad/apk/...). Trong khoi div.game lay them dong 'Ho Tro May Tuong Tu' (may mau)."""
    models = {}
    for blk in re.findall(r'<div class=[\'"]game[\'"][^>]*>(.*?)</div>', content, re.S):
        head = clean(blk.split("<br", 1)[0])
        head = re.sub(r"^Hỗ Trợ Máy Tương Tự:\s*", "", head)
        for u in re.findall(r'href=[\'"]([^\'"]+)[\'"]', blk):
            models[html.unescape(u)] = head
    out, seen = [], set()
    for m in re.finditer(r'<a\s[^>]*href=[\'"](https?://[^\'"]+)[\'"][^>]*>(.*?)</a>(?=(.{0,80}))', content, re.S):
        url, label, after = html.unescape(m.group(1)), clean(m.group(2)), clean(re.split(r"<a\b|</div>|<br", m.group(3))[0])
        u = urlparse(url)
        last = u.path.rsplit("/", 1)[-1]
        ext = last.rsplit(".", 1)[-1].lower() if "." in last else ""
        if ext not in FILE_EXT or url in seen:
            continue
        seen.add(url)
        out.append({"url": url, "label": label, "ext": ext, "host": u.netloc, "own_host": u.netloc == OWN_HOST,
                    "resolution": resolution(url) or resolution(label), "size_kb": parse_size_kb(after),
                    "kind": variant_kind(label, last), "models": models.get(url, "")})
    return out


def parse_images(content):
    """Anh trong bai: uu tien link anh goc (the <a> bao quanh), roi src. Bo anh giao dien."""
    imgs, seen = [], set()
    for m in re.finditer(r'(?:<a\s[^>]*href=["\']([^"\']+\.(?:jpe?g|png|gif))["\'][^>]*>\s*)?<img\s[^>]*?src=["\']([^"\']+)["\'][^>]*?>', content, re.S):
        full, src = m.group(1), m.group(2)
        tag = m.group(0)
        alt = re.search(r'alt=["\']([^"\']*)["\']', tag)
        url = html.unescape(full or src)
        if url in seen:
            continue
        seen.add(url)
        wh = (re.search(r'width="(\d+)"', tag), re.search(r'height="(\d+)"', tag))
        imgs.append({"src": url, "alt": clean(alt.group(1)) if alt else "",
                     "w": int(wh[0].group(1)) if wh[0] else None, "h": int(wh[1].group(1)) if wh[1] else None})
    return imgs


def parse_comic(content):
    return [{"src": html.unescape(src), "caption": clean(cap)}
            for src, cap in re.findall(r'<figure class="comic-page"><img[^>]*?src="([^"]+)"[^>]*/?>\s*<figcaption>(.*?)</figcaption>', content, re.S)]


def online_filter(cat_ids, title, text):
    """Loai game online va mod/hack game online theo yeu cau cua sep. Tra (status, ly_do)."""
    why = []
    if 4 in cat_ids:
        why.append("danh muc Game Online Mobile")
    t = strip_accents(title or "")
    if ONLINE_TITLE.search(t):
        why.append("tieu de co online")
    if why:
        return "loai", why
    body = strip_accents(text or "")
    if HACKMOD.search(t) and ONLINE_TEXT.search(body):
        return "loai", ["hack/mod + noi dung game online"]
    if HACKMOD.search(t):
        return "duyet", ["hack/mod (chua ro online hay offline)"]
    return "ok", []


def parse_post(p):
    content = p["content"]["rendered"]
    title = clean(p["title"]["rendered"])
    cats = p.get("categories", [])
    kind = kind_of(cats)
    text = clean(re.sub(r"<(figure|div class=\"javagame\"|iframe)\b.*?</\1>|<iframe.*?</iframe>", " ", content, flags=re.S))
    r = {"source": "waptai", "source_id": p["id"], "page_url": p["link"], "slug": p["slug"], "title": title,
         "date": p["date"], "modified": p["modified"], "kind": kind,
         "categories": [CATS[c][0] if c in CATS else str(c) for c in cats],
         "genres": [CATS[c][0] for c in cats if c in GENRE_CATS],
         "info": parse_info(content),
         "description_private": text[:2500],
         "images": parse_images(content),
         "downloads": parse_downloads(content),
         "norm_title": norm_title(title)}
    if kind == "truyen":
        r["comic_pages"] = parse_comic(content)
    own = [d for d in r["downloads"] if d["own_host"] and d["ext"] in ("jar", "apk", "jad", "sis", "sisx", "zip")]
    r["has_own_file"] = bool(own)
    status, why = classify_vi(title, text[:1500], "")
    if kind in ("game", "game_online", "phan_mem", "truyen", "meo", "tin"):
        o_status, o_why = online_filter(cats, title, text)
        if o_status == "loai" or (o_status == "duyet" and status == "ok"):
            status, why = o_status, o_why
    if kind == "hinh_nen":
        # anh nguoi mau: luon cho nguoi duyet, ghi them tu khoa nhay cam neu co
        status, why = ("loai", why) if status == "loai" else ("duyet", ["anh nguoi mau, can duyet"] + why)
    r["filter"] = {"status": status, "reasons": why}
    return r


def fetch_page(fetcher, page, per_page=100):
    url = f"{API}?per_page={per_page}&page={page}&orderby=id&order=asc&_fields={FIELDS}"
    return json.loads(fetcher.get(url))


def crawl(outdir, fetcher, max_pages=None, force=False):
    pdir = os.path.join(outdir, "waptai", "posts")
    os.makedirs(pdir, exist_ok=True)
    new = upd = same = 0
    page = 1
    while True:
        try:
            posts = fetch_page(fetcher, page)
        except Exception as e:
            if "400" in str(e) or "rest_post_invalid_page_number" in str(e):
                break  # het trang
            raise
        for p in posts:
            path = os.path.join(pdir, f"{p['id']}.json")
            old = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
            if old and old.get("modified") == p["modified"] and not force:
                same += 1
                continue
            r = parse_post(p)
            if old:
                for k in ("local", "thumbs"):  # giu ket qua cac buoc sau (jar da lam sach, anh thu nho)
                    if k in old:
                        r[k] = old[k]
            json.dump(r, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            upd += bool(old)
            new += not old
        if len(posts) < 100 or (max_pages and page >= max_pages):
            break
        page += 1
    return new, upd, same


def summary(outdir):
    import collections, glob
    c = collections.Counter()
    for f in glob.glob(os.path.join(outdir, "waptai", "posts", "*.json")):
        r = json.load(open(f, encoding="utf-8"))
        c[(r["kind"], r["filter"]["status"])] += 1
    return c


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="thu muc dau ra (repo du lieu rieng, thu muc data)")
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--max-pages", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    f = Fetcher(delay=a.delay)
    new, upd, same = crawl(a.out, f, a.max_pages, a.force)
    print(f"xong: {new} moi, {upd} cap nhat, {same} giu nguyen, {f.requests} yeu cau")
    for (kind, st), n in sorted(summary(a.out).items()):
        print(f"  {kind:12s} {st:6s} {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
