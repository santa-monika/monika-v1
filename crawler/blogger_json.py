"""Sinh posts.json (dau vao cho tools/blogger-import.mjs cua monika-java) tu du lieu game da loc.
Bai link-only: khong co meta.jar; bang link tai theo do phan giai nam trong than bai (tro ve trang nguon)."""
import argparse, glob, html, json, os, re
from .normalize import strip_accents
from datetime import datetime, timedelta, timezone

# Worker (parseRes) chi giu toi da 6 do phan giai dau tien trong meta.res: dua cac cau pho bien len truoc.
RES_PRIORITY = ["240x320", "320x240", "240x400", "176x220", "176x208", "128x160", "128x128", "360x640", "320x480", "480x800"]
PLAIN = {"jar": "JAR", "zip_hoac_khac": "Gói ZIP"}
API_PIC = "https://api.justmonika.top/v1/pic/"


def rows_html(g):
    rows = []
    by_res = {}
    for v in g["variants"]:
        by_res.setdefault((v["resolution"] or "?", v["kind"]), []).append(v)
    for (res, kind), vs in sorted(by_res.items()):
        v = vs[0]
        kb = [x["size_kb"] for x in vs if x["size_kb"]]
        size = f"{min(kb)}–{max(kb)} KB" if kb and min(kb) != max(kb) else (f"{kb[0]} KB" if kb else "")
        if kind == "jar":
            links = f'<a href="http://dedomil.net/games/{g["source_id"]}/download/{v["variant_id"]}">JAD</a> · <a href="http://dedomil.net/games/{g["source_id"]}/download-jar/{v["variant_id"]}">JAR</a>'
        else:
            links = f'<a href="http://dedomil.net/games/{g["source_id"]}/download/{v["variant_id"]}">Tải gói</a>'
        rows.append(f"<tr><td>{html.escape(res)}</td><td>{PLAIN.get(kind, kind)}</td><td>{size}</td><td>{html.escape(v['model'])}</td><td>{links}</td></tr>")
    return "\n".join(rows)


def v_lines(g):
    """Dong v1..vN cho Worker: 'co|KB|JAD=url|JAR=url' (jar) hoac 'co|KB|Goi ZIP=url' (zip/khac). Sap cau pho bien truoc."""
    by_res = {}
    for v in g["variants"]:
        if v["resolution"]:
            by_res.setdefault((v["resolution"], v["kind"]), []).append(v)
    def key(k):
        r = RES_PRIORITY.index(k[0]) if k[0] in RES_PRIORITY else 99
        return (r, k[0], 0 if k[1] == "jar" else 1)
    out = []
    for (res, kind) in sorted(by_res, key=key):
        vs = by_res[(res, kind)]
        v = vs[0]
        kb = min((x["size_kb"] for x in vs if x["size_kb"]), default=0)
        base = f"http://dedomil.net/games/{g['source_id']}"
        if kind == "jar":
            out.append(f"{res}|{kb}|JAD={base}/download/{v['variant_id']}|JAR={base}/download-jar/{v['variant_id']}")
        else:
            out.append(f"{res}|{kb}|Gói ZIP={base}/download/{v['variant_id']}")
    return out[:40]


def kb_range(g):
    jars = [x["size_kb"] for x in g["variants"] if x["kind"] == "jar" and x["size_kb"]]
    return (min(jars), max(jars)) if jars else (0, 0)


