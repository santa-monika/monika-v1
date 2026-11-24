"""bisduckopath.blogspot.com: nguon Blogger con cap nhat (ban Viet hoa, mod, port, ban va). Cac buoc, chay lai duoc:
  sync     feed JSON (toan bo, hoac --since de chi lay bai moi sua) -> data/bisducko/posts/<id>.json (giu html goc, phan loai, phat hien bai doi)
  resolve  mo link MediaFire cua bai doi (API co sha256/revision) -> danh sach tep; so voi lan truoc de ghi lich su: moi / ban va / go bo
  fetch    tai tep moi hoac da doi, gai zip nhieu JAR, go quang cao nhung, dedupe sha256, up Pixeldrain (ten bdk-<n>-...)
  build    posts.json (cho tools/blogger-import.mjs) + bdk-aliases.json (khoa on dinh -> tep Pixeldrain hien hanh) + bao cao
Game Port (chi chay tren gia lap): meta `port: 1`, nhan Port, tieu de giu [Port]; Worker an khoi app. Khong lay game online, ban nguoi lon, co bac."""
import argparse, collections, hashlib, html as htmllib, io, json, os, re, sys, time, urllib.parse, urllib.request, zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from .common import UA, RateLimited
from .filters import classify
from .normalize import strip_accents
from . import mediafire as mf, jarpromo, pd_upload
from .fetch_jars import inspect, pd_name

BLOG = "https://bisduckopath.blogspot.com"
FEED = BLOG + "/feeds/posts/default"
API = "http://api.justmonika.top"
RES = re.compile(r"(?<!\d)(\d{2,4})\s*[xX×]\s*(\d{2,4})(?!\d)")
JAR_EXT = (".jar",)
NOT_JAVA_LABELS = {"Game Android", "Game PS và PSP", "Game PS và PSP Việt Hoá", "Game NDS", "Game NDS Việt Hoá", "Gameboy Advance", "Gameboy Advance Việt Hoá",
                   "Game NES và SNES", "Game NES và SNES Việt Hoá", "Game Android Việt Hoá"}
SKIP_LABELS = {"Game Online": "game online", "Casino": "co bac", "Game Người Lớn": "18+", "News": "tin rieng cua site nguon",
               "Blogger - Blogspot": "mau Blogger, khong lien quan"}
ONLINE_TITLE = re.compile(r"(online|ngoc\s*rong|\bnro\b|ninja\s*school|gopet|\bkpah\b|army\s*\d?\b)", re.I)
OFFLINE = re.compile(r"\boffline\b", re.I)
RESCUE = re.compile(r"007\s*casino\s*royale", re.I)  # game James Bond, khong phai co bac
ARTICLE_LABELS = {"Thủ Thuật", "JavaME Wiki", "Giả Lập", "Firmware", "CFW", "Source Code", "Phim"}
GENRE = {"Nhập Vai": "Nhập vai", "Hành Động": "Hành động", "Chiến Thuật": "Chiến thuật", "Giải Đố": "Giải đố & trí tuệ", "Phiêu Lưu": "Phiêu lưu",
         "Arcade": "Arcade & chạy nhảy", "Bắn Súng": "Bắn súng", "Đua Xe": "Đua xe", "Đối Kháng": "Đối kháng", "Kinh Dị": "Sinh tồn & kinh dị",
         "Nông Trại": "Mô phỏng & quản lý", "Bóng Đá": "Thể thao", "Thể Thao": "Thể thao", "Phòng Thủ Tháp": "Thủ thành", "Thủ Tháp": "Thủ thành",
         "Sinh Tồn": "Sinh tồn & kinh dị", "Vui Nhộn": "Trẻ em & vui nhộn", "Đi Cảnh 2D": "Arcade & chạy nhảy", "Metroidvania": "Phiêu lưu",
         "3D Platformer": "Arcade & chạy nhảy", "Chạy Và Bắn": "Hành động", "Bắn Máy Bay": "Bắn súng", "Bắn Bóng": "Giải đố & trí tuệ",
         "Chặt Chém": "Hành động", "Thẻ Bài": "Cờ & bài", "Hàng Hải": "Phiêu lưu", "Đua Thuyền": "Đua xe", "Tank": "Bắn súng",
         "Visual Novel": "Phiêu lưu", "Động Vật": "Trẻ em & vui nhộn", "Sủng Vật": "Mô phỏng & quản lý"}
