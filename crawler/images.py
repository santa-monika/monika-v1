"""Tai anh chup man hinh cua game da qua bo loc va thu nho (khung 240x320 hoac 320x240, JPEG)."""
import argparse, glob, io, json, os, sys
from PIL import Image
from .common import Fetcher


def thumb(raw):
    im = Image.open(io.BytesIO(raw))
    im = im.convert("RGB")
    box = (320, 240) if im.width >= im.height else (240, 320)
    im.thumbnail(box)
    out = io.BytesIO()
    im.save(out, "JPEG", quality=72, optimize=True)
    return out.getvalue(), im.size


def run(data_dir, fetcher, max_per_game=1, id_from=0, id_to=0):
    gdir = os.path.join(data_dir, "dedomil", "games")
    idir = os.path.join(data_dir, "dedomil", "img")
    os.makedirs(idir, exist_ok=True)
    n = bad = 0
    for path in sorted(glob.glob(os.path.join(gdir, "*.json"))):
        g = json.load(open(path, encoding="utf-8"))
        if g["filter"]["status"] != "ok" or g.get("thumbs") is not None:
            continue
        if (id_from and g["source_id"] < id_from) or (id_to and g["source_id"] > id_to):
            continue
        if not any(v.get("resolution") for v in g["variants"]):
            continue  # khong co ban tai: khong dang bai nen khong can anh
        thumbs = []
        for i, url in enumerate(g["screenshots"][:max_per_game], 1):
            try:
                data, size = thumb(fetcher.get(url, binary=True))
            except Exception as e:
                bad += 1
                print(f"loi anh {g['source_id']}#{i}: {type(e).__name__}", file=sys.stderr)
                continue
            name = f"{g['source_id']}_{i}.jpg"
            open(os.path.join(idir, name), "wb").write(data)
            thumbs.append({"file": f"img/{name}", "w": size[0], "h": size[1], "bytes": len(data), "source_url": url})
            n += 1
        g["thumbs"] = thumbs
        json.dump(g, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return n, bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--max-per-game", type=int, default=1)
    ap.add_argument("--id-from", type=int, default=0)
    ap.add_argument("--id-to", type=int, default=0)
    a = ap.parse_args()
    n, bad = run(a.out, Fetcher(delay=a.delay), a.max_per_game, a.id_from, a.id_to)
    print(f"anh: {n} moi, {bad} loi")
