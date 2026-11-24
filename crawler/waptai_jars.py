"""Tai JAR cua waptai (host up.waptai.com), go muc nhung (crawler.jarclean), luu ban sach + ghi ket qua vao JSON bai.
Chi lay bai qua bo loc (status ok). Chay lai duoc: file da co (dung sha256 ban sach) thi bo qua.
Khong dang len dau ca; dau ra la thu muc JAR sach de sep duyet truoc khi dua len kho."""
import argparse, hashlib, json, os, re, sys
from .common import Fetcher, RateLimited
from . import jarclean


def safe_name(url):
    n = url.rsplit("/", 1)[-1]
    return re.sub(r"[^A-Za-z0-9._-]", "_", n)


def process_post(r, jar_out, fetcher, only_res=None, max_files=None):
    """-> (so file moi, so loi). Sua r['local'] tai cho."""
    outdir = os.path.join(jar_out, str(r["source_id"]))
    os.makedirs(outdir, exist_ok=True)
    local = {d["url"]: d for d in r.get("local", {}).get("files", [])}
    new = bad = 0
    n = 0
    for d in r["downloads"]:
        if not (d["own_host"] and d["ext"] == "jar"):
            continue
        if only_res and d["resolution"] not in only_res:
            continue
        if max_files and n >= max_files:
            break
        n += 1
        path = os.path.join(outdir, safe_name(d["url"]))
        if d["url"] in local and os.path.exists(path):
            continue
        try:
            raw = fetcher.get(d["url"], binary=True)
            clean, log, warn = jarclean.clean_jar(raw)
            inside = jarclean.waptai_strings_inside(clean)
        except RateLimited:
            raise
        except Exception as e:
            bad += 1
            print(f"loi jar {r['source_id']} {d['url']}: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        open(path, "wb").write(clean)
        local[d["url"]] = {"url": d["url"], "file": f"{r['source_id']}/{os.path.basename(path)}",
                           "resolution": d["resolution"], "bytes_orig": len(raw), "bytes_clean": len(clean),
                           "sha256_orig": hashlib.sha256(raw).hexdigest(), "sha256_clean": hashlib.sha256(clean).hexdigest(),
                           "changed": clean != raw, "removed": log, "warnings": warn, "waptai_inside": inside}
        new += 1
        r["local"] = {"files": list(local.values())}
    r["local"] = {"files": list(local.values())}
    return new, bad


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="thu muc data (chua waptai/posts)")
    ap.add_argument("--jar-out", required=True, help="thu muc luu JAR sach")
    ap.add_argument("--ids", default="", help="id bai, cach nhau dau phay")
    ap.add_argument("--all", action="store_true", help="tat ca bai game/phan_mem qua bo loc co JAR")
    ap.add_argument("--res", default="", help="chi lay cac do phan giai nay, vi du 240x320,320x240")
    ap.add_argument("--max-per-post", type=int, default=None)
    ap.add_argument("--delay", type=float, default=2.0)
    a = ap.parse_args(argv)
    f = Fetcher(delay=a.delay, timeout=90)
    ids = [int(x) for x in a.ids.split(",") if x.strip()]
    if a.all:
        import glob
        for fp in glob.glob(os.path.join(a.data, "waptai", "posts", "*.json")):
            rr = json.load(open(fp, encoding="utf-8"))
            if rr["kind"] in ("game", "phan_mem") and rr["filter"]["status"] == "ok" and rr["has_own_file"]:
                ids.append(rr["source_id"])
        ids = sorted(set(ids))
    res = {x.strip() for x in a.res.split(",") if x.strip()} or None
    pdir = os.path.join(a.data, "waptai", "posts")
    new = bad = 0
    for pid in ids:
        path = os.path.join(pdir, f"{pid}.json")
        r = json.load(open(path, encoding="utf-8"))
        if r["filter"]["status"] != "ok":
            print(f"bo qua {pid}: bo loc {r['filter']['status']}", file=sys.stderr)
            continue
        try:
            n, b = process_post(r, a.jar_out, f, res, a.max_per_post)
        except RateLimited as e:
            json.dump(r, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(f"DUNG: site gioi han tai (429), thu lai sau {e.retry_after}s. Da lam {new} JAR trong lan chay nay.", file=sys.stderr)
            print(f"dung do 429: {new} JAR moi, {bad} loi")
            return 3
        json.dump(r, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        new += n
        bad += b
    print(f"xong: {new} JAR moi, {bad} loi, {f.requests} yeu cau")
    return 1 if bad and not new else 0


if __name__ == "__main__":
    sys.exit(main())
