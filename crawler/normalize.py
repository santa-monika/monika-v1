"""Chuan hoa ten, do phan giai va loai ban (goc / viethoa / mod) de gop game giua cac site."""
import re, unicodedata

RES_RE = re.compile(r"(\d{3})\s*[xX]\s*(\d{3})")
# nhan bo khoi ten khi so khop
NOISE = r"(viet\s*hoa|vh|crack(ed)?|mod|hack(ed)?|full|free|unlock(ed)?|mien\s*phi|ban\s*quyen|s60|s40|jar|jad|sis|sisx|v\d+(\.\d+)*|\d+\.\d+(\.\d+)*)"


def strip_accents(s):
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def resolution(text):
    m = RES_RE.search(text or "")
    return f"{m.group(1)}x{m.group(2)}" if m else None


def norm_title(name):
    s = strip_accents(name or "").lower()
    s = re.sub(r"\.(jar|jad|sis|sisx)$", "", s)
    s = RES_RE.sub(" ", s)
    s = re.sub(r"[_\-.:,'’!?()\[\]&]+", " ", s)
    s = re.sub(rf"\b{NOISE}\b", " ", s)
    s = re.sub(r"\b(the|a|an)\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


def variant_kind(*texts):
    """goc | viethoa | mod, doan tu ten file/thu muc/tieu de."""
    s = strip_accents(" ".join(t or "" for t in texts)).lower()
    s = re.sub(r"[_\-.]+", " ", s)
    if re.search(r"viet\s*hoa|\bvh\b|tieng\s*viet", s):
        return "viethoa"
    if re.search(r"crack|\bmod\b|hack|unlock", s):
        return "mod"
    return "goc"
