"""Sinh posts.json (dau vao cua tools/blogger-import.mjs) cho cac nguon nhieu JAR: gom cac ban cung game thanh 1 bai, bang link tai theo do phan giai.
Mo ta trung thuc, dung mau (khong bia noi dung game): ten, ban Viet hoa neu co, cac do phan giai va dung luong. The loai doan theo tu khoa trong ten (co the sai).
Danh muc theo taxonomy v3 cua monika-java. Link tai: http://api.justmonika.top/v1/p/<ID>/<ten>.jar (Worker can duoc deploy truoc)."""
import argparse, collections, html, json, os, re, sys
from datetime import datetime, timedelta, timezone
from .normalize import strip_accents

API = "http://api.justmonika.top"
RES_PRIORITY = ["240x320", "320x240", "240x400", "176x220", "176x208", "208x208", "128x160", "128x128", "360x640", "320x480", "480x800"]
SRC_NAME = {"qnw": "quangninhwap.com", "gt321": "giaitri321.pro (kho lưu trữ)", "wvip": "wapvip.pro (kho lưu trữ)"}
GAME_RULES = [
    ("Đối kháng", r"fight|boxing|wwe|ufc|tekken|mortal|kombat|street\s*fighter|kungfu|kung\s*fu|doi\s*khang|wrestl"),
    ("Đua xe", r"race|racing|rally|moto|speed|drift|asphalt|dua\s*xe|kart|nitro|\bcars?\b|truck|bike|gt\s*racing|f1\b|driver|parking"),
    ("Thể thao", r"football|soccer|fifa|pes\b|golf|tennis|basket|nba|bong\s*da|cricket|olympic|billiard|bida|ski|surf|hockey|rugby|baseball|bowling|fishing|cau\s*ca"),
    ("Bắn súng", r"shoot|\bgun|sniper|commando|counter|ban\s*sung|rambo|contra|duty|combat|hunter|hunting|swat|terror|soldier|sas\b|\bwar\b|army|strike|special\s*force|specnaz"),
    ("Kiếm hiệp & võ hiệp", r"kiem|hiep|vo\s*lam|tam\s*quoc|truyen\s*ky|thuc\s*son|tien\s*(kiem|hiep)|phong\s*than|dau\s*pha|tri\s*tham|tay\s*du|thuy\s*hu|vong\s*linh|long\s*tranh|thieu\s*lam|tieu\s*ngao|thien\s*long|cuu\s*am|dai\s*chien|chinh\s*phuc|anh\s*hung|trieu\s*van|quan\s*vu|lien\s*quan|dao\s*kiem|bao\s*kiem|vo\s*su|samurai"),
    ("Thủ thành", r"tower|defen[cs]e|plants?\s*vs|zombies?|thu\s*thanh|castle|phong\s*thu"),
    ("Chiến thuật", r"strateg|chien\s*thuat|empire|age\s*of|civiliz|command\s*&|warlord|general|total\s*war|conquer|clash"),
    ("Nhập vai", r"\brpg\b|heroes|lore|final\s*fantasy|fantasy|quest|legend|dragon|diablo|knight|nhap\s*vai|ma\s*dao|chronicle|saga|kingdom|hero\b|rong\b"),
    ("Giải đố & trí tuệ", r"puzzle|bubble|tetris|xep\s*(hinh|gach)|bejeweled|diamond|match|sudoku|brain|quiz|trieu\s*phu|pikachu|lines?\b|jewel|bloxx|word|crossword|domino|gem|memory|mine\s*sweep|dao\s*vang|nối|noi\s*hinh"),
    ("Cờ & bài", r"co\s*tuong|chess|co\s*vua|co\s*ca\s*ngua|co\s*caro|caro|checkers|backgammon|reversi|othello|solitaire"),
    ("Sinh tồn & kinh dị", r"horror|silent\s*hill|resident\s*evil|dead|ghost|kinh\s*di|surviv|haunt|vampire|alien|predator|zombie|terror|evil"),
    ("Mô phỏng & quản lý", r"\bsim\b|sims|tycoon|farm|manager|restaurant|hotel|nong\s*trai|quan\s*ly|city|pet\b|cooking|shop|theme\s*park|dream\s*house"),
    ("Trẻ em & vui nhộn", r"kids?|tom\b|jerry|doremon|doraemon|dora\b|panda|baby|cute|cartoon|sponge|mickey|bear|penguin|smurf|ben\s*10|pokemon|chu\s*be"),
    ("Arcade & chạy nhảy", r"mario|sonic|\brun\b|runner|jump|ninja|rayman|dash|pac|crash|temple|platform|boy\b|bros|bomberman|worms|arcade|angry|bird|fruit|cat\b"),
    ("Phiêu lưu", r"adventure|prince|persia|tomb\s*raider|indiana|lara|assassin|lost|island|treasure|explor|jungle|jones|phieu\s*luu|pirate|spider|batman|superman|iron\s*man|hulk|avatar|transformers"),
]
APP_RULES = [
    ("Mạng & trình duyệt", r"opera|browser|ucweb|\buc\b|web|mini|wap|internet|3g|gprs|download"),
    ("Chat & mạng xã hội", r"chat|yahoo|facebook|zalo|skype|messenger|nimbuzz|ebuddy|palringo|\bym\b|sms"),
    ("Bản đồ & GPS", r"\bmaps?\b|gps|ban\s*do|vimap|navi|route|bus"),
    ("Trình phát nhạc & video", r"mp3|music|player|nhac|video|media|radio|vplayer|zing|tv\b|karaoke"),
    ("Ảnh & camera", r"camera|photo|anh\b|picture|image|paint|draw"),
    ("Tùy biến máy", r"font|launcher|theme|wallpaper|skin|ringtone|desktop"),
    ("Đọc sách & truyện", r"reader|book|ebook|doc\s*sach|truyen|ebook|bible"),
    ("Giả lập & chạy game", r"emulator|jbed|jbed|ngage|gia\s*lap|\bjava\b|j2me|midlet"),
    ("Văn phòng & học tập", r"hoc|dict|tu\s*dien|office|calc|word|excel|pdf|lich|hoc\s*tap|tieng\s*anh|english"),
    ("Công cụ hệ thống", r"manager|tool|system|file|task|memory|battery|pin|virus|antivirus|speed|zip|rar|backup|clean|boost"),
]


