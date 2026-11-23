"""Lap chi muc thu vien Pixeldrain cua chu du an (chi metadata + sha256). Can PD_KEY neu tai khoan khong cong khai."""
import argparse, base64, json, os, re, sys, urllib.request
from .normalize import norm_title, resolution, variant_kind


def fetch_files():
    req = urllib.request.Request("https://pixeldrain.com/api/user/files")
    key = os.environ.get("PD_KEY")
    if key:
        req.add_header("Authorization", "Basic " + base64.b64encode(f":{key}".encode()).decode())
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["files"]


def build(files):
    out = []
    for f in files:
        n = f["name"]
        if not n.lower().endswith((".jar", ".jad", ".sis", ".sisx", ".zip")):
            continue
        out.append({"id": f["id"], "name": n, "size": f["size"], "sha256": f.get("hash_sha256"),
                    "norm_title": norm_title(re.sub(r"^((aowvn|ts|s60|s40)[-_])+", "", n, flags=re.I)),
                    "resolution": resolution(n), "kind": variant_kind(n),
                    "ext": os.path.splitext(n)[1].lower()})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    idx = build(fetch_files())
    os.makedirs(os.path.join(a.out, "pixeldrain"), exist_ok=True)
    json.dump(idx, open(os.path.join(a.out, "pixeldrain", "index.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"pixeldrain: {len(idx)} file")
