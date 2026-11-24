"""Lap danh muc ung vien (inventory.jsonl) cho cac nguon nhieu JAR: quangninhwap (trang da crawl), giaitri321 va wapvip (CDX archive.org).
Moi dong: src, url, ts (archive), via (direct|xtgem|archive), file, title, group (khoa gop cac ban cung game), res, plat, kind (game|app), vh, section.
Loai: game online, mod/hack, crack, 18+/co bac (bo loc o filters.classify + mau online/mod rieng cho 3 nguon nay). Ghi them excluded.jsonl de sep xem ly do."""
import argparse, glob, gzip, json, os, re, sys, urllib.parse
from .filters import classify
from .normalize import strip_accents

ONLINE_MOD = re.compile(
    r"(\bmod\b|hack|auto[\s_-]*click|\bgdl\b|\bxld\b|army|avatar|ngoc[\s_-]*rong|\bnro\b|ninja[\s_-]*school|gopet|kpah|hiep[\s_-]*si|online|fixlag|"
    r"key\d|crack|\btool\b|gunny|bomb[\s_-]*online|tuy[\s_-]*giang|phong[\s_-]*van|vuon[\s_-]*thuy|bigkool|teamobi|\bvang\b|cheat|"
    r"resize|safemgr|activ|unlock|keygen|patch)", re.I)
PLAT_TOK = re.compile(r"^(s40|s60|s60v\d|s40v\d+|e\d\d|n\d\d|v\d+(\.\d+)*|wapvip|wapm4u|free|full|vi|jar|java|gdl|xld|nokia|samsung|lg|motorola|"
                      r"sonyericsson|se|midp\d?|cldc\d?|ver\d*|new|crack|final)$", re.I)
RES = re.compile(r"(?<!\d)(\d{2,3})\s*[xX_]\s*(\d{2,3})(?!\d)")
VH = re.compile(r"(viet\s*hoa|viethoa|\bvh\b|tieng\s*viet|vietsub|\bvie\b)", re.I)
SKIP_SECTION_GT321 = ("online/", "android/", "files/", "media/", "truyen/", "tienich/", "game-offline/gameteamobi")
APP_HINT = ("ung-dung", "ungdung", "phan-mem", "soft/")


def clean_title(raw):
    base = urllib.parse.unquote(raw)
    base = re.sub(r"\.(jar|jad|sisx?|zip)$", "", base, flags=re.I)
    res = None
    m = RES.search(base)
    if m:
        res = f"{m.group(1)}x{m.group(2)}"
    t = RES.sub(" ", base)
    t = re.sub(r"[_\-+.]+", " ", t)
    t = " ".join(w for w in t.split() if not PLAT_TOK.match(w)).strip()
    t = re.sub(r"\s+", " ", t)
    if t and t == t.lower():
        t = t.title()
    return t, res


def group_key(title):
    return re.sub(r"[^a-z0-9]+", "", strip_accents(title).lower())


def plat_of(name):
    n = name.lower()
    if re.search(r"s60|e\d\d|n\d\d|\.sisx?$", n):
        return "s60"
    if re.search(r"s40", n):
        return "s40"
    return "j2me"


def make(src, url, file, via, ts=None, slug=None, section="", kind="game", label=""):
    title, res = clean_title(slug.replace("-", " ") if slug else file)
    _, fres = clean_title(file)
    res = fres or res or None
    if not res and label:
        m = RES.search(label)
        res = f"{m.group(1)}x{m.group(2)}" if m else None
    if not res:
        m = re.search(r"files(\d{2,3})x(\d{2,3})", section)
        res = f"{m.group(1)}x{m.group(2)}" if m else None
    return {"src": src, "url": url, "ts": ts, "via": via, "file": urllib.parse.unquote(file), "title": title, "group": group_key(title),
            "res": res, "plat": plat_of(file), "kind": kind, "vh": bool(VH.search(f"{title} {file}")), "section": section}


def qnw(data):
    out = []
    for p in sorted(glob.glob(os.path.join(data, "quangninhwap", "pages", "*.json"))):
        r = json.load(open(p, encoding="utf-8"))
        sect = os.path.basename(p)[:-5]
        kind = "app" if sect.startswith(("tai-ung-dung", "ban-do", "Ung20", "tai-opera", "thu-thuat")) else "game"
        for f in r["files"]:
            if f["ext"] != "jar":
                continue
            u = f["url"].replace("http://www.", "http://")
            file = u.rsplit("/", 1)[-1]
            out.append(make("qnw", u, file, "xtgem", section=sect, kind=kind, label=f["label"]))
    return out


def cdx_rows(data, site):
    for l in gzip.open(os.path.join(data, "archive", site, "cdx.jsonl.gz"), "rt", encoding="utf-8"):
        yield json.loads(l)


def gt321(data):
    out, seen = [], set()
    for r in cdx_rows(data, "giaitri321.pro"):
        p = urllib.parse.urlsplit(r["u"])
        path = p.path.lstrip("/")
        if not path.lower().endswith(".jar") or r["m"] == "text/html" or any(path.startswith(s) for s in SKIP_SECTION_GT321):
            continue
        key = path.lower()
        if key in seen:
            continue
        seen.add(key)
        parts = path.split("/")
        slug = parts[-2] if len(parts) >= 3 and not re.fullmatch(r"\d+", parts[-2]) else None
        kind = "app" if path.startswith("soft/") else "game"
        out.append(make("gt321", f"http://giaitri321.pro/{path}", parts[-1], "archive", ts=r["t"], slug=slug,
                        section="/".join(parts[:2]), kind=kind))
    return out


def wvip(data):
    out, seen = [], set()
    for r in cdx_rows(data, "wapvip.pro"):
        p = urllib.parse.urlsplit(r["u"])
        path = p.path.lstrip("/")
        if not path.lower().endswith(".jar") or r["m"] == "text/html":
            continue
        if not path.startswith("chuyen-muc/"):
            continue  # files/luutru, files/tap-tin: ban dung san cho game online/mod, de sau
        key = path.lower()
        if key in seen:
            continue
        seen.add(key)
        parts = path.split("/")
        kind = "app" if "ungdung" in parts[1] else "game"
        out.append(make("wvip", f"http://wapvip.pro/{path}", parts[-1], "archive", ts=r["t"], section="/".join(parts[:3]), kind=kind))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--srcs", default="qnw,gt321,wvip")
    a = ap.parse_args(argv)
    os.makedirs(os.path.join(a.data, "inventory"), exist_ok=True)
    fn = {"qnw": qnw, "gt321": gt321, "wvip": wvip}
    for s in a.srcs.split(","):
        items = fn[s](a.data)
        keep, drop = [], []
        for it in items:
            text = f"{it['title']} {it['file']} {it['section']}"
            st, why = classify(it["title"], it["file"])
            if ONLINE_MOD.search(strip_accents(text)) or not it["title"]:
                drop.append({**it, "why": "online/mod/crack"})
            elif st == "loai":
                drop.append({**it, "why": f"18+/co bac {why[:2]}"})
            else:
                keep.append({**it, "review": st == "duyet"})
        groups = {x["group"] for x in keep}
        with open(os.path.join(a.data, "inventory", f"{s}.jsonl"), "w", encoding="utf-8") as f:
            for it in keep:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        with open(os.path.join(a.data, "inventory", f"{s}-excluded.jsonl"), "w", encoding="utf-8") as f:
            for it in drop:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        print(f"{s}: {len(items)} JAR ung vien -> giu {len(keep)} ({len(groups)} game/ung dung khac nhau), loai {len(drop)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
