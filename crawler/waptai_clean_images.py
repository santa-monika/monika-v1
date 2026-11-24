"""Xoa chu 'WapTai.COM' in san tren anh chup game (cap nhat images.json: them truong 'clean' cho anh nhan dien chac).
Cach lam: mat na mau vang cua chu (crawler/assets/wm_template.png) khop voi mat na vang cua anh o ti le 1:1 (anh rong 176px),
chi xu ly khi do khop >= nguong; vung chu duoc to lai (inpaint) roi up ban sach len Pixeldrain. Anh goc van giu, url_of() chon ban sach.
Can opencv-python-headless va numpy. Anh khong nhan dien chac thi giu nguyen."""
import argparse, hashlib, json, os, sys
from concurrent.futures import ThreadPoolExecutor
from . import pd_upload, waptai_images as wi

ASSET = os.path.join(os.path.dirname(__file__), "assets", "wm_template.png")
THRESH = 0.75


def _cv():
    import cv2, numpy as np
    return cv2, np


def gold(im):
    cv2, np = _cv()
    h = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    H, S, V = h[..., 0], h[..., 1], h[..., 2]
    return ((H >= 12) & (H <= 38) & (S > 120) & (V > 150)).astype(np.uint8)


def template():
    cv2, np = _cv()
    return (cv2.imread(ASSET, cv2.IMREAD_GRAYSCALE) > 0).astype(np.uint8)


def find(im, T=None):
    """(do khop, (x, y)) hoac None neu anh qua nho."""
    cv2, np = _cv()
    T = template() if T is None else T
    if im.shape[1] != 176 or im.shape[0] < T.shape[0] or im.shape[1] < T.shape[1]:
        return None
    m = gold(im).astype(np.float32)
    cov = cv2.matchTemplate(m, T.astype(np.float32), cv2.TM_CCORR) / T.sum()
    _, mx, _, loc = cv2.minMaxLoc(cov)
    return mx, loc


def clean(im, loc, T=None):
    cv2, np = _cv()
    T = template() if T is None else T
    x, y = loc
    h, w = T.shape
    mask = np.zeros(im.shape[:2], np.uint8)
    mask[y:y + h, x:x + w] = T
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8))
    return cv2.inpaint(im, mask, 3, cv2.INPAINT_TELEA)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--src", required=True, help="thu muc anh goc da tai (waptai_images --out)")
    ap.add_argument("--out", required=True, help="thu muc luu anh da xoa chu")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-upload", action="store_true")
    a = ap.parse_args(argv)
    cv2, np = _cv()
    T = template()
    idx_path = os.path.join(a.data, "waptai", "images.json")
    idx = wi.load(idx_path)
    os.makedirs(a.out, exist_ok=True)
    todo, seen = [], 0
    for u, e in idx.items():
        if e.get("clean") or "truyen_" in u:
            continue
        im = cv2.imread(os.path.join(a.src, e["name"]))
        if im is None:
            continue
        r = find(im, T)
        if not r or r[0] < THRESH:
            continue
        cl = clean(im, r[1], T)
        ok, buf = cv2.imencode("." + ("png" if e["ext"] == "png" else "jpg"), cl,
                               [cv2.IMWRITE_JPEG_QUALITY, 92] if e["ext"] != "png" else [])
        raw = buf.tobytes()
        sha = hashlib.sha256(raw).hexdigest()
        name = f"waptai-img-{sha[:12]}.{e['ext'] if e['ext'] == 'png' else 'jpg'}"
        open(os.path.join(a.out, name), "wb").write(raw)
        todo.append((u, {"sha256": sha, "bytes": len(raw), "ext": name.rsplit('.', 1)[1], "name": name, "score": round(float(r[0]), 3)}))
        if a.limit and len(todo) >= a.limit:
            break
    print(f"{len(todo)} anh can xoa chu")
    if a.no_upload:
        return 0
    known = {}

    def push(item):
        u, c = item
        if c["sha256"] in known:
            return u, c, known[c["sha256"]]
        return u, c, pd_upload.upload_one(os.path.join(a.out, c["name"]), c["name"])

    done = bad = 0
    with ThreadPoolExecutor(a.workers) as ex:
        for fu in [ex.submit(push, t) for t in todo]:
            try:
                u, c, pid = fu.result()
                c["pixeldrain_id"] = pid
                known[c["sha256"]] = pid
                idx[u]["clean"] = c
                done += 1
            except Exception as e:
                bad += 1
                print(f"loi up: {e}", file=sys.stderr)
            if done and done % 100 == 0:
                wi.save(idx_path, idx)
                print(f"da up {done}", flush=True)
    wi.save(idx_path, idx)
    print(f"xong: {done} anh sach, {bad} loi")
    return 1 if bad and not done else 0


if __name__ == "__main__":
    sys.exit(main())
