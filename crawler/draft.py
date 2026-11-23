"""Sinh nhap bai Blogspot (HTML) tu du lieu game + mo ta tieng Viet tu viet. Chua dang len dau ca."""
import argparse, glob, html, json, os


def make(g, vi, thumbs_dir_note="img/"):
    jars = [v for v in g["variants"] if v["kind"] == "jar" and v["size_kb"]]
    size = min((v["size_kb"] for v in jars), default=0)
    lines = ["type: game", f"size: {size}" if size else "size:", f"cat: {vi['cat']}",
             f"src: dedomil:{g['source_id']}", f"desc: {vi['desc']}"]
    for r in g["by_resolution"]:
        if not r["resolution"]:
            continue
        ex = next(v for v in g["variants"] if v["variant_id"] == r["example_variant_id"])
        lines.append(f"v: goc|{r['resolution']}|{ex['page_url']}|{r['size_kb_min']}|{r['kind']}|{r['builds']}")
    meta = "\n".join(lines)
    imgs = "\n".join(f'<img src="{html.escape(t["file"])}" alt="{html.escape(g["title"])}" />' for t in g.get("thumbs", [])[:1])
    credit = f'Nguồn thông tin: <a href="{g["page_url"]}">dedomil.net</a>' + (f' · Hãng: {html.escape(g["vendor"])}' if g.get("vendor") else "")
    return (f'<pre class="mk-meta">\n{html.escape(meta, quote=False)}\n</pre>\n{imgs}\n'
            f'<p>{html.escape(vi["desc"])}</p>\n<p>{html.escape(vi["body"])}</p>\n'
            f'<p>Chọn bản đúng độ phân giải màn hình máy bạn. Tệp được tải từ trang nguồn, Monika không lưu bản sao.</p>\n<p>{credit}</p>\n')


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    a = ap.parse_args()
    vi = json.load(open(os.path.join(a.data, "vi", "mo-ta-vi.json"), encoding="utf-8"))
    os.makedirs(os.path.join(a.data, "drafts"), exist_ok=True)
    rows = []
    for p in sorted(glob.glob(os.path.join(a.data, "dedomil", "games", "*.json")), key=lambda x: int(os.path.basename(x)[:-5])):
        g = json.load(open(p, encoding="utf-8"))
        if g["filter"]["status"] != "ok" or str(g["source_id"]) not in vi:
            continue
        open(os.path.join(a.data, "drafts", f"dedomil-{g['source_id']}.html"), "w", encoding="utf-8").write(make(g, vi[str(g["source_id"])]))
        rows.append(g["source_id"])
    print(f"nhap: {len(rows)} bai")