def cat_of(title, kind, default=None):
    t = strip_accents(title).lower()
    for name, pat in (APP_RULES if kind == "app" else GAME_RULES):
        if re.search(pat, t):
            return name
    return default or ("Khác" if kind == "app" else "Hành động")


def valid_cats(kind):
    return {n for n, _ in (APP_RULES if kind == "app" else GAME_RULES)} | {"Khác"}


def load_overrides(files):
    """Ket qua lam sach ten/the loai (moi dong: src, group, title, cat, skip) -> {(src, group): dong}."""
    ov = {}
    for f in files:
        for w in json.load(open(f, encoding="utf-8")):
            ov[(w["src"], w["group"])] = w
    return ov


def res_key(r):
    return (RES_PRIORITY.index(r) if r in RES_PRIORITY else 99, r or "~")


def best_title(rows):
    c = collections.Counter(r["title"] for r in rows)
    return max(c, key=lambda t: (c[t], len(t)))


def build_games(inv, state, index_by_id, src, start, limit=0, overrides=None):
    overrides = overrides or {}
    stmap = {r["url"]: r for r in state if r.get("ok") and r.get("pixeldrain_id")}
    groups = collections.OrderedDict()
    for it in inv:
        st = stmap.get(it["url"])
        if st:
            groups.setdefault(it["group"], []).append((it, st))
    posts = []
    n = 0
    for g, rows in groups.items():
        if all(st.get("dup") for _, st in rows):
            continue  # moi tep deu trung tep da co tren kho (vd. da len tu waptai): game nay da co bai, khong dang lai
        items = [r[0] for r in rows]
        ov = overrides.get((src, g), {})
        if ov.get("skip"):
            continue  # cờ bạc / 18+ / game online được phát hiện ở bước làm sạch tên
        title = best_title(items)
        kind = items[0]["kind"]
        vh = any(i["vh"] for i in items)
        t_vi = (ov.get("title") or "").strip()
        if t_vi and 2 <= len(t_vi) <= 80:
            title = t_vi
        oc = ov.get("cat")
        cat = oc if oc in valid_cats(kind) and oc != "Khác" else cat_of(title, kind, default="Khác")
        seen, variants = set(), []
        for it, st in rows:
            name = st.get("pd_name") or index_by_id.get(st["pixeldrain_id"], {}).get("name") or os.path.basename(it["file"])
            key = (it["res"], st["sha256"])
            if key in seen:
                continue
            seen.add(key)
            variants.append({"res": it["res"] or "Chung", "kb": max(1, round(st["bytes"] / 1024)), "plat": it["plat"],
                             "url": f"{API}/v1/p/{st['pixeldrain_id']}/{re.sub(r'[^A-Za-z0-9._-]', '_', name)}"})
        variants.sort(key=lambda v: (res_key(v["res"]), v["kb"]))
        variants = variants[:40]
        reses = []
        for v in variants:
            if v["res"] != "Chung" and v["res"] not in reses:
                reses.append(v["res"])
        what = "ứng dụng" if kind == "app" else "game"
        desc = (f"{title} là {what} cho điện thoại Java (J2ME){' bản Việt hóa' if vh else ''}. "
                f"Có {len(variants)} bản tải{', theo độ phân giải ' + ', '.join(reses[:5]) if reses else ''}. "
                "Chọn đúng bản cho màn hình máy của bạn trong bảng dưới.")
        rows_html = "\n".join(f"<tr><td>{html.escape(v['res'])}</td><td>{v['kb']} KB</td><td><a href=\"{v['url']}\">Tải JAR</a></td></tr>" for v in variants)
        body = (f"<p>{html.escape(desc)}</p>\n<h3>Tải về theo độ phân giải</h3>\n"
                "<p>Chọn dòng đúng độ phân giải màn hình máy bạn. Máy Nokia S60 nên ưu tiên bản có chữ S60 trong tên tệp.</p>\n"
                '<table border="1" cellpadding="4" cellspacing="0" width="100%">\n<tr><th>Màn hình</th><th>Dung lượng</th><th>Tải</th></tr>\n'
                f"{rows_html}\n</table>\n<p>Tệp lấy từ {html.escape(SRC_NAME[src])}{'; đã gỡ phần quảng cáo nhúng trong MANIFEST' if any(st.get('cleaned') for _, st in rows) else ''}.</p>")
        meta = {"type": "app" if kind == "app" else "game", "size": str(min(v["kb"] for v in variants)), "cat": cat,
                "tags": "vh" if vh else "goc", "plat": "j2me", "res": ", ".join(reses[:6]), "desc": desc}
        meta.update({f"v{i}": f"{v['res']}|{v['kb']}|JAR={v['url']}" for i, v in enumerate(variants, 1)})
        labels = ["App" if kind == "app" else "Game", cat] + (["VH"] if vh else [])
        posts.append({"title": title + (" Việt hóa" if vh and "viet" not in strip_accents(title).lower() else ""), "html": body, "labels": labels, "meta": meta,
                      "published": (start - timedelta(minutes=n)).strftime("%Y-%m-%dT%H:%M:%SZ"), "description": desc[:150]})
        n += 1
        if limit and n >= limit:
            break
    return posts


