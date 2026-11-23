"""Sinh posts.json (dau vao cho tools/blogger-import.mjs cua monika-java) tu du lieu game da loc.
Bai link-only: khong co meta.jar; bang link tai theo do phan giai nam trong than bai (tro ve trang nguon)."""
import argparse, glob, html, json, os
from datetime import datetime, timedelta, timezone

# Worker (parseRes) chi giu toi da 6 do phan giai dau tien trong meta.res: dua cac cau pho bien len truoc.
RES_PRIORITY = ["240x320", "320x240", "240x400", "176x220", "176x208", "128x160", "128x128", "360x640", "320x480", "480x800"]
PLAIN = {"jar": "JAR", "zip_hoac_khac": "Gói ZIP"}


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
        body = (f'<p>{html.escape(v["desc"])}</p>\n<p>{html.escape(v["body"])}</p>\n'
                f'<h3>Tải về theo độ phân giải</h3>\n<p>Chọn dòng đúng độ phân giải màn hình máy bạn. Tệp tải từ trang nguồn (HTTP), Monika không lưu bản sao.</p>\n'
                f'<table>\n<tr><th>Màn hình</th><th>Loại</th><th>Dung lượng</th><th>Máy mẫu</th><th>Tải</th></tr>\n{rows_html(g)}\n</table>\n'
                f'<p>Nguồn thông tin: <a href="{g["page_url"]}">dedomil.net</a>' + (f' · Hãng: {html.escape(g["vendor"])}' if g.get("vendor") else "") + "</p>")
        posts.append({
            "title": g["title"], "html": body, "labels": ["Game", v["cat"]],
            "meta": {"type": "game", "size": str(min(jars)) if jars else "", "cat": v["cat"], "tags": "goc", "plat": "j2me",
                     "res": ", ".join(res), "desc": v["desc"]},
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
