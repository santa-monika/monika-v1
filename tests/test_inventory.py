import io, unittest, zipfile
from crawler import inventory, fetch_jars


def make_jar(manifest, extra=None):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("META-INF/MANIFEST.MF", manifest)
        for k, v in (extra or {}).items():
            z.writestr(k, v)
    return b.getvalue()


class T(unittest.TestCase):
    def test_title_res(self):
        t, r = inventory.clean_title("Spiderman-Toxic-City-176x220.jar")
        self.assertEqual((t, r), ("Spiderman Toxic City", "176x220"))
        t, r = inventory.clean_title("S40-Assassins-Creed-III-240x320.jar")
        self.assertEqual((t, r), ("Assassins Creed III", "240x320"))

    def test_group_merges_variants(self):
        a = inventory.make("x", "u1", "Contra4-176x208-wapm4u.jar", "direct")
        b = inventory.make("x", "u2", "Contra4-240x320.jar", "direct")
        self.assertEqual(a["group"], b["group"])

    def test_inspect_ok_and_promo(self):
        ok = fetch_jars.inspect(make_jar("MIDlet-1: Game, /i.png, G\r\n"))
        self.assertTrue(ok["ok"] and ok["promo"] == [])
        pr = fetch_jars.inspect(make_jar("MIDlet-1: Game, , G\r\nMIDlet-Info-URL: http://wapvip.pro\r\n"))
        self.assertIn("wapvip", pr["promo"])

    def test_inspect_bad(self):
        self.assertFalse(fetch_jars.inspect(b"<html>")["ok"])
        self.assertFalse(fetch_jars.inspect(make_jar("Foo: bar\r\n"))["ok"])


if __name__ == "__main__":
    unittest.main()
