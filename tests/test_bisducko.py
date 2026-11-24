import io, unittest, zipfile
from crawler import bisducko as b, mediafire as mf


def P(title, labels, html="<div>x</div>"):
    return {"id": "1", "url": "https://x/p", "title": title, "labels": labels, "published": "2026-01-01T00:00:00Z", "updated": "2026-01-01T00:00:00Z", "html": html}


def jar(name="Game", extra=None):
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        z.writestr("META-INF/MANIFEST.MF", f"MIDlet-1: {name}, /i.png, G\r\n")
        for k, v in (extra or {}).items():
            z.writestr(k, v)
    return bio.getvalue()


class T(unittest.TestCase):
    def test_links(self):
        self.assertEqual(mf.link_key("https://www.mediafire.com/file/93mktvzkkda48gr/Bomberman_%252708.zip/file"), ("file", "93mktvzkkda48gr"))
        self.assertEqual(mf.link_key("https://app.mediafire.com/folder/omxswxp7a9p6y?fbclid=x"), ("folder", "omxswxp7a9p6y"))
        self.assertEqual(mf.link_key("https://www.mediafire.com/folder/cvcjioe1j5b2m/Elven+Chronic"), ("folder", "cvcjioe1j5b2m"))
        self.assertIsNone(mf.link_key("https://drive.google.com/file/d/abc"))

    def test_classify(self):
        c = b.classify_post(P("[Phát Hành] Elven Chronicles Việt Hoá | Game Java J2ME", ["Game Java", "Game Java Việt Hoá"]))
        self.assertEqual((c["kind"], c["port"]), ("game", False))
        c = b.classify_post(P("[Port] Bomberman '08 | Game Java", ["Game Java", "Game Java Port"]))
        self.assertEqual((c["kind"], c["port"]), ("game", True))
        self.assertEqual(b.classify_post(P("Game Online X", ["Game Java", "Game Online"]))["kind"], None)
        self.assertEqual(b.classify_post(P("Tải Game Java Army 2 Offline", ["Game Java", "Game Online"]))["kind"], "game")
        self.assertEqual(b.classify_post(P("[Mod] Ninja School 3 menu", ["Game Java", "Game Java Mod"]))["kind"], None)
        self.assertEqual(b.classify_post(P("[Mod] Ninja School 3.5 offline", ["Game Java", "Game Java Mod"]))["kind"], "game")
        self.assertEqual(b.classify_post(P("James Cameron's Avatar Việt Hoá", ["Game Java"]))["kind"], "game")
        self.assertEqual(b.classify_post(P("Vương Quốc Sủng Vật 2 Việt Hoá", ["Game Java"]))["kind"], "game")
        self.assertEqual(b.classify_post(P("Playboy Casino Việt Hoá", ["Game Java"]))["kind"], None)
        self.assertEqual(b.classify_post(P("007 Casino Royale Việt Hoá", ["Game Java"]))["kind"], "game")
        self.assertEqual(b.classify_post(P("Sea Fantasy Việt Hoá | Game Android", ["Game Android"]))["kind"], None)
        self.assertEqual(b.classify_post(P("Brightness Patcher", ["App và Tools", "Java App"]))["kind"], "app")
        self.assertEqual(b.classify_post(P("Tải Theme Mandy Cat cho Nokia s60", ["Chủ Đề - Theme"]))["kind"], "media")
        self.assertEqual(b.classify_post(P("Hướng dẫn hackphone", ["Thủ Thuật", "JavaME Wiki"]))["kind"], "post")
        self.assertEqual(b.classify_post(P("DONATE", []))["kind"], None)
        self.assertEqual(b.classify_post(P("[Phát Hành] Snow Bros Việt Hoá | Game Java", []))["kind"], "game")
        self.assertEqual(b.classify_post(P("Avatar: Sự kiện hè", ["News"]))["kind"], None)

    def test_title_and_version(self):
        self.assertEqual(b.clean_title("[Phát Hành] Elven Chronicles Việt Hoá | Game Java J2ME"), "Elven Chronicles Việt Hoá")
        self.assertEqual(b.clean_title("Tải Game Java Snake 2017 tiếng Việt"), "Snake 2017 tiếng Việt")
        self.assertEqual(b.version_of({"title": "Sorcerer v1.75 Việt hoá", "_text": ""}), "1.75")
        self.assertEqual(b.version_of({"title": "Game", "_text": "Update v2 fix lỗi"}), "2")
        self.assertEqual(b.version_of({"title": "Game", "_text": "tên"}), "")

    def test_variant(self):
        self.assertEqual(b.variant_of("240x320 s60", "x.jar"), ("240x320", "s60", "goc"))
        self.assertEqual(b.variant_of("Tải xuống", "Game_VI_320x240.jar"), ("320x240", "j2me", "vh"))
        self.assertEqual(b.variant_of("", "Bomberman08_VI (1).jar"), (None, "j2me", "vh"))

    def test_jars_in(self):
        one = jar()
        self.assertEqual([n for n, _ in b.jars_in(one, "a.jar")], ["a.jar"])
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, "w") as z:
            z.writestr("x/240x320.jar", one)
            z.writestr("x/320x240.jar", jar("G2"))
            z.writestr("readme.txt", "hi")
        self.assertEqual(sorted(n for n, _ in b.jars_in(bio.getvalue(), "pack.zip")), ["240x320.jar", "320x240.jar"])
        self.assertEqual(b.jars_in(b"not a zip", "x.zip"), [])

    def test_alias_stable_and_build(self):
        self.assertEqual(b.alias_key("1", "240x320", "j2me", "goc", 0), b.alias_key("1", "240x320", "j2me", "goc", 0))
        self.assertNotEqual(b.alias_key("1", "240x320", "j2me", "goc", 0), b.alias_key("1", "320x240", "j2me", "goc", 0))
        html = ('<div><img src="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhABCDEFGHIJKLMNOPQRSTUVWXYZ/s320/a.jpg"/></div>'
                '<div>Thể Loại: nhập vai</div><div>Màn Hình: 240x320</div><div>Nội dung: Một game rất dài để làm mô tả cho bài viết thử nghiệm.</div>'
                '<a href="https://www.mediafire.com/file/abcdefghi1234/x.zip/file">Tải xuống</a>')
        p = {**P("[Port] Game Thử", ["Game Java", "Game Java Port", "Nhập Vai"], html), "kind": "game", "port": True, "n": 7, "files": [
            {"qk": "abcdefghi1234", "fn": "x.zip", "size": 1000, "created": "2026-05-01", "hint": {"label": "Tải xuống", "ord": 0, "folder": False},
             "jars": [{"name": "a.jar", "sha256": "aa", "bytes": 2048, "pd_id": "PD000001", "pd_name": "bdk-7-abcdef-a.jar"}]}]}
        post, why = b.build_post(p, set())
        self.assertEqual(why, "")
        self.assertEqual(post["meta"]["port"], "1")
        self.assertTrue(post["title"].startswith("[Port] Game Thử"))
        self.assertEqual(post["meta"]["cat"], "Nhập vai")
        self.assertIn("/v1/p/b", post["meta"]["v1"])
        self.assertTrue(post["meta"]["v1"].startswith("240x320|2|JAR=http://api.justmonika.top/v1/p/b"))
        self.assertIn("PORT:", post["html"])
        self.assertNotIn("mediafire", post["html"])
        self.assertIn("img", post["meta"])
        self.assertEqual(post["meta"]["ver"], "2026-05-01")
        # khong co JAR hop le -> bo
        p["files"][0]["jars"] = []
        self.assertIsNone(b.build_post(p, set())[0])


if __name__ == "__main__":
    unittest.main()
