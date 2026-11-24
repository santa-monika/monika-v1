"""Chuyen anh minh hoa/trang truyen cua waptai ve kho cua sep (Pixeldrain) de bai khong con hotlink java.waptai.com.
Moi anh duoc tai 1 lan (cham, delay), dedupe theo sha256, dat ten waptai-img-<sha12>.<ext>, len Pixeldrain, ghi vao data/waptai/images.json
({url_goc: {sha256, bytes, ext, pixeldrain_id, name}}). Chay lai duoc: url da co pixeldrain_id thi bo qua.
Worker phat lai qua /v1/pi/<ID>/<ten> (https://api.justmonika.top, http cho may cu)."""
import argparse, glob, hashlib, json, os, sys
from .common import Fetcher, RateLimited
from . import pd_upload

API = "http://api.justmonika.top"
EXT_MAGIC = [(b"\xff\xd8\xff", "jpg"), (b"\x89PNG", "png"), (b"GIF8", "gif"), (b"RIFF", "webp")]


def post_images(r):
    """Cac anh se dung trong bai (cung quy tac voi waptai_posts)."""
    k = r["kind"]
    if k == "truyen":
        return [c["src"] for c in r.get("comic_pages", [])]
    if k in ("game", "phan_mem"):
        return [i["src"] for i in r["images"]
                if (i["w"] or 999) >= 100 and ("/wp-content/uploads/" in i["src"] or "/picture/" in i["src"])][:3]
    return []


def ext_of(raw):
    for m, e in EXT_MAGIC:
        if raw.startswith(m):
            return e
    return None


def url_of(entry):
    return f"{API}/v1/pi/{entry['pixeldrain_id']}/{entry['name']}"


def load(path):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}


def save(path, idx):
    json.dump(idx, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True, help="thu muc luu tam anh tai ve")
    ap.add_argument("--delay", type=float, default=0.6)
    ap.add_argument("--kinds", default="game,truyen,phan_mem")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)
    kinds = set(a.kinds.split(","))
    idx_path = os.path.join(a.data, "waptai", "images.json")
    idx = load(idx_path)
    urls = []
    for p in sorted(glob.glob(os.path.join(a.data, "waptai", "posts", "*.json")), key=lambda p: int(os.path.basename(p)[:-5])):
        r = json.load(open(p, encoding="utf-8"))
        if r["kind"] in kinds and r["filter"]["status"] == "ok":
            urls += [u for u in post_images(r) if u not in urls]
    todo = [u for u in dict.fromkeys(urls) if not idx.get(u, {}).get("pixeldrain_id")]
    print(f"{len(urls)} anh, can xu ly {len(todo)}")
    os.makedirs(a.out, exist_ok=True)
    f = Fetcher(delay=a.delay, timeout=60)
    by_sha = {v["sha256"]: v for v in idx.values() if v.get("pixeldrain_id")}
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading
    lock = threading.Lock()
    done = bad = 0
    pend = {}  # sha -> id dang up (tranh up trung)

    def push(u, ent):
        with lock:
            if ent["sha256"] in by_sha:
                return u, ent, by_sha[ent["sha256"]]["pixeldrain_id"]
        pid = pd_upload.upload_one(os.path.join(a.out, ent["name"]), ent["name"])
        return u, ent, pid

    ex = ThreadPoolExecutor(max_workers=a.workers)
    futs = []
    try:
        for n, u in enumerate(todo, 1):
            ent = idx.get(u)
            if not ent or not ent.get("sha256"):
                try:
                    raw = f.get(u, binary=True)
                except RateLimited as e:
                    print(f"DUNG do 429 (thu lai sau {e.retry_after}s)", file=sys.stderr)
                    break
                except Exception as e:
                    bad += 1
                    print(f"loi {u}: {e}", file=sys.stderr)
                    continue
                ext = ext_of(raw)
                if not ext:
                    bad += 1
                    print(f"loi {u}: khong phai anh", file=sys.stderr)
                    continue
                sha = hashlib.sha256(raw).hexdigest()
                ent = {"sha256": sha, "bytes": len(raw), "ext": ext, "name": f"waptai-img-{sha[:12]}.{ext}"}
                open(os.path.join(a.out, ent["name"]), "wb").write(raw)
            with lock:
                dup = pend.get(ent["sha256"])
                if dup is None:
                    pend[ent["sha256"]] = ent
            if dup is not None:  # cung noi dung da dang up: doi roi gan id sau
                futs.append(("later", u, ent))
                continue
            futs.append(ex.submit(push, u, ent))
            if a.limit and len(futs) >= a.limit:
                break
        for fu in futs:
            if isinstance(fu, tuple):
                continue
            try:
                u, ent, pid = fu.result()
                ent["pixeldrain_id"] = pid
                idx[u] = ent
                by_sha[ent["sha256"]] = ent
                done += 1
            except Exception as e:
                bad += 1
                print(f"loi up: {e}", file=sys.stderr)
            if done % 100 == 0:
                save(idx_path, idx)
                print(f"da up {done}", flush=True)
        for fu in futs:
            if isinstance(fu, tuple):
                _, u, ent = fu
                if ent["sha256"] in by_sha:
                    idx[u] = {**ent, "pixeldrain_id": by_sha[ent["sha256"]]["pixeldrain_id"]}
                    done += 1
    finally:
        ex.shutdown(wait=True)
    save(idx_path, idx)
    print(f"xong: {done} anh, {bad} loi")
    return 1 if bad and not done else 0


if __name__ == "__main__":
    sys.exit(main())
