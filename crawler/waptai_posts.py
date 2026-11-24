"""Sinh posts.json (dau vao cho tools/blogger-import.mjs cua monika-java) tu game waptai da lam sach + len Pixeldrain.
Chi lay game: qua bo loc (ok), co du moi JAR da len Pixeldrain, va co mo ta viet lai (--desc, file JSON do buoc viet lai sinh ra).
Moi bai co cac dong v1..vN: 'co|KB|JAR=http://api.justmonika.top/v1/p/<ID>/<ten>.jar' va bang link tai (the <table>, may cu van xem duoc)."""
import argparse, glob, html, json, os, sys
from datetime import datetime, timedelta, timezone

API = "http://api.justmonika.top"
RES_PRIORITY = ["240x320", "320x240", "240x400", "176x220", "176x208", "128x160", "128x128", "360x640", "320x480", "480x800"]
CATS = {"Nhập vai", "Hành động", "Chiến thuật", "Phiêu lưu", "Giải đố", "Đua xe", "Thể thao", "Bắn súng", "Đối kháng",
        "Vui nhộn", "Sinh tồn", "Kiếm hiệp", "Thủ thành"}


def res_key(r):
    return (RES_PRIORITY.index(r) if r in RES_PRIORITY else 99, r or "~")


def files_of(r):
    """[(download, local_file)] chi cac JAR da len Pixeldrain, sap theo do phan giai."""
    by_url = {x["url"]: x for x in r.get("local", {}).get("files", [])}
    out = []
    for d in r["downloads"]:
        if d["own_host"] and d["ext"] == "jar":
            x = by_url.get(d["url"])
            if not x or not x.get("pixeldrain_id"):
                return None  # thieu file: chua du bo, chua dang
            out.append((d, x))
    return sorted(out, key=lambda t: (res_key(t[0]["resolution"]), t[1]["file"])) or None


def link_of(x):
    return f"{API}/v1/p/{x['pixeldrain_id']}/{os.path.basename(x['file'])}"


def kb_of(x):
    return max(1, round(x["bytes_clean"] / 1024))


def table_html(items):
    rows = []
    for d, x in items:
        models = ", ".join(m.strip() for m in (d.get("models") or "").replace("…", "").split(",")[:3] if m.strip())
        rows.append(f"<tr><td>{html.escape(d['resolution'] or 'Chung')}</td><td>{kb_of(x)} KB</td><td>{html.escape(models)}</td>"
                    f'<td><a href="{link_of(x)}">Tải JAR</a></td></tr>')
    return ('<table border="1" cellpadding="4" cellspacing="0" width="100%">\n<tr><th>Màn hình</th><th>Dung lượng</th><th>Máy mẫu</th><th>Tải</th></tr>\n'
            + "\n".join(rows) + "\n</table>")


def build(data, desc, start, only_ids=None):
    posts, skipped = [], []
    n = 0
    for p in sorted(glob.glob(os.path.join(data, "waptai", "posts", "*.json")), key=lambda p: int(os.path.basename(p)[:-5])):
        r = json.load(open(p, encoding="utf-8"))
        if r["kind"] != "game" or r["filter"]["status"] != "ok":
            continue
        if only_ids and r["source_id"] not in only_ids:
            continue
        d = desc.get(str(r["source_id"]))
        items = files_of(r)
        if not d:
            skipped.append((r["source_id"], "chua co mo ta viet lai"))
            continue
        if not items:
            skipped.append((r["source_id"], "chua du JAR tren Pixeldrain"))
            continue
        cat = d["cat"] if d["cat"] in CATS else "Hành động"
        imgs = [i["src"] for i in r["images"] if (i["w"] or 999) >= 100 and ("/wp-content/uploads/" in i["src"] or "/picture/" in i["src"])][:3]
        res = sorted({x["resolution"] for x, _ in items if x["resolution"]}, key=res_key)[:6]
        v = []
        for dl, x in items:
            v.append(f"{dl['resolution'] or 'Chung'}|{kb_of(x)}|JAR={link_of(x)}")
        meta = {"type": "game", "size": str(min(kb_of(x) for _, x in items)), "cat": cat, "tags": "vh" if d["vh"] else "goc",
                "plat": "j2me", "res": ", ".join(res), "desc": d["desc"]}
        if imgs:
            meta["img"] = imgs[0]
        meta.update({f"v{i}": line for i, line in enumerate(v[:40], 1)})
        labels = ["Game", cat] + (["VH"] if d["vh"] else []) + (["Gameloft"] if any("GameLoft" in c for c in r["categories"]) else [])
        body = "".join(f'<img src="{html.escape(u)}" alt="{html.escape(d["title"])}" />\n' for u in imgs)
        body += "".join(f"<p>{html.escape(par)}</p>\n" for par in d["body"].split("\n\n") if par.strip())
        body += f"<h3>Tải về theo độ phân giải</h3>\n<p>Chọn dòng đúng độ phân giải màn hình máy bạn.</p>\n{table_html(items)}\n"
        body += f'<p>Nguồn thông tin và ảnh chụp: <a href="{html.escape(r["page_url"])}">java.waptai.com</a></p>'
        posts.append({"title": d["title"], "html": body, "labels": labels, "meta": meta,
                      "published": (start - timedelta(minutes=n)).strftime("%Y-%m-%dT%H:%M:%SZ"), "description": d["desc"][:150]})
        n += 1
    return posts, skipped


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--desc", nargs="+", required=True, help="cac file JSON mo ta viet lai (mang {id,title,cat,vh,desc,body})")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ids", default="")
    a = ap.parse_args(argv)
    desc = {}
    for f in a.desc:
        for d in json.load(open(f, encoding="utf-8")):
            desc[str(d["id"])] = d
    only = {int(x) for x in a.ids.split(",") if x.strip()} or None
    posts, skipped = build(a.data, desc, datetime.now(timezone.utc).replace(microsecond=0), only)
    json.dump(posts, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(posts)} bai -> {a.out}; bo qua {len(skipped)}")
    for i, why in skipped[:10]:
        print("  -", i, why)
    return 0


if __name__ == "__main__":
    sys.exit(main())
