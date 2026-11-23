"""Sinh posts.json (dau vao cho tools/blogger-import.mjs cua monika-java) tu du lieu game da loc.
Bai link-only: khong co meta.jar; bang link tai theo do phan giai nam trong than bai (tro ve trang nguon)."""
import argparse, glob, html, json, os
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


def build(data, start):
    vi = json.load(open(os.path.join(data, "vi", "mo-ta-vi.json"), encoding="utf-8"))
    posts = []
    paths = sorted(glob.glob(os.path.join(data, "dedomil", "games", "*.json")), key=lambda p: int(os.path.basename(p)[:-5]))
    n = 0
    for p in paths:
        g = json.load(open(p, encoding="utf-8"))
        v = vi.get(str(g["source_id"]))
        if g["filter"]["status"] != "ok" or not v:
            continue
        jars = [x["size_kb"] for x in g["variants"] if x["kind"] == "jar" and x["size_kb"]]
        allres = {x["resolution"] for x in g["variants"] if x["resolution"]}
        res = sorted(allres, key=lambda r: (RES_PRIORITY.index(r) if r in RES_PRIORITY else 99, r))[:6]
        pic = f'{API_PIC}{g["source_id"]}_1.jpg'
        body = (f'<img src="{pic}" alt="{html.escape(g["title"])}" />\n<p>{html.escape(v["desc"])}</p>\n<p>{html.escape(v["body"])}</p>\n'
                f'<h3>Tải về theo độ phân giải</h3>\n<p>Chọn dòng đúng độ phân giải màn hình máy bạn. Tệp tải từ trang nguồn (HTTP), Monika không lưu bản sao.</p>\n'
                f'<table>\n<tr><th>Màn hình</th><th>Loại</th><th>Dung lượng</th><th>Máy mẫu</th><th>Tải</th></tr>\n{rows_html(g)}\n</table>\n'
                f'<p>Nguồn thông tin: <a href="{g["page_url"]}">dedomil.net</a>' + (f' · Hãng: {html.escape(g["vendor"])}' if g.get("vendor") else "") + "</p>")
        posts.append({
            "title": g["title"], "html": body, "labels": ["Game", v["cat"]],
            "meta": {"type": "game", "size": str(min(jars)) if jars else "", "cat": v["cat"], "tags": "goc", "plat": "j2me",
                     "res": ", ".join(res), "img": pic, "desc": v["desc"],
                     **{f"v{i}": line for i, line in enumerate(v_lines(g), 1)}},
            "published": (start - timedelta(minutes=n)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "description": v["desc"][:150],
        })
        n += 1
    return posts


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    posts = build(a.data, datetime.now(timezone.utc).replace(microsecond=0))
    json.dump(posts, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(posts)} bai -> {a.out}")
