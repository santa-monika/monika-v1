import io, unittest, zipfile
from crawler import jarclean, waptai
from crawler.filters import classify_vi


def make_jar(manifest, extra):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("META-INF/MANIFEST.MF", manifest)
        for n, d in extra.items():
            z.writestr(n, d)
    return b.getvalue()


INJ_CLASS = b"\xca\xfe\xba\xbe....https://waptai.com....platformRequest"


class JarCleanTest(unittest.TestCase):
    def test_goc_midlet_phu_chuan(self):
        man = ("Manifest-Version: 1.0\r\nMIDlet-Vendor: WapTai.COM\r\nMIDlet-Info-URL: http://waptai.com\r\n"
               "MIDlet-Name: FIFA\r\nMIDlet-1: FIFA, /icon.png, com.ea.Main\r\n"
               "MIDlet-2: WapTai.COM, WapTai/icon2.png, WapTai.COM.WapTai\r\n\r\n")
        jar = make_jar(man, {"com/ea/Main.class": b"GAME" * 500, "icon.png": b"png", "WapTai/icon2.png": b"x",
                             "WapTai/COM/WapTai.class": INJ_CLASS})
        out, log, warn = jarclean.clean_jar(jar)
        z = zipfile.ZipFile(io.BytesIO(out))
        self.assertEqual(warn, [])
        self.assertFalse([n for n in z.namelist() if "WapTai" in n])
        m = z.read("META-INF/MANIFEST.MF").decode()
        self.assertNotIn("waptai", m.lower())
        self.assertIn("MIDlet-1: FIFA, /icon.png, com.ea.Main", m)
        self.assertNotIn("MIDlet-2", m)
        self.assertEqual(z.read("com/ea/Main.class"), b"GAME" * 500)
        self.assertIsNone(z.testzip())

    def test_bien_the_mobileads_giu_class_game(self):
        man = ("Manifest-Version: 1.0\r\nMIDlet-Name: Tam Quoc\r\nMIDlet-1: Tam Quoc, /icon.png, main.cMIDlet\r\n"
               "MIDlet-2: WapTai.COM, icon2.png, MobileAds\r\n\r\n")
        jar = make_jar(man, {"main/cMIDlet.class": b"G" * 900, "icon.png": b"a", "icon2.png": b"b", "MobileAds.class": INJ_CLASS})
        out, log, warn = jarclean.clean_jar(jar)
        names = zipfile.ZipFile(io.BytesIO(out)).namelist()
        self.assertNotIn("MobileAds.class", names)
        self.assertNotIn("icon2.png", names)
        self.assertIn("main/cMIDlet.class", names)
        self.assertEqual(warn, [])

    def test_khong_xoa_class_that(self):
        # MIDlet phu tro vao class lon khong nhac waptai -> khong xoa, canh bao
        man = "Manifest-Version: 1.0\r\nMIDlet-1: G, /i.png, a.B\r\nMIDlet-2: WapTai.COM, WapTai/i2.png, a.Real\r\n\r\n"
        jar = make_jar(man, {"a/B.class": b"B", "a/Real.class": b"R" * 20000, "i.png": b"1", "WapTai/i2.png": b"2"})
        out, log, warn = jarclean.clean_jar(jar)
        self.assertIn("a/Real.class", zipfile.ZipFile(io.BytesIO(out)).namelist())
        self.assertTrue(any("giu class" in w for w in warn))

    def test_midlet_that_ten_waptai_duoc_giu(self):
        man = "Manifest-Version: 1.0\r\nMIDlet-Name: CS 3D WapTai.COM\r\nMIDlet-1: CS 3D WapTai.COM, /i.png, g.Main\r\nMIDlet-2: WapTai.COM, WapTai/icon2.png, WapTai.COM.WapTai\r\n\r\n"
        jar = make_jar(man, {"g/Main.class": b"M", "i.png": b"1", "WapTai/icon2.png": b"2", "WapTai/COM/WapTai.class": INJ_CLASS})
        out, _, warn = jarclean.clean_jar(jar)
        m = zipfile.ZipFile(io.BytesIO(out)).read("META-INF/MANIFEST.MF").decode()
        self.assertIn("MIDlet-1: CS 3D, /i.png, g.Main", m)
        self.assertEqual(warn, [])

    def test_khong_doi_khi_sach(self):
        man = "Manifest-Version: 1.0\r\nMIDlet-Name: X\r\nMIDlet-1: X, /i.png, a.B\r\n\r\n"
        jar = make_jar(man, {"a/B.class": b"B", "i.png": b"1"})
        out, log, warn = jarclean.clean_jar(jar)
        self.assertIs(out, jar)

    def test_dong_manifest_dai_duoc_gap_va_doc_lai(self):
        long_v = "A" * 200
        man = f"Manifest-Version: 1.0\r\nMIDlet-Name: X\r\nLong-Key: {long_v}\r\nMIDlet-1: X, /i.png, a.B\r\nMIDlet-2: WapTai.COM, WapTai/icon2.png, WapTai.COM.WapTai\r\n\r\n"
        out, _, _ = jarclean.clean_jar(make_jar(man, {"a/B.class": b"B", "i.png": b"1", "WapTai/icon2.png": b"2"}))
        raw = zipfile.ZipFile(io.BytesIO(out)).read("META-INF/MANIFEST.MF")
        self.assertTrue(all(len(l) <= 72 for l in raw.split(b"\r\n")))
        self.assertIn(("Long-Key", long_v), jarclean.parse_manifest(raw)[0])

    def test_jar_co_chu_ky_bo_qua(self):
        man = "Manifest-Version: 1.0\r\nMIDlet-1: X, /i.png, a.B\r\nMIDlet-2: WapTai.COM, WapTai/icon2.png, WapTai.COM.WapTai\r\n\r\n"
        jar = make_jar(man, {"META-INF/CERT.SF": b"s", "a/B.class": b"B"})
        out, _, warn = jarclean.clean_jar(jar)
        self.assertIs(out, jar)
        self.assertTrue(warn)


