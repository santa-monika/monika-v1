"""Loc noi dung nguoi lon / 18+ / co bac. Tra ve (trang_thai, ly_do): ok | loai | duyet."""
import re
from .normalize import strip_accents

HARD = [r"\bcasino\b", r"\broulette\b", r"\bblackjack\b", r"\bbaccarat\b", r"\bslots?\b", r"\bpoker\b",
        r"\bbetting\b", r"\bgambl", r"\blottery\b", r"\bjackpot\b", r"\bporn", r"\bxxx\b", r"\bsex\b", r"\bsexy\b",
        r"\berotic", r"\bstrip(per|tease|\s*poker)?\b", r"\bnude\b", r"\bnaked\b", r"\badult\b", r"\b18\s*\+",
        r"\bhentai\b", r"\bplayboy\b", r"\blingerie\b", r"\bbikini\b", r"\bhot\s+asian\b", r"\bgirls?\s+calendar\b",
        r"danh\s*bai", r"\bxoc\s*dia\b", r"\bto[iy]\s*bai\b", r"\bbigkool\b", r"\biwin\b", r"\bmaubinh\b", r"\bphom\b",
        r"\btien\s*len\b", r"\bsam\s*loc\b", r"\bsong\s*bai\b"]
SOFT = [r"\bgirl\b", r"\bbabe", r"\bkiss", r"\bdating\b", r"\bseduc", r"\bstrip\b", r"\bbar\b", r"\bbeer\b",
        r"\bvegas\b", r"\bcard\s*game\b", r"\bbingo\b", r"\bmahjong\b"]
VENDOR_BLOCK = {"playboy", "private media", "thumbplay adult"}


def classify(title="", description="", vendor=""):
    text = strip_accents(f"{title} {description}").lower()
    hard = [p for p in HARD if re.search(p, text)]
    if (vendor or "").lower() in VENDOR_BLOCK:
        hard.append("vendor")
    if hard:
        return "loai", hard
    soft = [p for p in SOFT if re.search(p, text)]
    return ("duyet", soft) if soft else ("ok", [])


# --- Bo loc cho bai tieng Viet (waptai): khong bo dau voi cum tu Viet de tranh "danh bai" = "danh bai(bai)" va "tien len" ---
VN_ASCII_PATTERNS = {r"danh\s*bai", r"\bxoc\s*dia\b", r"\bto[iy]\s*bai\b", r"\bphom\b", r"\btien\s*len\b",
                     r"\bsam\s*loc\b", r"\bsong\s*bai\b", r"\bmaubinh\b"}
HARD_EN = [p for p in HARD if p not in VN_ASCII_PATTERNS]
VN_HARD = [r"đánh\s*bài", r"đánh\s*bạc", r"cờ\s*bạc", r"cá\s*độ", r"xóc\s*đĩa", r"tá\s*lả", r"sâm\s*lốc", r"\bphỏm\b",
           r"tiến\s*lên\s*miền", r"mậu\s*binh", r"xập\s*xám", r"xì\s*dách", r"bài\s*cào", r"ba\s*cây", r"tài\s*xỉu",
           r"lô\s*đề", r"nhà\s*cái", r"khiêu\s*dâm", r"sex", r"người\s*lớn", r"18\s*\+"]


def classify_vi(title="", text="", vendor=""):
    """Tu khoa cam trong TIEU DE -> loai; chi o phan noi dung -> duyet (nguoi xem). Cum tu Viet khop co dau."""
    t_ascii = strip_accents(title or "").lower()
    b_ascii = strip_accents(text or "").lower()
    t_vi, b_vi = (title or "").lower(), (text or "").lower()
    in_title = [p for p in HARD_EN if re.search(p, t_ascii)] + [p for p in VN_HARD if re.search(p, t_vi)]
    if (vendor or "").lower() in VENDOR_BLOCK:
        in_title.append("vendor")
    if in_title:
        return "loai", in_title
    in_text = [p for p in HARD_EN if re.search(p, b_ascii)] + [p for p in VN_HARD if re.search(p, b_vi)]
    if in_text:
        return "duyet", in_text
    soft = [p for p in SOFT if re.search(p, t_ascii)]
    return ("duyet", soft) if soft else ("ok", [])
