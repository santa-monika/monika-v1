"""Doi chieu game nguon voi chi muc Pixeldrain (va sau nay voi cac site khac).
Quy tac: khop 'auto' chi khi ten chuan hoa giong het VA day so (so phan, nam) giong het.
Gan giong (ratio >= 0.8, cung day so) -> 'duyet' de nguoi xem. Khong bao gio tu gop o muc 'duyet'."""
import difflib, re
from .normalize import norm_title


def digits(s):
    return re.findall(r"\d+", s)


def core(title):
    """Bo phan phu de sau ':' hoac ' - ' de so khop ten ngan (Gangstar 3: Miami Vindication)."""
    return re.split(r"\s*[:\-–]\s+", title or "", maxsplit=1)[0]


def match(title, index):
    nt = norm_title(title)
    dt = digits(nt)
    auto = [f for f in index if f["norm_title"] == nt]
    if auto:
        return "auto", auto, 1.0
    cands = []
    for f in index:
        k = f["norm_title"]
        if digits(k) != dt and not (digits(norm_title(core(title))) == digits(k)):
            continue
        r = difflib.SequenceMatcher(None, nt, k).ratio()
        rc = difflib.SequenceMatcher(None, norm_title(core(title)), k).ratio()
        r = max(r, rc if rc == 1.0 else 0)
        if r >= 0.8:
            cands.append((r, f))
    if cands:
        best = max(c[0] for c in cands)
        return "duyet", [f for r, f in cands if r == best], best
    return "none", [], 0.0
