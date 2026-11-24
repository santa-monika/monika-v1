"""Go muc nhung cua WapTai khoi file JAR: MIDlet phu "WapTai.COM" (mo https://waptai.com qua platformRequest),
class WapTai/COM/WapTai, icon WapTai/icon2.png va cac dong waptai trong MANIFEST.MF.
Chi sua MANIFEST va xoa muc zip; moi muc con lai giu nguyen byte (khong dung toi class cua game)."""
import argparse, io, os, re, struct, sys, zipfile, zlib

MANIFEST = "META-INF/MANIFEST.MF"
INJECT_PREFIX = "WapTai/"
INJECT_CLASS = "WapTai.COM.WapTai"
WAP = re.compile(r"wap\s*tai(\.com)?", re.I)
# Thuoc tinh co the xoa han khi chi chua waptai; thuoc tinh bat buoc thi thay bang gia tri trung tinh.
DROP_IF_WAPTAI = {"MIDlet-Info-URL", "MIDlet-Delete-Confirm", "MIDlet-Description", "MIDlet-Install-Notify",
                  "MIDlet-Delete-Notify"}
REQUIRED_NEUTRAL = {"MIDlet-Vendor": "Unknown"}


def parse_manifest(raw):
    """-> (main_header_lines, [section_lines...]); moi dong la (key, value). Noi dong gap (bat dau bang khoang trang)."""
    text = raw.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n")
    logical = []
    for line in text.split("\n"):
        if line.startswith(" ") and logical:
            logical[-1] += line[1:]
        else:
            logical.append(line)
    sections, cur = [], []
    for line in logical:
        if line == "":
            if cur:
                sections.append(cur)
                cur = []
            continue
        k, sep, v = line.partition(":")
        cur.append((k.strip(), v.strip() if sep else ""))
    if cur:
        sections.append(cur)
    return sections


def fold(line):
    """Gap dong dai hon 72 byte nhu dac ta JAR."""
    b = line.encode("utf-8")
    if len(b) <= 72:
        return line + "\r\n"
    out, first = [], True
    while b:
        n = 72 if first else 71
        # khong cat giua ky tu UTF-8
        while n < len(b) and (b[n] & 0xC0) == 0x80:
            n -= 1
        out.append(("" if first else " ") + b[:n].decode("utf-8"))
        b = b[n:]
        first = False
    return "\r\n".join(out) + "\r\n"


def midlet_index(key):
    m = re.fullmatch(r"MIDlet-(\d+)", key)
    return int(m.group(1)) if m else None


def is_injected_midlet(value):
    """MIDlet phu cua waptai: ten chi gom 'WapTai(.COM)', hoac class WapTai.COM.WapTai, hoac icon trong thu muc WapTai/.
    Khong dung quy tac 'ten co waptai' vi co game dat ten 'CS 3D WapTai.COM' (MIDlet that)."""
    parts = [p.strip() for p in value.split(",")]
    name = parts[0] if parts else ""
    cls = parts[2] if len(parts) > 2 else ""
    icon = parts[1].replace("\\", "/").lstrip("/") if len(parts) > 1 else ""
    return bool(re.fullmatch(r"wap\s*tai(\.com)?", name, re.I)) or cls == INJECT_CLASS or icon.startswith(INJECT_PREFIX)