def entry(g, cat, desc, body_intro, res, n, start, pic):
    jars_min, _ = kb_range(g)
    img = f'<img src="{pic}" alt="{html.escape(g["title"])}" />\n' if pic else ""
    body = (img + f'<p>{html.escape(desc)}</p>\n<p>{html.escape(body_intro)}</p>\n'
            f'<h3>Tải về theo độ phân giải</h3>\n<p>Chọn dòng đúng độ phân giải màn hình máy bạn. Tệp tải từ trang nguồn (HTTP), Monika không lưu bản sao.</p>\n'
            f'<table>\n<tr><th>Màn hình</th><th>Loại</th><th>Dung lượng</th><th>Máy mẫu</th><th>Tải</th></tr>\n{rows_html(g)}\n</table>\n'
            f'<p>Nguồn thông tin: <a href="{g["page_url"]}">dedomil.net</a>' + (f' · Hãng: {html.escape(g["vendor"])}' if g.get("vendor") else "") + "</p>")
    meta = {"type": "game", "size": str(jars_min) if jars_min else "", "cat": cat, "tags": "goc", "plat": "j2me",
            "res": ", ".join(res), "desc": desc}
    if pic:
        meta["img"] = pic
    meta.update({f"v{i}": line for i, line in enumerate(v_lines(g), 1)})
    base = re.sub(r"[^a-z0-9]+", "-", strip_accents(g["title"]).lower()).strip("-")[:28].strip("-") or "game"
    return {"title": g["title"], "slug": f'{base}-{g["source_id"]}', "html": body, "labels": ["Game", cat], "meta": meta,
            "published": (start - timedelta(minutes=n)).strftime("%Y-%m-%dT%H:%M:%SZ"), "description": desc[:150]}


def build(data, start, skip_ids=()):
    """Bai cho moi game qua bo loc va co ban tai. Game co mo ta viet tay (vi/mo-ta-vi.json) dung ban viet tay,
    con lai sinh tu du lieu co cau truc. Sap theo luot tai giam dan; skip_ids = game da dang roi."""
    from .genre import guess_genre
    from .vi_desc import describe
    vi = json.load(open(os.path.join(data, "vi", "mo-ta-vi.json"), encoding="utf-8"))
    games = []
    for p in glob.glob(os.path.join(data, "dedomil", "games", "*.json")):
        g = json.load(open(p, encoding="utf-8"))
        if g["filter"]["status"] != "ok" or g["source_id"] in skip_ids or not v_lines(g):
            continue
        games.append(g)
    games.sort(key=lambda g: (-(g.get("downloads") or 0), g["source_id"]))
    posts = []
    for n, g in enumerate(games):
        allres = {x["resolution"] for x in g["variants"] if x["resolution"]}
        res = sorted(allres, key=lambda r: (RES_PRIORITY.index(r) if r in RES_PRIORITY else 99, r))
        th = g.get("thumbs") or []
        pic = f'{API_PIC}{g["source_id"]}_1.jpg' if th else ""
        v = vi.get(str(g["source_id"]))
        if v:
            cat, desc, intro = v["cat"], v["desc"], v["body"]
        else:
            cat = guess_genre(g["title"], g.get("description_en_private") or "")
            lo, hi = kb_range(g)
            desc, intro = describe(g, cat, res, lo, hi)
        posts.append(entry(g, cat, desc, intro, res[:6], n, start, pic))
    return posts


def split(posts, per_file):
    return [posts[i:i + per_file] for i in range(0, len(posts), per_file)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True, help="thu muc dau ra: posts-001.json, posts-002.json, ...")
    ap.add_argument("--per-file", type=int, default=300)
    ap.add_argument("--skip", default="", help="id game da dang, cach nhau dau phay")
    ap.add_argument("--skip-handwritten", action="store_true", help="bo qua game co mo ta viet tay (da dang o dot thi diem)")
    a = ap.parse_args()
    skip = {int(x) for x in a.skip.split(",") if x.strip()}
    if a.skip_handwritten:
        skip |= {int(k) for k in json.load(open(os.path.join(a.data, "vi", "mo-ta-vi.json"), encoding="utf-8"))}
    posts = build(a.data, datetime.now(timezone.utc).replace(microsecond=0), skip)
    os.makedirs(a.out, exist_ok=True)
    parts = split(posts, a.per_file)
    for i, part in enumerate(parts, 1):
        json.dump(part, open(os.path.join(a.out, f"posts-{i:03d}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(posts)} bai -> {len(parts)} file trong {a.out}")
