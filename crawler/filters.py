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
