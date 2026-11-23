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


def run(data_dir, fetcher, max_per_game=2):
    gdir = os.path.join(data_dir, "dedomil", "games")
    idir = os.path.join(data_dir, "dedomil", "img")
    os.makedirs(idir, exist_ok=True)
    n = bad = 0
    for path in sorted(glob.glob(os.path.join(gdir, "*.json"))):
        g = json.load(open(path, encoding="utf-8"))
        if g["filter"]["status"] != "ok" or g.get("thumbs") is not None:
            continue
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
    a = ap.parse_args()
    n, bad = run(a.out, Fetcher(delay=a.delay))
    print(f"anh: {n} moi, {bad} loi")
