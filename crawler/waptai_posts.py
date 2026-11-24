"""Sinh posts.json (dau vao cho tools/blogger-import.mjs cua monika-java) tu game waptai da lam sach + len Pixeldrain.
Chi lay game: qua bo loc (ok), co du moi JAR da len Pixeldrain, va co mo ta viet lai (--desc, file JSON do buoc viet lai sinh ra).
Moi bai co cac dong v1..vN: 'co|KB|JAR=http://api.justmonika.top/v1/p/<ID>/<ten>.jar' va bang link tai (the <table>, may cu van xem duoc)."""
import argparse, glob, html, json, os, sys
from datetime import datetime, timedelta, timezone
from . import waptai_images as images

API = "http://api.justmonika.top"
RES_PRIORITY = ["240x320", "320x240", "240x400", "176x220", "176x208", "128x160", "128x128", "360x640", "320x480", "480x800"]
CATS = {"Nhập vai", "Hành động", "Chiến thuật", "Phiêu lưu", "Giải đố", "Đua xe", "Thể thao", "Bắn súng", "Đối kháng",
        "Vui nhộn", "Sinh tồn", "Kiếm hiệp", "Thủ thành"}
APP_CATS = {"Mạng & trình duyệt", "Chat & mạng xã hội", "Đọc sách & truyện", "Trình phát nhạc & video", "Văn phòng & học tập",
            "Công cụ hệ thống", "Bản đồ & GPS", "Đời sống", "Tùy biến máy", "Ảnh & camera", "Giả lập & chạy game", "Khác"}


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


def img_url(u, idx):
    """Anh da chuyen ve kho Pixeldrain thi dung link Worker; chua thi tam hotlink nguon (ghi nhan de bao)."""
    e = idx.get(u)
    return images.url_of(e) if e and e.get("pixeldrain_id") else u


def load_posts(data, kind, only_ids=None):
    for p in sorted(glob.glob(os.path.join(data, "waptai", "posts", "*.json")), key=lambda p: int(os.path.basename(p)[:-5])):
        r = json.load(open(p, encoding="utf-8"))
        if r["kind"] == kind and r["filter"]["status"] == "ok" and (not only_ids or r["source_id"] in only_ids):
            yield r


def stamp(start, n):
    return (start - timedelta(minutes=n)).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_files(r, d, items, imgs_raw, idx, labels, extra_meta, cat, plat="j2me"):
    imgs = [img_url(u, idx) for u in imgs_raw]
    res = sorted({x["resolution"] for x, _ in items if x["resolution"]}, key=res_key)[:6]
    meta = {"type": extra_meta["type"], "size": str(min(kb_of(x) for _, x in items)), "cat": cat, "tags": extra_meta.get("tags", "goc"),
            "plat": plat, "res": ", ".join(res), "desc": d["desc"]}
    if imgs:
        meta["img"] = imgs[0]
    for i, (dl, x) in enumerate(items[:40], 1):
        meta[f"v{i}"] = f"{dl['resolution'] or 'Chung'}|{kb_of(x)}|JAR={link_of(x)}"
    body = "".join(f'<img src="{html.escape(u)}" alt="{html.escape(d["title"])}" />\n' for u in imgs)
    body += "".join(f"<p>{html.escape(par)}</p>\n" for par in d["body"].split("\n\n") if par.strip())
    body += f"<h3>Tải về theo độ phân giải</h3>\n<p>Chọn dòng đúng độ phân giải màn hình máy bạn.</p>\n{table_html(items)}\n"
    body += f'<p>Nguồn thông tin và ảnh chụp: <a href="{html.escape(r["page_url"])}">java.waptai.com</a></p>'
    return {"title": d["title"], "html": body, "labels": labels, "meta": meta, "description": d["desc"][:150]}


