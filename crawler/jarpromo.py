"""Go quang cao nhung o muc MANIFEST cua JAR tu cac site wap (wapm4u, xtgem, wapvip, giaitri321...): MIDlet phu quang cao, Info-URL,
Delete-Confirm, Vendor. Khong dong den class cua game; chu 'Edit by ... wapm4u' nam trong class la credit nguoi viet hoa, de nguyen (da duoc sep duyet o waptai).
Ghi lai zip bang zipfile (giai nen roi nen lai tung muc, noi dung khong doi). Tra ve (bytes_moi, nhat_ky); khong co gi de sua thi tra nguyen ban."""
import io, re, zipfile

SITE = re.compile(r"(wapvip|giaitri321|quangninhwap|wapm4u|xtgem|waptai|wap\.sh|uiwap|dongthap|campha1|tntinhyeu|hoangxuanpro|meovathay|mtaiaz|\.mobi\b|wap\s*\w*\.(com|net|pro|vn|info))", re.I)
DROP_KEYS = {"MIDlet-Info-URL", "MIDlet-Delete-Confirm", "MIDlet-Description", "MIDlet-Install-Notify", "MIDlet-Delete-Notify"}
MF = "META-INF/MANIFEST.MF"


def _logical(raw):
    text = raw.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n")
    out = []
    for line in text.split("\n"):
        if line.startswith(" ") and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def _fold(line):
    b = line.encode("utf-8")
    if len(b) <= 72:
        return line + "\r\n"
    parts, first = [], True
    while b:
        n = 72 if first else 71
        while n < len(b) and (b[n] & 0xC0) == 0x80:
            n -= 1
        parts.append(("" if first else " ") + b[:n].decode("utf-8"))
        b, first = b[n:], False
    return "\r\n".join(parts) + "\r\n"


def clean_manifest(raw):
    lines = _logical(raw)
    # phan dau (header chinh) toi dong trong dau tien
    try:
        cut = lines.index("")
    except ValueError:
        cut = len(lines)
    head, tail = lines[:cut], lines[cut:]
    log, mid, other = [], [], []
    for ln in head:
        k, sep, v = ln.partition(":")
        k, v = k.strip(), v.strip()
        m = re.fullmatch(r"MIDlet-(\d+)", k)
        if m:
            mid.append((int(m.group(1)), v))
        else:
            other.append((k, v))
    keep_mid = []
    for i, v in sorted(mid):
        name = v.split(",")[0].strip()
        if i >= 2 and (SITE.search(v) or re.search(r"\.(com|net|mobi|pro|vn)\b", name, re.I)):
            log.append(f"xoa MIDlet-{i}: {v}")
        else:
            keep_mid.append(v)
    if not keep_mid and mid:
        return raw, []
    new_other = []
    for k, v in other:
        if SITE.search(v) and k in DROP_KEYS:
            log.append(f"xoa {k}: {v}")
            continue
        if SITE.search(v) and k == "MIDlet-Vendor":
            nv = " ".join(w for w in v.split() if not SITE.search(w)).strip(" -,;") or "Unknown"
            log.append(f"doi {k}: {v} -> {nv}")
            v = nv
        new_other.append((k, v))
    if not log:
        return raw, []
    out = [_fold(f"{k}: {v}") for k, v in new_other if k]
    out += [_fold(f"MIDlet-{n}: {v}") for n, v in enumerate(keep_mid, 1)]
    out.append("\r\n")
    out += [_fold(l) if l else "\r\n" for l in tail[1:] if l is not None]
    return "".join(out).encode("utf-8"), log


def clean_jar(raw):
    z = zipfile.ZipFile(io.BytesIO(raw))
    if MF not in z.namelist():
        return raw, []
    new_mf, log = clean_manifest(z.read(MF))
    if not log:
        return raw, []
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as out:
        for info in z.infolist():
            data = new_mf if info.filename == MF else z.read(info.filename)
            zi = zipfile.ZipInfo(info.filename, info.date_time)
            zi.compress_type = zipfile.ZIP_STORED if info.compress_type == zipfile.ZIP_STORED else zipfile.ZIP_DEFLATED
            zi.external_attr = info.external_attr
            out.writestr(zi, data)
    return b.getvalue(), log
