"""Danh muc tep S60 (.sis/.sisx), theme (.nth), hinh nen (anh) va nhac chuong (.mp3) tu quangninhwap (trang da crawl), giaitri321 va wapvip (CDX archive.org).
Moi dong: src, url, ts, via, file, title, group, res, plat, kind (s60game|s60app|theme|wallpaper|ringtone), album (hinh nen/nhac chuong: ten thu muc), section.
Loai: 18+ (bikini, sexy, hot girl...), game online/mod, thu muc anh trang tri cua site (images, icon, banner, smile, css...). files/luutru va files/tap-tin cua wapvip khong lay (quyet dinh truoc day).
Xuat data/inventory/media.jsonl va media-excluded.jsonl."""
import argparse, glob, json, os, re, sys, urllib.parse
from .filters import classify
from .normalize import strip_accents
from .inventory import ONLINE_MOD, clean_title, group_key, make, cdx_rows

IMG = ("jpg", "jpeg", "png", "gif")
ADULT = re.compile(r"(bikini|sexy|\bsex\b|nude|goi[\s_-]*cam|hot[\s_-]*girl|girl[\s_-]*hot|nong[\s_-]*bong|nguc|lingerie|\bbody\b|18\+|\bxxx\b|"
                   r"hot[\s_-]*boy|do[\s_-]*lot|mong|vu[\s_-]*to)", re.I)
DECOR = re.compile(r"(^|/)(images?|img|icons?|banner|smileys?|smile|css|javascript|thumbs?|avatar|anh[\s_-]*dai[\s_-]*dien|tin[\s_-]*tuc|truyen|"
                   r"download|pic|file|attach|upload)(/|$)", re.I)
WP_DIR_WVIP = re.compile(r"^chuyen-muc/(nhacchuonghinhnen|hinhanh)/([^/]+)/[^/]+$")
RING_WVIP = re.compile(r"^chuyen-muc/(nhacchuonghinhnen|nhacchuong|nhac[^/]*)/([^/]+)/[^/]+\.mp3$", re.I)
S60_SECTION_PLAT = [(r"s60v?5|symbian[\s_-]*3|touch|cam[\s_-]*ung|5800|5230|n8|c7|v5", "s60v5"),
                    (r"s60v?3|symbian[\s_-]*9|n95|n73|e71|e72|os9", "s60v3"),
                    (r"s60v?2|s60v?1|176x208|nokia[\s_-]*6600|n70|os[67]", "s60v2")]


def sis_plat(path):
    t = strip_accents(urllib.parse.unquote(path)).lower()
    for rx, p in S60_SECTION_PLAT:
        if re.search(rx, t):
            return p
    return "s60"  # chua ro doi may: de trong, Worker xep vao S60 chung


def mk(src, url, file, via, kind, ts=None, album="", section="", label="", slug=None):
    it = make(src, url, file, via, ts=ts, slug=slug, section=section, kind="game", label=label)
    it["kind"] = kind
    it["album"] = album
    ext = file.rsplit(".", 1)[-1].lower() if "." in file else ""
    it["ext"] = ext
    if kind in ("s60game", "s60app") or (kind == "theme" and ext in ("sis", "sisx")):
        it["plat"] = sis_plat(f"{section} {file}")
    elif kind == "theme":
        it["plat"] = "nokia"
    else:
        it["plat"] = ""
    if kind == "wallpaper" and album:
        it["group"] = group_key(album)
    return it


def qnw(data):
    out = []
    for p in sorted(glob.glob(os.path.join(data, "quangninhwap", "pages", "*.json"))):
        r = json.load(open(p, encoding="utf-8"))
        sect = os.path.basename(p)[:-5]
        for f in r.get("files") or []:
            ext = (f.get("ext") or "").lower()
            if ext not in ("sis", "sisx", "nth"):
                continue
            u = f["url"].replace("http://www.", "http://")
            if u in {x["url"] for x in out[-300:]}:
                continue
            file = u.rsplit("/", 1)[-1]
            if ext == "nth" or sect.startswith(("tai-theme", "hinh-nen")):
                kind = "theme"
            elif sect.startswith(("tai-game", "game")):
                kind = "s60game"
            else:
                kind = "s60app"
            if sect.startswith(("thu-thuat",)):
                continue  # file huong dan/hack, khong phai noi dung de dang
            out.append(mk("qnw", u, file, "xtgem", kind, section=sect, label=f.get("label", "")))
        # hinh nen: moi trang con la 1 anh, link "Tai ve may" tro toi tep anh
        if sect.startswith(("hinh-nen", "anh-", "tai-hinh-nen", "icon-dep")):
            for l in r.get("links") or []:
                u = l.get("url", "")
                if re.search(r"/img/[^/]+\.(jpe?g|png|gif)$", u, re.I) and "quangninhwap.com" in u:
                    album = sect.split("_")[0]
                    out.append(mk("qnw", u.replace("http://www.", "http://"), u.rsplit("/", 1)[-1], "direct", "wallpaper", album=album, section=sect))
    seen, res = set(), []
    for it in out:
        if it["url"] not in seen:
            seen.add(it["url"]); res.append(it)
    return res


