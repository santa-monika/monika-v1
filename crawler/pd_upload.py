"""Dua JAR da lam sach (crawler.waptai_jars) len Pixeldrain cua sep, dedupe theo sha256, ghi id vao JSON bai.
Xac thuc: bien moi truong PD_KEY (Basic auth) neu co; trong moi truong cloud proxy tu chen thong tin.
Tai len khong phai la dang bai: chi cat file vao kho. Chay lai duoc: tep da co pixeldrain_id thi bo qua."""
import argparse, base64, json, os, sys, time, urllib.error, urllib.parse, urllib.request

API = "https://pixeldrain.com/api"


def _req(method, path, data=None, headers=None, timeout=300):
    h = dict(headers or {})
    key = os.environ.get("PD_KEY")
    if key:
        h["Authorization"] = "Basic " + base64.b64encode(f":{key}".encode()).decode()
    req = urllib.request.Request(API + path, data=data, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or "{}")


def pd_name(post_id, file):
    return f"waptai-{post_id}-{os.path.basename(file)}"


def load_known(index_path):
    """sha256 -> id cua cac file da co tren Pixeldrain (chi muc tu repo du lieu)."""
    if not index_path or not os.path.exists(index_path):
        return {}
    return {f["sha256"]: f["id"] for f in json.load(open(index_path, encoding="utf-8")) if f.get("sha256")}


def upload_one(path, name):
    data = open(path, "rb").read()
    last = None
    for attempt in range(3):
        try:
            return _req("PUT", "/file/" + urllib.parse.quote(name), data, {"Content-Type": "application/java-archive"})["id"]
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code} {e.read()[:200]!r}"
            if e.code in (400, 401, 403, 413):
                break
        except Exception as e:
            last = repr(e)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"upload {name}: {last}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--jar-out", required=True)
    ap.add_argument("--index", default="", help="data/pixeldrain/index.json de dedupe (tuy chon)")
    ap.add_argument("--ids", default="", help="chi cac id bai nay (de trong = tat ca)")
    ap.add_argument("--limit", type=int, default=0, help="toi da n tep (thu nghiem)")
    a = ap.parse_args(argv)
    known = load_known(a.index)
    want = {int(x) for x in a.ids.split(",") if x.strip()}
    import glob
    up = dup = bad = 0
    for fp in sorted(glob.glob(os.path.join(a.data, "waptai", "posts", "*.json")), key=lambda p: int(os.path.basename(p)[:-5])):
        r = json.load(open(fp, encoding="utf-8"))
        if want and r["source_id"] not in want:
            continue
        dirty = False
        for x in r.get("local", {}).get("files", []):
            if x.get("pixeldrain_id"):
                continue
            if x["sha256_clean"] in known:
                x["pixeldrain_id"], x["pixeldrain_dup"] = known[x["sha256_clean"]], True
                dup += 1
                dirty = True
                continue
            if a.limit and up >= a.limit:
                break
            path = os.path.join(a.jar_out, x["file"])
            try:
                pid = upload_one(path, pd_name(r["source_id"], x["file"]))
                info = _req("GET", f"/file/{pid}/info")
                if info.get("hash_sha256") != x["sha256_clean"]:
                    raise RuntimeError(f"sha256 lech: {pid}")
            except Exception as e:
                bad += 1
                print(f"loi {x['file']}: {e}", file=sys.stderr)
                continue
            x["pixeldrain_id"], x["pixeldrain_name"] = pid, pd_name(r["source_id"], x["file"])
            known[x["sha256_clean"]] = pid
            up += 1
            dirty = True
        if dirty:
            json.dump(r, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if a.limit and up >= a.limit:
            break
    print(f"xong: {up} tep len, {dup} da co (trung sha256), {bad} loi")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