APP_CATS = [("Giả lập & chạy game", r"gia\s*lap|emulator|phoneme|kemulator|j2mex|jl-?mod|pstros|meboy"), ("Mạng & trình duyệt", r"opera|browser|ucweb|web|telegram|mpgram"),
            ("Trình phát nhạc & video", r"youtube|ttpod|nhac|music|tone|player|coreplay"), ("Công cụ hệ thống", r"manager|quan\s*ly|file|task|xplore|jar tool|patcher|tool|key|control|test")]
PRIORITY = ["240x320", "320x240", "240x400", "176x220", "176x208", "128x160", "128x128", "360x640", "640x360", "320x480", "480x800", "480x640", "352x416"]


# ---------- feed ----------
def http_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_feed(since=None, delay=1.0):
    out, start = [], 1
    while True:
        q = {"alt": "json", "max-results": 150, "start-index": start, "orderby": "updated"}
        if since:
            q["updated-min"] = since
        feed = http_json(FEED + "?" + urllib.parse.urlencode(q))["feed"]
        ents = feed.get("entry", [])
        out += ents
        if len(ents) < 150:
            return out
        start += 150
        time.sleep(delay)


def entry_to_post(e):
    alt = next((l["href"] for l in e.get("link", []) if l.get("rel") == "alternate"), "")
    return {"id": re.search(r"post-(\d+)$", e["id"]["$t"]).group(1), "url": alt, "title": htmllib.unescape(e["title"]["$t"]).strip(),
            "published": e["published"]["$t"], "updated": e["updated"]["$t"], "labels": [c["term"] for c in e.get("category", [])],
            "html": e["content"]["$t"]}


