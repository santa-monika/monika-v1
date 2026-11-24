"""Lay chi muc URL (CDX) cua mot site tu archive.org, chi metadata, khong tai file.
Ghi data/archive/<site>/cdx.jsonl.gz (moi dong: {t, u, m, s, l, d}) + summary.json.
Gioi han toc do, dung ngay khi gap 429. Chay trong GitHub Actions (web.archive.org khong vao duoc tu moi truong cloud cua Claude)."""
import argparse, collections, gzip, json, os, sys, urllib.parse
from .common import Fetcher, RateLimited

CDX = "https://web.archive.org/cdx/search/cdx"
FIELDS = "timestamp,original,mimetype,statuscode,length,digest"
PAGE = 50000  # dong moi trang, dung resumeKey de lay tiep


def fetch_all(site, fetcher, limit_pages=100):
    key = None
    rows = []
    for _ in range(limit_pages):
        q = {"url": site, "matchType": "domain", "output": "json", "fl": FIELDS, "filter": "statuscode:200",
             "collapse": "urlkey", "limit": PAGE, "showResumeKey": "true"}
        if key:
            q["resumeKey"] = key
        raw = fetcher.get(CDX + "?" + urllib.parse.urlencode(q))
        data = json.loads(raw) if raw.strip() else []
        key = None
        if data and len(data) >= 2 and data[-2] == [] and isinstance(data[-1], list) and len(data[-1]) == 1:
            key = data[-1][0]
            data = data[:-2]
        if data and data[0][0] == "timestamp":
            data = data[1:]
        rows += data
        print(f"{site}: {len(rows)} dong", flush=True)
        if not key:
            break
    return rows


def summarize(rows):
    ext = collections.Counter()
    top = collections.Counter()
    for t, u, m, s, l, d in rows:
        path = urllib.parse.urlsplit(u).path
        e = path.rsplit(".", 1)[-1].lower() if "." in path.rsplit("/", 1)[-1] else "(none)"
        ext[e] += 1
        parts = [x for x in path.split("/") if x]
        top["/".join(parts[:2]) if len(parts) > 1 else "/"] += 1
    return {"total": len(rows), "ext": ext.most_common(25), "thu_muc_2_cap": top.most_common(60)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--sites", nargs="+", required=True)
    ap.add_argument("--delay", type=float, default=3.0)
    a = ap.parse_args(argv)
    f = Fetcher(delay=a.delay, timeout=180)
    for site in a.sites:
        d = os.path.join(a.out, "archive", site)
        os.makedirs(d, exist_ok=True)
        try:
            rows = fetch_all(site, f)
        except RateLimited as e:
            print("429 tu archive.org, dung:", e, file=sys.stderr)
            return 3
        with gzip.open(os.path.join(d, "cdx.jsonl.gz"), "wt", encoding="utf-8") as g:
            for t, u, m, s, l, dg in rows:
                g.write(json.dumps({"t": t, "u": u, "m": m, "s": s, "l": l, "d": dg}, ensure_ascii=False) + "\n")
        json.dump(summarize(rows), open(os.path.join(d, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