def cdx(data, site, src, base):
    out, seen = [], set()
    for r in cdx_rows(data, site):
        if not str(r["s"]).startswith("2") or r["m"] == "text/html":
            continue
        u = urllib.parse.urlsplit(r["u"])
        path = urllib.parse.unquote(u.path).lstrip("/")
        low = path.lower()
        ext = low.rsplit(".", 1)[-1] if "." in low else ""
        if ext not in ("sis", "sisx", "nth", "mp3") + IMG:
            continue
        if low.startswith(("files/luutru", "files/tap-tin", "files/hinh-anh")):
            continue
        key = low
        if key in seen:
            continue
        seen.add(key)
        parts = path.split("/")
        album = ""
        kind = None
        if ext in ("sis", "sisx"):
            if "theme" in low:
                kind = "theme"
            elif src == "wvip":
                kind = "s60app" if ("ungdung" in low or "soft" in low) else "s60game"
            else:
                kind = "s60app" if low.startswith(("soft/", "tienich")) else "s60game"
        elif ext == "nth":
            kind = "theme"
        elif ext == "mp3":
            if src == "wvip":
                m = RING_WVIP.match(path)
                if m:
                    kind, album = "ringtone", m.group(2)
            elif low.startswith("media/nhacchuong/"):
                kind, album = "ringtone", parts[2] if len(parts) > 3 else "nhac-chuong"
        elif ext in IMG:
            if src == "wvip":
                m = WP_DIR_WVIP.match(path)
                if m and not DECOR.search("/".join(parts[2:-1])):
                    kind, album = "wallpaper", m.group(2)
            elif low.startswith("media/hinhnen/") and len(parts) >= 4:
                kind, album = "wallpaper", "hinh-nen-" + parts[2]
        if not kind:
            continue
        slug = None
        if kind == "theme" and ext == "nth":
            album = "/".join(parts[:-1])  # theo thu muc (gom theo man hinh/chuyen muc)
        out.append(mk(src, f"{base}/{path}", parts[-1], "archive", kind, ts=r["t"], album=album, section="/".join(parts[:3])))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    a = ap.parse_args(argv)
    items = qnw(a.data) + cdx(a.data, "giaitri321.pro", "gt321", "http://giaitri321.pro") + cdx(a.data, "wapvip.pro", "wvip", "http://wapvip.pro")
    keep, drop = [], []
    for it in items:
        text = strip_accents(f"{it['title']} {it['file']} {it['section']} {it['album']}")
        why = None
        if ADULT.search(text):
            why = "18+ (ten/thu muc)"
        else:
            st, w = classify(it["title"] + " " + it["album"], it["file"])
            if st == "loai":
                why = f"18+/co bac {w[:2]}"
        if not why and it["album"] in ("quangcao", "flash"):
            why = "album quang cao / flash"
        if not why and it["kind"] in ("s60game", "s60app") and ONLINE_MOD.search(text):
            why = "online/mod/crack"
        if not why and it["kind"] in ("s60game", "s60app", "theme") and not it["title"]:
            why = "khong co ten"
        (drop if why else keep).append({**it, "why": why} if why else it)
    os.makedirs(os.path.join(a.data, "inventory"), exist_ok=True)
    with open(os.path.join(a.data, "inventory", "media.jsonl"), "w", encoding="utf-8") as f:
        for it in keep:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    with open(os.path.join(a.data, "inventory", "media-excluded.jsonl"), "w", encoding="utf-8") as f:
        for it in drop:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    from collections import Counter
    print("giu", len(keep), "loai", len(drop))
    print(sorted(Counter((x["src"], x["kind"]) for x in keep).items()))
    print("album:", len({(x["src"], x["album"]) for x in keep if x["kind"] in ("wallpaper", "ringtone")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