def clean_manifest(raw):
    """-> (manifest_moi_bytes, nhat_ky, midlet_bi_xoa[(class, icon)]). Khong doi gi neu khong co dau vet waptai."""
    sections = parse_manifest(raw)
    log, removed = [], []
    if not sections:
        return raw, log, removed
    main = sections[0]
    midlets, others = [], []
    for k, v in main:
        i = midlet_index(k)
        if i is None:
            others.append((k, v))
        else:
            midlets.append((i, v))
    midlets.sort()
    kept = []
    for i, v in midlets:
        if is_injected_midlet(v):
            log.append(f"xoa MIDlet-{i}: {v}")
            parts = [x.strip() for x in v.split(",")]
            removed.append((parts[2] if len(parts) > 2 else "", parts[1] if len(parts) > 1 else ""))
        else:
            kept.append(v)
    new_others = []
    for k, v in others:
        if WAP.search(v):
            if k in DROP_IF_WAPTAI:
                log.append(f"xoa {k}: {v}")
                continue
            if k in REQUIRED_NEUTRAL:
                log.append(f"doi {k}: {v} -> {REQUIRED_NEUTRAL[k]}")
                v = REQUIRED_NEUTRAL[k]
            elif k in ("MIDlet-Name", "Name"):
                nv = re.sub(r"\s*[-–_]?\s*" + WAP.pattern, "", v, flags=re.I).strip() or v
                log.append(f"doi {k}: {v} -> {nv}")
                v = nv
            else:
                log.append(f"CON dau vet {k}: {v}")
        new_others.append((k, v))
    new_kept = []
    for v in kept:
        if WAP.search(v.split(",")[0]):
            nv = re.sub(r"\s*[-–_]?\s*" + WAP.pattern, "", v.split(",")[0], flags=re.I).strip()
            if nv:
                log.append(f"doi ten MIDlet: {v.split(',')[0]} -> {nv}")
                v = ",".join([nv] + v.split(",")[1:])
        new_kept.append(v)
    if not log:
        return raw, log, removed
    out = []
    for k, v in new_others:
        out.append(fold(f"{k}: {v}"))
    for n, v in enumerate(new_kept, 1):
        out.append(fold(f"MIDlet-{n}: {v}"))
    out.append("\r\n")
    for sec in sections[1:]:
        out.extend(fold(f"{k}: {v}") for k, v in sec)
        out.append("\r\n")
    return "".join(out).encode("utf-8"), log, removed


def _raw_compressed(data, info):
    off = info.header_offset
    n, e = struct.unpack_from("<HH", data, off + 26)
    start = off + 30 + n + e
    return data[start:start + info.compress_size]