def build(data, desc, start, only_ids=None, idx=None, app_desc=None, truyen_desc=None, guide_desc=None):
    """Tra ve (posts, skipped). Thu tu: game, phan mem, truyen, thu thuat. Moi nhom chi gom bai du dieu kien."""
    idx = idx or {}
    posts, skipped = [], []
    for r in load_posts(data, "game", only_ids):
        d = desc.get(str(r["source_id"]))
        items = files_of(r)
        if not d:
            skipped.append((r["source_id"], "chua co mo ta viet lai"))
            continue
        if d.get("flag"):
            skipped.append((r["source_id"], "flag " + d["flag"]))
            continue
        if not items:
            skipped.append((r["source_id"], "chua du JAR tren Pixeldrain"))
            continue
        cat = d["cat"] if d["cat"] in CATS else "Hành động"
        labels = ["Game", cat] + (["VH"] if d["vh"] else []) + (["Gameloft"] if any("GameLoft" in c for c in r["categories"]) else [])
        posts.append(build_files(r, d, items, images.post_images(r), idx, labels,
                                 {"type": "game", "tags": "vh" if d["vh"] else "goc"}, cat))
    for r in load_posts(data, "phan_mem", only_ids):
        d = (app_desc or {}).get(str(r["source_id"]))
        items = files_of(r)
        if not d:
            skipped.append((r["source_id"], "app: chua co mo ta"))
            continue
        if not items:
            skipped.append((r["source_id"], "app: chua du JAR tren Pixeldrain"))
            continue
        cat = d["cat"] if d["cat"] in APP_CATS else "Khác"
        posts.append(build_files(r, d, items, images.post_images(r), idx, ["App", cat], {"type": "app"}, cat))
    for r in load_posts(data, "truyen", only_ids):
        d = (truyen_desc or {}).get(str(r["source_id"]))
        if not d or d.get("flag"):
            skipped.append((r["source_id"], "truyen: " + ("chua co mo ta" if not d else "flag " + d["flag"])))
            continue
        pages = [img_url(c["src"], idx) for c in r.get("comic_pages", [])]
        if not pages:
            skipped.append((r["source_id"], "truyen: khong co trang"))
            continue
        cat = "Truyện tranh & manga"
        body = f"<p>{html.escape(d['body'])}</p>\n" + "".join(
            f'<p><img src="{html.escape(u)}" alt="{html.escape(d["title"])} - trang {i}/{len(pages)}" /></p>\n' for i, u in enumerate(pages, 1))
        body += f'<p>Nguồn: <a href="{html.escape(r["page_url"])}">java.waptai.com</a></p>'
        posts.append({"title": d["title"], "html": body, "labels": ["Bài viết", cat],
                      "meta": {"type": "post", "cat": cat, "img": pages[0], "desc": d["desc"]}, "description": d["desc"][:150]})
    for r in list(load_posts(data, "meo", only_ids)) + list(load_posts(data, "tin", only_ids)):
        d = (guide_desc or {}).get(str(r["source_id"]))
        if not d or d.get("flag") or not (d.get("body_html") or "").strip():
            skipped.append((r["source_id"], "meo: chua co/bo"))
            continue
        cat = "Thủ thuật & mẹo"
        posts.append({"title": d["title"], "html": d["body_html"], "labels": ["Bài viết", cat],
                      "meta": {"type": "post", "cat": cat, "desc": d["desc"]}, "description": d["desc"][:150]})
    for n, p in enumerate(posts):
        p["published"] = stamp(start, n)
    return posts, skipped


def load_desc(files):
    out = {}
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        for x in (d.values() if isinstance(d, dict) else d):
            out[str(x["id"])] = x
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--desc", nargs="+", required=True, help="JSON mo ta game (mang hoac dict id->{title,cat,vh,desc,body})")
    ap.add_argument("--app-desc", nargs="*", default=[])
    ap.add_argument("--truyen-desc", nargs="*", default=[])
    ap.add_argument("--guide-desc", nargs="*", default=[])
    ap.add_argument("--out", required=True, help="file posts.json (mot file) hoac thu muc khi dung --per-file")
    ap.add_argument("--per-file", type=int, default=0, help="chia ra nhieu file posts-001.json ... moi file toi da n bai")
    ap.add_argument("--ids", default="")
    a = ap.parse_args(argv)
    only = {int(x) for x in a.ids.split(",") if x.strip()} or None
    idx = images.load(os.path.join(a.data, "waptai", "images.json"))
    posts, skipped = build(a.data, load_desc(a.desc), datetime.now(timezone.utc).replace(microsecond=0), only, idx,
                           load_desc(a.app_desc), load_desc(a.truyen_desc), load_desc(a.guide_desc))
    if a.per_file:
        os.makedirs(a.out, exist_ok=True)
        files = []
        for i in range(0, len(posts), a.per_file):
            f = os.path.join(a.out, f"posts-{i // a.per_file + 1:03d}.json")
            json.dump(posts[i:i + a.per_file], open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            files.append(f)
        print(f"{len(posts)} bai -> {len(files)} file trong {a.out}; bo qua {len(skipped)}")
    else:
        json.dump(posts, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"{len(posts)} bai -> {a.out}; bo qua {len(skipped)}")
    hot = sum(1 for p in posts if "java.waptai.com" in json.dumps(p["meta"]) or 'src="https://java.waptai.com' in p["html"])
    print(f"bai con hotlink anh waptai: {hot}")
    import collections
    for why, n in collections.Counter(w for _, w in skipped).most_common(8):
        print(f"  - {n}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
