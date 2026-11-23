import unittest
from crawler.dedomil import parse_game, parse_ids
from crawler.filters import classify
from crawler.normalize import norm_title, variant_kind, resolution

PAGE = '''<div class="NHRY">Jet Ski Venice</div>
<div class="SPLASH"><a href="/hry_scr/x/Jet_1.jpg"><img/></a></div>
<div class="SECSCR"><a href="/hry_scr/x/Jet_2.gif">[second]</a></div>
<div class="OPIS"><b>Added</b>: 22.06.2019<br/></div>
<div class="OPIS"><b>Downloads</b>: 48825</div>
<div class="OPIS"><b>Vendor</b>: Microforum</div>
<div><b>Description</b>: Race a jet ski in Venice.
 <br><br>
 <b>The game's characteristics may vary.</b></div>
<div class="MODELS"><img/> Nokia 3220 / 6020 (<b>128x128</b>)</div>
<div class="LOAD"><a href="/games/8189/download/94679" class="bluelink">JAD</a> |
<a href="/games/8189/download-jar/94679" class="bluelink">JAR</a> 55.4kB</div>
<div class="MODELS"><img/> Nokia 5800 (<b>360x640</b>)</div>
<div class="LOAD"><a href="/games/8189/download/94680" class="bluelink">download</a> 1.5MB</div>'''


class T(unittest.TestCase):
    def test_parse_game(self):
        g = parse_game(PAGE, 8189)
        self.assertEqual(g["title"], "Jet Ski Venice")
        self.assertEqual(g["vendor"], "Microforum")
        self.assertEqual(g["downloads"], 48825)
        self.assertEqual(len(g["screenshots"]), 2)
        self.assertEqual([v["kind"] for v in g["variants"]], ["jar", "zip_hoac_khac"])
        self.assertEqual(g["variants"][0]["resolution"], "128x128")
        self.assertEqual(g["variants"][1]["size_kb"], 1536)
        self.assertEqual(g["filter"]["status"], "ok")
        self.assertEqual([(r["resolution"], r["kind"]) for r in g["by_resolution"]], [("128x128", "jar"), ("360x640", "zip_hoac_khac")])

    def test_ids(self):
        h = '<a href="/games/12/screens">a</a><a href="/games/12/category/1">b</a><a href="/games/7/screens">c</a>'
        self.assertEqual(parse_ids(h), [12, 7])

    def test_filter(self):
        self.assertEqual(classify("Roulette Royal Casino")[0], "loai")
        self.assertEqual(classify("Hot Asian Calendar 2009")[0], "loai")
        self.assertEqual(classify("Real Football 2012")[0], "ok")
        self.assertEqual(classify("Game danh bai Tien Len")[0], "loai")

    def test_normalize(self):
        self.assertEqual(norm_title("Tam-quoc-dai-chien_240x320.jar"), norm_title("Tam Quoc Dai Chien"))
        self.assertEqual(norm_title("Sky-force-VH_128x160.jar"), norm_title("Sky Force"))
        self.assertEqual(variant_kind("Sky-force-VH_128x160.jar"), "viethoa")
        self.assertEqual(variant_kind("Army 2.3.9 Hack"), "mod")
        self.assertEqual(variant_kind("Real Football 2012"), "goc")
        self.assertEqual(resolution("x_240X320.jar"), "240x320")


if __name__ == "__main__":
    unittest.main()