def _dos(dt):
    y, mo, d, h, mi, s = dt
    return ((h << 11) | (mi << 5) | (s // 2)), (((max(y, 1980) - 1980) << 9) | (mo << 5) | d)


def build_zip(items):
    """items: list dict(name, method, crc, csize, usize, date_time, comp, ext_attr). Sao nguyen byte da nen, khong nen lai."""
    out, cds = io.BytesIO(), []
    for it in items:
        name = it["name"].encode("utf-8")
        flag = 0x800 if any(c > 127 for c in name) else 0
        dtime, ddate = _dos(it["date_time"])
        off = out.tell()
        out.write(struct.pack("<4s5H3L2H", b"PK\x03\x04", 20, flag, it["method"], dtime, ddate, it["crc"], it["csize"], it["usize"], len(name), 0))
        out.write(name)
        out.write(it["comp"])
        cds.append((it, name, flag, dtime, ddate, off))
    start = out.tell()
    for it, name, flag, dtime, ddate, off in cds:
        out.write(struct.pack("<4s6H3L5H2L", b"PK\x01\x02", 20, 20, flag, it["method"], dtime, ddate, it["crc"], it["csize"],
                              it["usize"], len(name), 0, 0, 0, 0, it["ext_attr"], off))
        out.write(name)
    size = out.tell() - start
    out.write(struct.pack("<4s4H2LH", b"PK\x05\x06", 0, 0, len(cds), len(cds), size, start, 0))
    return out.getvalue()


def _deflate(raw):
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    return c.compress(raw) + c.flush()


def _referenced_icons(manifest_bytes):
    icons = set()
    for sec in parse_manifest(manifest_bytes)[:1]:
        for k, v in sec:
            if midlet_index(k) is not None:
                parts = [x.strip() for x in v.split(",")]
                if len(parts) > 1 and parts[1]:
                    icons.add(parts[1].lstrip("/"))
            elif k == "MIDlet-Icon" and v:
                icons.add(v.lstrip("/"))
    return icons


def clean_jar(data):
    """-> (jar_moi_bytes, nhat_ky, canh_bao). Neu khong co gi de go: tra data nguyen ban."""
    zin = zipfile.ZipFile(io.BytesIO(data))
    names = zin.namelist()
    log, warn = [], []
    drop = {n for n in names if n.startswith(INJECT_PREFIX)}
    if any(n.upper().startswith("META-INF/") and n.upper().endswith((".SF", ".RSA", ".DSA")) for n in names):
        warn.append("JAR co chu ky so, bo qua")
        return data, log, warn
    new_man = None
    if MANIFEST in names:
        raw = zin.read(MANIFEST)
        new_man, mlog, removed = clean_manifest(raw)
        log += mlog
        if new_man == raw:
            new_man = None
        else:
            icons_left = _referenced_icons(new_man)
            for cls, icon in removed:
                path = cls.replace(".", "/") + ".class" if cls else ""
                if path in names:
                    body = zin.read(path)
                    # chi xoa class nho co nhac waptai (hoac dung ten class da biet): khong bao gio xoa class that cua game
                    if cls == INJECT_CLASS or (len(body) < 8192 and re.search(rb"wap\s*tai", body, re.I)):
                        drop.add(path)
                        drop.update(n for n in names if n.startswith(path[:-6] + "$"))
                    else:
                        warn.append(f"giu class {cls}: khong nho/khong chua waptai")
                ic = icon.lstrip("/")
                if ic in names and ic not in icons_left:
                    drop.add(ic)
    if not drop and new_man is None:
        return data, log, warn
    log += [f"xoa muc zip {n}" for n in sorted(drop) if not n.endswith("/")]
    items = []
    for info in zin.infolist():
        if info.filename in drop:
            continue
        if info.filename == MANIFEST and new_man is not None:
            comp = _deflate(new_man)
            items.append(dict(name=info.filename, method=8, crc=zlib.crc32(new_man), csize=len(comp), usize=len(new_man),
                              date_time=info.date_time, comp=comp, ext_attr=info.external_attr))
        else:
            items.append(dict(name=info.filename, method=info.compress_type, crc=info.CRC, csize=info.compress_size,
                              usize=info.file_size, date_time=info.date_time, comp=_raw_compressed(data, info),
                              ext_attr=info.external_attr))
    result = build_zip(items)
    warn += verify(result)
    return result, log, warn


def verify(data):
    """Kiem tra sau khi sua: zip doc duoc, moi MIDlet-N co class trong zip, khong con dau vet waptai o manifest/ten muc."""
    w = []
    z = zipfile.ZipFile(io.BytesIO(data))
    if z.testzip():
        w.append("zip loi CRC")
    names = set(z.namelist())
    if MANIFEST in names:
        for k, v in parse_manifest(z.read(MANIFEST))[0] if parse_manifest(z.read(MANIFEST)) else []:
            if midlet_index(k) is not None:
                parts = [p.strip() for p in v.split(",")]
                if len(parts) >= 3 and (parts[2].replace(".", "/") + ".class") not in names:
                    w.append(f"{k}: khong thay class {parts[2]}")
                if len(parts) >= 2 and parts[1] and parts[1].lstrip("/") not in {n.lstrip("/") for n in names}:
                    w.append(f"{k}: khong thay icon {parts[1]}")
            if WAP.search(v):
                w.append(f"con waptai trong manifest: {k}")
    if any(WAP.search(n) for n in names):
        w.append("con muc zip co ten waptai")
    return w


def waptai_strings_inside(data):
    """Thong ke muc con nhac waptai (credit Viet hoa nam trong class/resource cua game, khong sua tu dong)."""
    z = zipfile.ZipFile(io.BytesIO(data))
    hits = []
    for n in z.namelist():
        if n.endswith("/") or n == MANIFEST:
            continue
        if re.search(rb"wap\s*tai", z.read(n), re.I):
            hits.append(n)
    return hits


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst", help="file ket qua hoac thu muc")
    a = ap.parse_args(argv)
    data = open(a.src, "rb").read()
    new, log, warn = clean_jar(data)
    dst = os.path.join(a.dst, os.path.basename(a.src)) if os.path.isdir(a.dst) else a.dst
    open(dst, "wb").write(new)
    for l in log:
        print("  -", l)
    for w in warn:
        print("  !", w)
    print(f"{a.src}: {len(data)} -> {len(new)} byte, con {len(waptai_strings_inside(new))} muc nhac waptai trong game")
    return 0


if __name__ == "__main__":
    sys.exit(main())
