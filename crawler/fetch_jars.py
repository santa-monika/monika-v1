"""Tai JAR theo danh muc (crawler.inventory), kiem tra, quet quang cao nhung, dedupe sha256, dua len Pixeldrain, ghi ket qua vao state jsonl.
Chay lai duoc: URL da co trong state thi bo qua. Dung ngay khi gap 429 (khong thu lai, ton trong gioi han cua site).
Nguon: direct | xtgem (trang trung gian 'Download', di theo link do voi Referer, nhu nguoi dung bam) | archive (web.archive.org .../<ts>id_/<url>).
Khong lach gioi han: khong doi IP, khong gia nhieu trinh duyet; mot luong, nghi giua cac yeu cau."""
import argparse, hashlib, html, io, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error, zipfile
from .common import UA, RateLimited
from . import pd_upload, jarpromo

PROMO = re.compile(rb"(wapvip|giaitri321|quangninhwap|wapm4u|xtgem|waptai|wap\.sh|uiwap|dongthap|campha1|tntinhyeu|hoangxuanpro|meovathay|mtaiaz)", re.I)
HOTLINK = re.compile(rb'href="([^"]*xthotlink[^"]*)"')


def http_get(url, referer=None, timeout=60):
    h = {"User-Agent": UA}
    if referer:
        h["Referer"] = referer
    q = urllib.parse.quote(url, safe=":/?&=%._-~@+,()")
    try:
        with urllib.request.urlopen(urllib.request.Request(q, headers=h), timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 429:
            ra = e.headers.get("Retry-After") if e.headers else None
            raise RateLimited(url, int(ra) if ra and ra.isdigit() else None)
        raise


def fetch(item, delay):
    u = item["url"]
    if item["via"] == "archive":
        u = f"https://web.archive.org/web/{item['ts']}id_/{u}"
    b = http_get(u)
    if b[:2] != b"PK" and item["via"] == "xtgem":
        m = HOTLINK.search(b)
        if m:
            time.sleep(delay)
            b = http_get(urllib.parse.urljoin(u, html.unescape(m.group(1).decode())), referer=u)
    return b


def inspect(raw):
    """-> dict: ok, error, midlets, promo (cac cho nghi la quang cao nhung), icon (ten muc png) """
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
        bad = z.testzip()
        if bad:
            return {"ok": False, "error": f"zip loi: {bad}"}
        names = z.namelist()
        mf = z.read("META-INF/MANIFEST.MF") if "META-INF/MANIFEST.MF" in names else b""
    except Exception as e:
        return {"ok": False, "error": f"khong phai zip: {type(e).__name__}"}
    text = mf.decode("utf-8", "replace").replace("\r\n", " ").replace("\n ", "")
    midlets = re.findall(r"^MIDlet-(\d+):\s*(.*)$", mf.decode("utf-8", "replace").replace("\r\n", "\n"), re.M)
    if not midlets:
        return {"ok": False, "error": "khong co MIDlet-1"}
    promo = sorted({m.group(1).decode().lower() for m in PROMO.finditer(mf)})
    promo += [f"muc:{n}" for n in names if PROMO.search(n.encode("utf-8", "replace"))][:3]
    for n in names:
        if n.endswith(".class") and z.getinfo(n).file_size <= 6000:
            m = PROMO.search(z.read(n))
            if m:
                promo.append(f"class:{n}:{m.group(1).decode().lower()}")
                break
    icon = None
    parts = [p.strip() for p in midlets[0][1].split(",")]
    if len(parts) > 1 and parts[1].lstrip("/") in names:
        icon = parts[1].lstrip("/")
    return {"ok": True, "midlets": len(midlets), "promo": promo, "icon": icon, "name": parts[0]}


def pd_name(src, gid, file):
    return f"{src}-{gid}-" + re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(file))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--inv", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--index", default="", help="data/pixeldrain/index.json de dedupe")
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--budget-s", type=int, default=0, help="dung sau chung nay giay")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1, help="chia theo nhom game (gid % nshards == shard) de chay song song tren nhieu runner")
    ap.add_argument("--seen", default="", help="glob cac state khac chi doc (de bo qua tep da xong)")
    a = ap.parse_args(argv)
    inv = [json.loads(l) for l in open(a.inv, encoding="utf-8")]
    gids = {}
    for it in inv:
        gids.setdefault(it["group"], len(gids) + 1)
    done = set()
    import glob as _glob
    seen_files = [f for f in _glob.glob(a.seen)] if a.seen else []
    known = {}
    if a.index and os.path.exists(a.index):
        # chi dung lai tep cu neu ten khop quy tac cua Worker /v1/p (ten khac se khong phat duoc), con lai up lai voi ten dung
        known = {f["sha256"]: f["id"] for f in json.load(open(a.index, encoding="utf-8"))
                 if f.get("sha256") and re.match(r"^(waptai|qnw|gt321|wvip)-\d+-.+\.jar$", f.get("name", ""), re.I)}
    for sf in ([a.state] if os.path.exists(a.state) else []) + [f for f in seen_files if f != a.state]:
        for l in open(sf, encoding="utf-8"):
            r = json.loads(l)
            if r.get("ok") and r.get("promo") and not r.get("pixeldrain_id"):
                continue  # ban cu bi giu lai vi quang cao: tai lai de lam sach
            done.add(r["url"])
            if r.get("sha256") and r.get("pixeldrain_id"):
                known[r["sha256"]] = r["pixeldrain_id"]
    t0, n, nbad = time.time(), 0, 0
    out = open(a.state, "a", encoding="utf-8")
    for it in inv:
        if it["url"] in done or gids[it["group"]] % a.nshards != a.shard:
            continue
        if (a.limit and n >= a.limit) or (a.budget_s and time.time() - t0 > a.budget_s):
            break
        n += 1
        rec = {"url": it["url"], "group": it["group"], "gid": gids[it["group"]], "src": it["src"]}
        try:
            raw = fetch(it, a.delay)
            try:
                raw, log = jarpromo.clean_jar(raw)
            except Exception:
                log = []
            if log:
                rec["cleaned"] = log
            info = inspect(raw)
            rec.update(info)
            if info["ok"]:
                rec["sha256"] = hashlib.sha256(raw).hexdigest()
                rec["bytes"] = len(raw)
                if rec["sha256"] in known:
                    rec.update(pixeldrain_id=known[rec["sha256"]], dup=True)
                elif not a.no_upload:
                    name = pd_name(it["src"], rec["gid"], it["file"])
                    path = f"/tmp/fj-{os.getpid()}.jar"
                    open(path, "wb").write(raw)
                    rec["pixeldrain_id"] = pd_upload.upload_one(path, name)
                    rec["pd_name"] = name
                    known[rec["sha256"]] = rec["pixeldrain_id"]
                    os.remove(path)
        except RateLimited as e:
            print("429, dung:", e, file=sys.stderr)
            break
        except urllib.error.HTTPError as e:
            rec.update(ok=False, error=f"HTTP {e.code}")
        except Exception as e:
            rec.update(ok=False, error=f"{type(e).__name__}: {str(e)[:80]}")
        if not rec.get("ok"):
            nbad += 1
        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        out.flush()
        if n % 10 == 0:
            print(f"{n} tep, {nbad} loi, {int(time.time() - t0)} giay", flush=True)
        time.sleep(a.delay)
    print(f"xong lan chay: {n} tep, {nbad} loi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