class WaptaiParseTest(unittest.TestCase):
    def test_tai_ve_nhay_don_va_kich_thuoc(self):
        c = ("<div class=\"game\">Hỗ Trợ Máy Tương Tự:  Nokia 8208, E75&#8230;<br /><a href='https://up.waptai.com/download/game/x_240x320.jar' rel='nofollow'>Tải Game 240&#215;320</a>  (399.2 KB)</div>"
             "<div class=\"game\">y<br /><a href=\"https://up.waptai.com/download/game/x_Viet_Hoa_320x240.jar\">Tải 320x240</a> (1.5 MB)</div>")
        d = waptai.parse_downloads(c)
        self.assertEqual([x["resolution"] for x in d], ["240x320", "320x240"])
        self.assertEqual(d[0]["size_kb"], 399)
        self.assertEqual(d[1]["size_kb"], 1536)
        self.assertTrue(d[0]["own_host"])
        self.assertIn("Nokia 8208", d[0]["models"])
        self.assertEqual(d[1]["kind"], "viethoa")

    def test_loai_game_online_va_hack(self):
        self.assertEqual(waptai.online_filter([4], "Game X", "")[0], "loai")
        self.assertEqual(waptai.online_filter([6], "Tải Game MU Online", "")[0], "loai")
        self.assertEqual(waptai.online_filter([6], "Tải Game Foo Hack", "Game online can may chu")[0], "loai")
        self.assertEqual(waptai.online_filter([6], "Tải Game Foo Mod", "Choi mot minh")[0], "duyet")
        self.assertEqual(waptai.online_filter([6], "Tải Game Bình Thường", "")[0], "ok")

    def test_bo_loc_tieng_viet(self):
        self.assertEqual(classify_vi("Tải Game Hành Động", "Nhân vật đánh bại kẻ thù, tiến lên phía trước")[0], "ok")
        self.assertEqual(classify_vi("Tải Game Đánh Bài Tiến Lên", "")[0], "loai")
        self.assertEqual(classify_vi("Tải Game Đua Xe", "Có minigame blackjack")[0], "duyet")
        self.assertEqual(classify_vi("Tải Game Casino Royale", "")[0], "loai")

    def test_phan_loai_noi_dung(self):
        self.assertEqual(waptai.kind_of([12]), "truyen")
        self.assertEqual(waptai.kind_of([58]), "hinh_nen")
        self.assertEqual(waptai.kind_of([4, 144]), "game_online")
        self.assertEqual(waptai.kind_of([5, 144]), "game")


if __name__ == "__main__":
    unittest.main()
