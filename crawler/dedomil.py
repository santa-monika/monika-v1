"""Crawler metadata dedomil.net (chi qua HTTP cong 80; HTTPS bi reset tu moi truong cloud).
Khong tai file JAR. Moi game -> 1 JSON. Chay lai duoc: bo qua game da co."""
import argparse, html, json, os, re, sys
from .common import Fetcher
from .filters import classify
from .normalize import norm_title, resolution

BASE = "http://dedomil.net"


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def parse_ids(page_html):
    """Lay danh sach id game tu trang liet ke (top/latest/category)."""
    seen, out = set(), []
    for m in re.finditer(r'href="/games/(\d+)/(?:screens|category/\d+)[^"]*"', page_html):
        gid = int(m.group(1))
        if gid not in seen:
            seen.add(gid)
            out.append(gid)
    return out


def parse_size(txt):
    m = re.search(r"([\d.]+)\s*(kB|KB|MB)", txt)
    if not m:
        return None
    v = float(m.group(1))
    return int(v * (1024 if m.group(2).lower() == "mb" else 1))  # kB


def parse_game(page_html, gid):
    g = {"source": "dedomil", "source_id": gid, "page_url": f"{BASE}/games/{gid}"}
    m = re.search(r'<div class="NHRY">(.*?)</div>', page_html, re.S)
    g["title"] = clean(m.group(1)) if m else None
    for key, field in (("Added", "added"), ("Downloads", "downloads"), ("Vendor", "vendor")):
        m = re.search(rf"<b>{key}</b>:\s*([^<]*)", page_html)
        g[field] = clean(m.group(1)) if m and clean(m.group(1)) else None
    if g["downloads"] and g["downloads"].isdigit():
        g["downloads"] = int(g["downloads"])
    m = re.search(r"<b>Description</b>:(.*?)(?:<br\s*/?>\s*<br\s*/?>\s*<b>The game's|</div>)", page_html, re.S)
    g["description_en_private"] = clean(m.group(1)) if m else None
    g["screenshots"] = [BASE + u if u.startswith("/") else u
                        for u in re.findall(r'(?:SPLASH|SECSCR)[^>]*>\s*<a href="([^"]+)"', page_html)]
    variants = []
    for mm in re.finditer(r'<div class="MODELS">(.*?)</div>\s*<div class="LOAD">(.*?)</div>', page_html, re.S):
        models, load = mm.group(1), mm.group(2)
        res = resolution(models)
        jad = re.search(r'/games/\d+/download/(\d+)"[^>]*>JAD', load)
        jar = re.search(r'/games/\d+/download-jar/(\d+)"', load)
        other = re.search(r'/games/\d+/download/(\d+)"[^>]*>download', load)
        kind = "jar" if jar else ("zip_hoac_khac" if other else None)
        if not kind:
            continue
        vid = int((jar or other).group(1))
        variants.append({"variant_id": vid, "model": clean(re.sub(r"\(<b>.*?</b>\)", "", models)),
                         "resolution": res, "kind": kind, "size_kb": parse_size(clean(load)),
                         "page_url": f"{BASE}/games/{gid}/download{'-jar' if jar else ''}/{vid}"})
    g["variants"] = variants
    # gom theo (do phan giai, loai): moi phan giai co the co nhieu build khac nhau theo dong may
    groups = {}
    for v in variants:
        groups.setdefault((v["resolution"], v["kind"]), []).append(v)
    g["by_resolution"] = [
        {"resolution": k[0], "kind": k[1], "builds": len(vs),
         "size_kb_min": min((x["size_kb"] or 0) for x in vs), "size_kb_max": max((x["size_kb"] or 0) for x in vs),
         "example_variant_id": vs[0]["variant_id"], "example_model": vs[0]["model"]}
        for k, vs in sorted(groups.items(), key=lambda kv: (kv[0][0] or "", kv[0][1]))]
    g["norm_title"] = norm_title(g["title"])
    status, why = classify(g["title"], g["description_en_private"], g["vendor"])
    g["filter"] = {"status": status, "reasons": why}
    return g


def crawl_games(ids, outdir, fetcher):
    os.makedirs(outdir, exist_ok=True)
    done = fail = skipped = 0
    for gid in ids:
        path = os.path.join(outdir, f"{gid}.json")
        if os.path.exists(path):
            skipped += 1
            continue
        try:
            g = parse_game(fetcher.get(f"{BASE}/games/{gid}"), gid)
        except Exception as e:
            fail += 1
            print(f"loi game {gid}: {type(e).__name__}", file=sys.stderr)
            continue
        with open(path, "w", encoding="utf-8") as f:
            json.dump(g, f, ensure_ascii=False, indent=1)
        done += 1
    return done, skipped, fail


def list_ids(fetcher, kind, pages):
    ids = []
    for p in pages:
        url = {"top": f"{BASE}/games/top/all/page/{p}", "latest": f"{BASE}/games/latest"}[kind]
        ids += parse_ids(fetcher.get(url))
        if kind == "latest":
            break
    return list(dict.fromkeys(ids))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="thu muc dau ra (repo du lieu rieng)")
    ap.add_argument("--ids", default="", help="danh sach id cach nhau dau phay")
    ap.add_argument("--top-pages", default="", help="vd 1-2: lay id tu bang xep hang top")
    ap.add_argument("--delay", type=float, default=2.0)
    a = ap.parse_args(argv)
    f = Fetcher(delay=a.delay)
    ids = [int(x) for x in a.ids.split(",") if x.strip()]
    if a.top_pages:
        lo, _, hi = a.top_pages.partition("-")
        ids += list_ids(f, "top", range(int(lo), int(hi or lo) + 1))
    ids = list(dict.fromkeys(ids))
    done, skipped, fail = crawl_games(ids, os.path.join(a.out, "dedomil", "games"), f)
    print(f"xong: {done} moi, {skipped} da co, {fail} loi, {f.requests} yeu cau")
    return 1 if fail and not done else 0


if __name__ == "__main__":
    sys.exit(main())