# ---------- html ----------
class Scan(HTMLParser):
    """Rut: link (nhan + href), anh (src + link bao quanh), cac dong van ban sach (giu a ngoai MediaFire, b/i)."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.imgs, self.lines, self.cur, self._a, self._txt, self._skip = [], [], [], [], None, [], 0

    def flush(self):
        t = "".join(self.cur).strip()
        if t:
            self.lines.append(t)
        self.cur = []

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag in ("script", "style", "iframe"):
            self._skip += 1
        elif tag in ("br", "div", "p", "li", "tr", "h1", "h2", "h3", "h4", "ul", "ol"):
            self.flush()
            if tag == "li":
                self.cur.append("• ")
        elif tag == "a" and a.get("href"):
            self._a = {"href": htmllib.unescape(a["href"]), "txt": []}
        elif tag == "img" and a.get("src"):
            self.imgs.append({"src": a["src"], "href": self._a["href"] if self._a else "", "w": a.get("data-original-width"), "h": a.get("data-original-height")})
        elif tag in ("b", "strong") and not self._a:
            self.cur.append("<b>")
        elif tag in ("i", "em") and not self._a:
            self.cur.append("<i>")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "iframe"):
            self._skip = max(0, self._skip - 1)
        elif tag == "a" and self._a:
            a, self._a = self._a, None
            label = " ".join("".join(a["txt"]).split())
            if not self._skip:
                self.links.append({"href": a["href"], "label": label})
                if not mf.link_key(a["href"]) and label and re.match(r"https?://", a["href"]):
                    self.cur.append(f'<a href="{htmllib.escape(a["href"], True)}" rel="nofollow noopener">{htmllib.escape(label)}</a>')
        elif tag in ("b", "strong") and not self._a:
            self.cur.append("</b>")
        elif tag in ("i", "em") and not self._a:
            self.cur.append("</i>")
        elif tag in ("div", "p", "li", "tr", "h1", "h2", "h3", "h4", "ul", "ol"):
            self.flush()

    def handle_data(self, d):
        if self._skip:
            return
        if self._a is not None:
            self._a["txt"].append(d)
            if mf.link_key(self._a["href"]):
                return
            return  # van ban link ngoai duoc them o handle_endtag (dang <a>)
        self.cur.append(htmllib.escape(d))


def scan(html):
    s = Scan()
    s.feed(html)
    s.flush()
    return s


DROP_LINE = re.compile(r"^(?:[\s|/•\-–·]*|.*(?:đổi tên thành \.?jar|định dạng \.zip|\.zip thì).*|(?:tải xuống|dự phòng|link dự phòng|download)[\s|:]*)$", re.I)


def clean_lines(lines):
    out = []
    for l in lines:
        t = re.sub(r"</?[bi]>|<a [^>]*>|</a>", "", l)
        if DROP_LINE.match(t.strip()):
            continue
        out.append(l)
    return out


def img_id(src):
    m = re.search(r"/(AV[\w-]{20,})", src)
    return (m.group(1)[:80] if m else re.sub(r"=?[swh]\d+.*$", "", src.rsplit("/", 1)[-1]))[:80]


def img_url(img, w=640):
    """Anh goc (bo kich thuoc /sNNN/ -> /s<w>/ de trang nhe). Giu nguyen noi dung anh, khong sua/cat."""
    u = img["src"]
    return re.sub(r"/s\d+(-[a-z0-9-]*)?/", f"/s{w}/", u, count=1)


# ---------- phan loai ----------
def classify_post(p):
    L, t = set(p["labels"]), p["title"]
    if not L and not re.search(r"game|việt hoá|việt hóa|^\[", t, re.I):
        return {"kind": None, "skip": "trang tinh (Donate/Contact)"}
    for lab, why in SKIP_LABELS.items():
        if lab in L and not (lab == "Game Online" and OFFLINE.search(t)):
            return {"kind": None, "skip": why}
    st, why = classify(t, "")
    if st == "loai" and not RESCUE.search(t):
        return {"kind": None, "skip": f"18+/co bac {why[:2]}"}
    java = "Game Java" in L or (not L and bool(re.search(r"game", t, re.I)))
    if not java and L & NOT_JAVA_LABELS:
        return {"kind": None, "skip": "khong phai Java (Android/PSP/NDS/GBA/NES)"}
    if (java or not L) and ONLINE_TITLE.search(strip_accents(t)) and not OFFLINE.search(t):
        return {"kind": None, "skip": "game online / game co may chu"}
    port = bool(L & {"Game Java Port", "Game Port"}) or t.lower().startswith("[port]")
    if java and "Android" in L and "Game Port" in L and "Game Java Port" not in L:
        return {"kind": None, "skip": "port iOS sang Android (khong phai Java)"}
    if "Chủ Đề - Theme" in L:
        return {"kind": "media", "port": False}
    if java and not (L & ARTICLE_LABELS and not (L & {"Game Java Việt Hoá", "Game Java Mod"}) and re.search(r"hướng dẫn|cách", t, re.I)):
        return {"kind": "game", "port": port}
    if L & {"Java App", "App và Tools"}:
        return {"kind": "app", "port": False}
    if L & ARTICLE_LABELS:
        return {"kind": "post", "port": False}
    return {"kind": "post" if not java else "game", "port": port and java}


def clean_title(t):
    t = re.sub(r"^\s*\[(?:Phát Hành|Java|Hoàn Thành|Game Java|Update v?\d+)\]\s*", "", t, flags=re.I)
    t = re.sub(r"\s*[|｜]\s*(?:Game Java.*|Java App.*|Trình quản lý file.*|bisduckoPath|App Telegram.*)$", "", t, flags=re.I)
    t = re.sub(r"^\s*Tải\s+Game\s+Java\s+", "", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip(" |-–")


def version_of(p):
    for src in (p["title"], p.get("_text", "")):
        m = re.search(r"\bv(?:er(?:sion)?)?\.?\s*(\d+(?:\.\d+)+|\d+)\b", src, re.I)
        if m:
            return m.group(1)
    return ""


def plat_of(s):
    s = s.lower()
    if re.search(r"s60|symbian|e\d\d\b|n\d\d\b", s):
        return "s60"
    return "s40" if "s40" in s else "j2me"


def variant_of(label, fn):
    both = f"{label} {fn}"
    m = RES.search(both)
    res = f"{m.group(1)}x{m.group(2)}" if m else None
    s = strip_accents(both).lower()
    kind = "vh" if re.search(r"viet\s*hoa|\bvh\b|tieng\s*viet|\bvi\b|_vi[_.\s]", s) else "goc"
    return res, plat_of(both), kind


# ---------- trang thai ----------
def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pfile(d, pid):
    return os.path.join(d, "posts", f"{pid}.json")


def load(d, pid):
    f = pfile(d, pid)
    return json.load(open(f, encoding="utf-8")) if os.path.exists(f) else None


def save(d, rec):
    os.makedirs(os.path.join(d, "posts"), exist_ok=True)
    json.dump(rec, open(pfile(d, rec["id"]), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def all_posts(d):
    fs = sorted(os.listdir(os.path.join(d, "posts"))) if os.path.isdir(os.path.join(d, "posts")) else []
    return [json.load(open(os.path.join(d, "posts", f), encoding="utf-8")) for f in fs if f.endswith(".json")]


def next_n(d):
    return max([p.get("n", 0) for p in all_posts(d)] + [0]) + 1


def cmd_sync(a):
    ents = [entry_to_post(e) for e in fetch_feed(a.since or None)]
    n0, new, changed = next_n(a.data), 0, 0
    seen = set()
    for p in ents:
        seen.add(p["id"])
        old = load(a.data, p["id"])
        c = classify_post(p)
        sc = scan(p["html"])
        sha = hashlib.sha256(p["html"].encode()).hexdigest()[:16]
        if old and old.get("html_sha") == sha and old.get("updated") == p["updated"] and not a.force:
            continue
        rec = old or {"n": n0, "history": [], "files": [], "rev": 0, "seen": now_iso()}
        if not old:
            n0 += 1
            new += 1
        else:
            changed += 1
        rec.update({k: p[k] for k in ("id", "url", "title", "published", "updated", "labels", "html")}, html_sha=sha, kind=c["kind"],
                   port=c.get("port", False), skip=c.get("skip", ""), gone=False, dirty=True,
                   links=[{"href": l["href"], "label": l["label"], "ord": i} for i, l in enumerate(sc.links) if mf.link_key(l["href"])],
                   ext_links=[{"href": l["href"], "label": l["label"]} for l in sc.links
                              if not mf.link_key(l["href"]) and re.search(r"drive\.google|mega\.nz|taptin|modsfire|storage\.to|mydrive|github\.com|workers\.dev|vercel", l["href"])])
        rec["history"].append({"at": now_iso(), "ev": "moi" if not old else "bai doi", "updated": p["updated"]})
        save(a.data, rec)
    if not a.since:  # quet day du: bai khong con tren feed
        for r in all_posts(a.data):
            if r["id"] not in seen and not r.get("gone"):
                r["gone"] = True
                r["history"].append({"at": now_iso(), "ev": "go khoi feed"})
                save(a.data, r)
    print(f"sync: {len(ents)} bai tren feed, {new} moi, {changed} doi")


def cmd_resolve(a):
    posts = all_posts(a.data)
    cutoff = time.time() - a.recheck * 86400
    todo = [p for p in posts if p["kind"] in ("game", "app", "post", "media") and not p.get("gone") and
            (p.get("dirty") or (a.recheck and time.mktime(time.strptime(p.get("checked", "1970-01-01T00:00:00Z"), "%Y-%m-%dT%H:%M:%SZ")) < cutoff))]
    todo = [p for p in todo if p["n"] % a.nshards == a.shard]
    todo.sort(key=lambda p: p.get("checked", ""))
    if a.limit:
        todo = todo[:a.limit]
    nev = 0
    for p in todo:
        old = {f["qk"]: f for f in p["files"]}
        new, errs = [], []
        for l in p["links"]:
            kind, key = mf.link_key(l["href"])
            try:
                fs = mf.folder_files(key, a.delay) if kind == "folder" else [mf.file_info(key, a.delay)]
            except RateLimited as e:
                print("429, dung:", e, file=sys.stderr)
                return 1
            except Exception as e:
                errs.append({"href": l["href"], "error": str(e)[:100]})
                continue
            for f in fs:
                f["hint"] = {"label": l["label"], "ord": l["ord"], "folder": kind == "folder"}
                if any(x["qk"] == f["qk"] for x in new):
                    continue
                o = old.get(f["qk"])
                if o and o.get("mf_sha") == f["mf_sha"]:
                    f = {**o, "hint": f["hint"], "rev": f["rev"]}
                else:
                    if o:
                        p["history"].append({"at": now_iso(), "ev": "ban va (tep doi noi dung)", "file": f["fn"], "created": f["created"]})
                    elif old:
                        p["history"].append({"at": now_iso(), "ev": "tep moi", "file": f["fn"], "created": f["created"]})
                    f["status"] = "pending"
                new.append(f)
        for q, o in old.items():
            if not any(x["qk"] == q for x in new) and not errs:
                p["history"].append({"at": now_iso(), "ev": "tep bi go", "file": o["fn"]})
        if errs and not new:
            new = p["files"]  # that bai tam thoi: giu nguyen, lan sau thu lai
        p["files"], p["link_errors"], p["dirty"], p["checked"] = new, errs, False, now_iso()
        p["rev"] = 1 + sum(1 for h in p["history"] if h["ev"].startswith(("ban va", "tep moi")))
        save(a.data, p)
        nev += 1
    print(f"resolve: {nev} bai")
    return 0


# ---------- tai tep ----------
def jars_in(raw, fn):
    """-> [(ten, bytes)] cac JAR trong tep: chinh no (neu la MIDlet) hoac cac .jar ben trong zip (goi nhieu cỡ man hinh)."""
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
    except Exception:
        return []
    names = z.namelist()
    if "META-INF/MANIFEST.MF" in names and b"MIDlet-1" in z.read("META-INF/MANIFEST.MF"):
        return [(fn, raw)]
    out = []
    for n in names:
        if n.lower().endswith(".jar") and not n.endswith("/") and z.getinfo(n).file_size < 60_000_000:
            out.append((os.path.basename(n), z.read(n)))
    return out[:30]


def cmd_fetch(a):
    index = {}
    if a.index and os.path.exists(a.index):
        index = {f["sha256"]: f["id"] for f in json.load(open(a.index, encoding="utf-8"))
                 if f.get("sha256") and re.match(r"^(waptai|qnw|gt321|wvip|bdk)-\d+-.+\.jar$", f.get("name", ""), re.I)}
    for p in all_posts(a.data):  # da up trong cac lan chay truoc
        for f in p["files"]:
            for j in f.get("jars", []):
                if j.get("sha256") and j.get("pd_id"):
                    index[j["sha256"]] = j["pd_id"]
    t0, n, nbad = time.time(), 0, 0
    posts = [p for p in all_posts(a.data) if p["kind"] in ("game", "app") and not p.get("gone") and p["n"] % a.nshards == a.shard]
    for p in posts:
        for f in p["files"]:
            if f.get("status") != "pending" and not (a.retry and f.get("status") == "error"):
                continue
            if (a.limit and n >= a.limit) or (a.budget_s and time.time() - t0 > a.budget_s):
                print(f"fetch: dung, {n} tep, {nbad} loi")
                return 0
            n += 1
            ext = os.path.splitext(f["fn"])[1].lower()
            if ext not in (".jar", ".zip"):
                f.update(status="other", jars=[])
                save(a.data, p)
                continue
            try:
                raw = mf.download(f["qk"], a.delay, f.get("mf_sha") or None)
                jars = []
                for name, jb in jars_in(raw, f["fn"]):
                    try:
                        jb, log = jarpromo.clean_jar(jb)
                    except Exception:
                        log = []
                    info = inspect(jb)
                    if not info["ok"]:
                        continue
                    sha = hashlib.sha256(jb).hexdigest()
                    rec = {"name": name, "sha256": sha, "bytes": len(jb), "midlet": info.get("name", ""), "cleaned": log or None}
                    if sha in index:
                        rec.update(pd_id=index[sha], dup=True)
                    elif not a.no_upload:
                        pn = pd_name("bdk", p["n"], f"{f['qk'][:6]}-{name}")
                        path = f"/tmp/bdk-{os.getpid()}.jar"
                        open(path, "wb").write(jb)
                        rec.update(pd_id=pd_upload.upload_one(path, pn), pd_name=pn)
                        os.remove(path)
                        index[sha] = rec["pd_id"]
                    jars.append(rec)
                f.update(status="ok" if jars else "other", jars=jars, error="")
            except RateLimited as e:
                print("429, dung:", e, file=sys.stderr)
                save(a.data, p)
                return 1
            except Exception as e:
                f.update(status="error", error=f"{type(e).__name__}: {str(e)[:100]}")
                nbad += 1
            save(a.data, p)
            if n % 10 == 0:
                print(f"{n} tep, {nbad} loi, {int(time.time() - t0)} giay", flush=True)
    print(f"fetch xong: {n} tep, {nbad} loi")
    return 0


# ---------- xuat bai ----------
def alias_key(pid, res, plat, kind, idx):
    return "b" + hashlib.sha1(f"{pid}|{res}|{plat}|{kind}|{idx}".encode()).hexdigest()[:10]


def safe_name(title, res, plat, kind):
    t = re.sub(r"[^A-Za-z0-9]+", "_", strip_accents(title)).strip("_")[:40] or "game"
    return "_".join(x for x in (t, res or "", "s60" if plat == "s60" else "", "VH" if kind == "vh" else "") if x) + ".jar"


def variants_of(p, post_res):
    """Cac ban tai da len kho: gop theo sha256, moi ban co khoa on dinh (alias) de ban va thay tep ma link trong bai khong doi."""
    out, seen, count = [], set(), collections.Counter()
    for f in sorted(p["files"], key=lambda f: (f["hint"]["ord"], f["fn"])):
        for j in f.get("jars", []):
            if not j.get("pd_id") or j["sha256"] in seen:
                continue
            seen.add(j["sha256"])
            label = f["hint"]["label"] if not f["hint"].get("folder") else ""
            res, plat, kind = variant_of(label, j["name"])
            if not res and len(post_res) == 1:
                res = post_res[0]
            slot = (res or "Chung", plat, kind)
            idx = count[slot]
            count[slot] += 1
            out.append({"res": slot[0], "plat": plat, "kind": kind, "kb": max(1, round(j["bytes"] / 1024)), "pd": j["pd_id"], "pd_name": j.get("pd_name") or "",
                        "alias": alias_key(p["id"], *slot, idx), "label": label, "name": re.sub(r"\.jar$", "", j["name"], flags=re.I)[:60], "created": f.get("created", "")})
    out.sort(key=lambda v: (PRIORITY.index(v["res"]) if v["res"] in PRIORITY else 99, v["res"], v["plat"], v["kind"], v["kb"]))
    return out[:40]


def genre_cat(p, text):
    for lab in p["labels"]:
        if lab in GENRE:
            return GENRE[lab]
    t = strip_accents(f"{p['title']} {field_text(text, 'Thể Loại')}").lower()
    for name, pat in APP_CATS if p["kind"] == "app" else []:
        if re.search(pat, t):
            return name
    if p["kind"] == "app":
        return "Khác"
    from .posts_generic import cat_of
    return cat_of(t, "game", default="Khác")


def field_text(lines, name):
    for l in lines:
        t = re.sub(r"<[^>]+>", "", l)
        m = re.match(rf"\s*{name}\s*:\s*(.*)", t, re.I)
        if m:
            return m.group(1)
    return ""


HEADER = re.compile(r"^\s*(thể loại|màn hình|tình trạng|nền tảng|thời gian hoàn thành|nội dung|mô tả)\b", re.I)


def desc_of(lines):
    for l in lines:
        t = re.sub(r"<[^>]+>", "", l).strip()
        t = re.sub(r"^(nội dung|mô tả)\s*:\s*", "", t, flags=re.I)
        if t and not HEADER.match(t) and len(t) > 30:
            return htmllib.unescape(t)[:150]
    return ""


def build_post(p, used_imgs, now_ms=None):
    sc = scan(p["html"])
    lines = clean_lines(sc.lines)
    text = [re.sub(r"<[^>]+>", "", l) for l in lines]
    p["_text"] = " ".join(text)
    title = clean_title(p["title"])
    kind = p["kind"]
    seen_i, imgs = set(), []
    for im in sc.imgs:
        i = img_id(im["src"])
        if i in seen_i:
            continue
        seen_i.add(i)
        imgs.append((i, img_url(im)))
    hero = next(((i, u) for i, u in imgs if i not in used_imgs), None)
    if hero:
        used_imgs.add(hero[0])
    post_res = sorted({f"{a}x{b}" for a, b in RES.findall(field_text(lines, "Màn Hình"))}, key=lambda r: (PRIORITY.index(r) if r in PRIORITY else 99, r))
    vs = variants_of(p, post_res) if kind in ("game", "app") else []
    if kind in ("game", "app") and not vs:
        return None, "chua co tep JAR hop le"
    ver = version_of(p) or max([v["created"] for v in vs] + [""]) if vs else version_of(p)
    port = p.get("port")
    shots = "".join(f'<p><img src="{htmllib.escape(u, True)}" alt="{htmllib.escape(title, True)}" style="max-width:100%;height:auto" /></p>\n' for _, u in imgs[:6])
    notice = ""
    if port:
        notice = ('<p><b>PORT:</b> đây là game được port xuống Java (J2ME) nhưng chỉ chạy được trên giả lập (ví dụ J2ME Loader trên Android, KEmulator hoặc JL-Mod trên PC), '
                  'không chạy trên điện thoại Java thật. Trong ứng dụng Monika, mục này không hiển thị; chỉ hiện trên web.</p>\n')
    body = shots + notice + "".join(f"<p>{l}</p>\n" for l in lines)
    ext_rows = []
    if vs:
        rows = "\n".join(f'<tr><td>{htmllib.escape(v["res"])}</td><td>{"S60" if v["plat"] == "s60" else ("S40" if v["plat"] == "s40" else "Java")}'
                         f'{" · Việt hóa" if v["kind"] == "vh" else ""}</td><td>{htmllib.escape(v["name"])}</td><td>{v["kb"]} KB</td>'
                         f'<td><a href="{API}/v1/p/{v["alias"]}/{safe_name(title, v["res"], v["plat"], v["kind"])}">Tải JAR</a></td></tr>' for v in vs)
        body += ('<h3>Tải về theo độ phân giải</h3>\n<table border="1" cellpadding="4" cellspacing="0" width="100%">\n'
                 f'<tr><th>Màn hình</th><th>Nền tảng</th><th>Tệp</th><th>Dung lượng</th><th>Tải</th></tr>\n{rows}\n</table>\n')
        for f in p["files"]:
            if f.get("status") == "other":
                ext_rows.append((f["fn"], f"https://www.mediafire.com/file/{f['qk']}"))
    elif kind in ("post", "media"):
        for f in p["files"]:
            ext_rows.append((f["fn"], f"https://www.mediafire.com/file/{f['qk']}"))
    for l in p.get("ext_links", []):
        ext_rows.append((l["label"] or l["href"], l["href"]))
    if ext_rows:
        body += "<h3>Tệp đính kèm (link nguồn)</h3>\n<ul>\n" + "\n".join(
            f'<li><a href="{htmllib.escape(h, True)}" rel="nofollow noopener">{htmllib.escape(n)}</a></li>' for n, h in ext_rows[:30]) + "\n</ul>\n"
    body += f'<p>Nguồn: <a href="{htmllib.escape(p["url"], True)}" rel="nofollow noopener">bisduckopath.blogspot.com</a>.</p>'
    L = p["labels"]
    tags = [t for t, c in (("vh", "Game Java Việt Hoá" in L or "việt hoá" in title.lower() or "việt hóa" in title.lower()),
                           ("mod", "Game Java Mod" in L or "Game Mod" in L or title.lower().startswith("[mod]")),
                           ("goc", False)) if c] or ["goc"]
    meta = {"type": kind}
    desc = desc_of(lines)
    if kind in ("game", "app"):
        cat = genre_cat(p, lines)
        reses = [v["res"] for v in vs if v["res"] != "Chung"]
        reses = list(dict.fromkeys(reses))[:6]
        plat = "j2me" if any(v["plat"] != "s60" for v in vs) else "s60v3,s60v5"
        labels = ["App" if kind == "app" else "Game", cat] + (["VH"] if "vh" in tags else []) + (["Port"] if port else []) + reses
        meta.update(ver=ver, size=str(min(v["kb"] for v in vs)), cat=cat, tags=",".join(tags), plat=plat, res=", ".join(reses), desc=desc)
        meta.update({f"v{i}": f'{v["res"]}|{v["kb"]}|JAR={API}/v1/p/{v["alias"]}/{safe_name(title, v["res"], v["plat"], v["kind"])}' for i, v in enumerate(vs, 1)})
    elif kind == "media":
        cat = "Theme Symbian & Nokia"
        labels = ["Giao diện", cat]
        meta.update(cat=cat, desc=desc)
        meta.update({f"v{i}": f"Chung|{max(1, f['size'] // 1024)}|Tải={n_u}" for i, f in enumerate(p["files"][:40], 1)
                     for n_u in [f"https://www.mediafire.com/file/{f['qk']}"]})
    else:
        cat = "Thủ thuật & mẹo"
        labels = ["Bài viết", cat]
        meta.update(cat=cat, desc=desc)
    if port:
        meta["port"] = "1"
    meta["sk"] = f"bdk-{p['id']}"
    if hero:
        meta["img"] = hero[1]
    post = {"title": ("[Port] " if port and not title.lower().startswith("[port]") else "") + title, "html": body, "labels": labels, "meta": meta,
            "published": p["published"], "description": desc[:150]}
    return post, ""


def cmd_build(a):
    os.makedirs(a.out, exist_ok=True)
    posts, aliases, skipped, rep = [], {}, collections.defaultdict(list), collections.Counter()
    used = set()
    allp = [p for p in all_posts(a.data)]
    for p in sorted(allp, key=lambda p: p["published"]):
        if p.get("gone") and not a.keep_gone:
            rep["go khoi nguon"] += 1
            continue
        if not p["kind"]:
            skipped[p["skip"]].append(p["title"])
            continue
        post, why = build_post(p, used)
        if not post:
            skipped[why].append(p["title"])
            continue
        posts.append(post)
        rep[f"{p['kind']}{' (Port)' if p.get('port') else ''}"] += 1
    # alias: tinh lai variants_of voi cung post_res nhu build_post de khoa khop link trong bai
    for p in allp:
        if p["kind"] in ("game", "app") and not p.get("gone"):
            post_res = sorted({f"{x}x{y}" for x, y in RES.findall(field_text(clean_lines(scan(p["html"]).lines), "Màn Hình"))}, key=lambda r: (PRIORITY.index(r) if r in PRIORITY else 99, r))
            for v in variants_of(p, post_res):
                aliases[v["alias"]] = {"pd": v["pd"], "name": v["pd_name"], "post": p["id"], "kb": v["kb"], "res": v["res"], "ver": v["created"]}
    json.dump(posts, open(os.path.join(a.out, "posts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(aliases, open(os.path.join(a.out, "bdk-aliases.json"), "w", encoding="utf-8"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    json.dump({k: v for k, v in skipped.items()}, open(os.path.join(a.out, "skipped.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"build: {len(posts)} bai, {len(aliases)} khoa tai, bo {sum(len(v) for v in skipped.values())}; {dict(rep)}")
    return 0


def cmd_report(a):
    """Bao cao: bai moi / ban va trong N ngay gan nhat, tep loi, game chua co JAR, game chua co anh, so Port."""
    cut = datetime.fromtimestamp(time.time() - a.days * 86400, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    allp = [p for p in all_posts(a.data) if not p.get("gone")]
    new, patch, err, nojar, noimg = [], [], [], [], []
    kinds = collections.Counter()
    for p in allp:
        if not p["kind"]:
            continue
        kinds[f"{p['kind']}{' Port' if p.get('port') else ''}"] += 1
        for h in p["history"]:
            if h["at"] >= cut:
                (new if h["ev"] == "moi" else patch if h["ev"] != "go khoi feed" else []).append((p["title"], h))
        if p["kind"] in ("game", "app"):
            for f in p["files"]:
                if f.get("status") == "error":
                    err.append(f"{p['title']}: {f['fn']} ({f.get('error', '')})")
            if not any(j.get("pd_id") for f in p["files"] for j in f.get("jars", [])) and all(f.get("status") != "pending" for f in p["files"]):
                nojar.append(p["title"])
            if "<img" not in p["html"]:
                noimg.append(p["title"])
    L = [f"# bisduckopath: bao cao {now_iso()}", "", "Tong: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())), ""]
    L += [f"## Bai moi ({a.days} ngay): {len(new)}"] + [f"- {t}" for t, _ in new[:50]]
    L += ["", f"## Ban va / tep doi ({a.days} ngay): {len(patch)}"] + [f"- {t}: {h['ev']} {h.get('file', '')} {h.get('created', '')}" for t, h in patch[:50]]
    L += ["", f"## Tep tai loi: {len(err)}"] + [f"- {x}" for x in err[:40]]
    L += ["", f"## Game/app chua co JAR hop le (khong dang): {len(nojar)}"] + [f"- {x}" for x in nojar[:60]]
    L += ["", f"## Game/app khong co anh trong bai: {len(noimg)}"] + [f"- {x}" for x in noimg[:60]]
    txt = "\n".join(L) + "\n"
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        open(os.path.join(a.out, "REPORT.md"), "w", encoding="utf-8").write(txt)
    print(txt)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sync", "resolve", "fetch", "build", "report"])
    ap.add_argument("--days", type=float, default=2)
    ap.add_argument("--data", required=True, help="thu muc data/bisducko trong repo du lieu")
    ap.add_argument("--since", default="", help="sync: chi bai sua tu moc ISO nay")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--recheck", type=float, default=0, help="resolve: kiem lai tep cua bai chua kiem qua N ngay")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--budget-s", type=int, default=0)
    ap.add_argument("--index", default="")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--retry", action="store_true", help="fetch: thu lai tep loi")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1, help="chia theo so thu tu bai (n %% nshards == shard) de chay song song")
    ap.add_argument("--out", default="")
    ap.add_argument("--keep-gone", action="store_true")
    a = ap.parse_args(argv)
    return {"sync": lambda: cmd_sync(a), "resolve": lambda: cmd_resolve(a), "fetch": lambda: cmd_fetch(a), "build": lambda: cmd_build(a), "report": lambda: cmd_report(a)}[a.cmd]() or 0


if __name__ == "__main__":
    sys.exit(main())