def build_text(items, written, start, offset=0):
    posts = []
    for n, it in enumerate(items):
        w = written.get(it["id"])
        if not w or w.get("skip") or not w.get("body"):
            continue
        paras = "".join(f"<p>{html.escape(p.strip())}</p>\n" for p in w["body"].split("\n\n") if p.strip())
        body = paras + f'<p>Nguồn tham khảo: <a href="{html.escape(it["url"])}">quangninhwap.com</a> (tóm tắt bằng lời của Monika).</p>'
        post_type = "post"
        posts.append({"title": w.get("title") or it["title"], "html": body, "labels": ["Bài viết", it["cat"]],
                      "meta": {"type": post_type, "cat": it["cat"], "desc": w["desc"][:150]},
                      "published": (start - timedelta(minutes=offset + n)).strftime("%Y-%m-%dT%H:%M:%SZ"), "description": w["desc"][:150]})
    return posts


def unique_titles(posts):
    """Blogger dung tieu de lam duong dan: tieu de trung (cung thang) se bi tool nhap tu choi, them so thu tu."""
    seen = collections.Counter()
    for p in posts:
        key = strip_accents(p["title"]).lower()
        seen[key] += 1
        if seen[key] > 1:
            p["title"] = f"{p['title']} ({seen[key]})"
    return posts


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--inv", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--index", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--text-items", default="")
    ap.add_argument("--text-out", nargs="*", default=[])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--overrides", nargs="*", default=[], help="file json lam sach ten/the loai (haiku2/out-N.json)")
    a = ap.parse_args(argv)
    inv = [json.loads(l) for l in open(a.inv, encoding="utf-8")]
    state = [json.loads(l) for l in open(a.state, encoding="utf-8")]
    index = {f["id"]: f for f in json.load(open(a.index, encoding="utf-8"))}
    start = datetime.now(timezone.utc).replace(microsecond=0)
    posts = build_games(inv, state, index, a.src, start, a.limit, load_overrides(a.overrides))
    if a.text_items:
        written = {}
        for f in a.text_out:
            for w in json.load(open(f, encoding="utf-8")):
                written[w["id"]] = w
        posts += build_text(json.load(open(a.text_items, encoding="utf-8")), written, start, len(posts))
    posts = unique_titles(posts)
    json.dump(posts, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(posts)} bai -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
