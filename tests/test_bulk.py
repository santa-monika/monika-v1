import unittest, json, os, tempfile
from crawler.genre import guess_genre
from crawler.vi_desc import describe
from crawler import dedomil
from crawler.blogger_json import split


class TestBulk(unittest.TestCase):
    def test_genre(self):
        self.assertEqual(guess_genre("Gangstar Rio: City of Saints"), "Hành động")
        self.assertEqual(guess_genre("Real Football 2012"), "Thể thao")
        self.assertEqual(guess_genre("Asphalt 6"), "Đua xe")
        self.assertEqual(guess_genre("Tetris"), "Giải đố & trí tuệ")
        self.assertEqual(guess_genre("Zzz Qqq", ""), "Khác")

    def test_describe_len(self):
        g = {"source_id": 7, "title": "Foo", "vendor": "Gameloft"}
        d, body = describe(g, "Hành động", ["240x320", "320x240"], 100, 300)
        self.assertLessEqual(len(d), 120)
        self.assertIn("Foo", body)
        self.assertIn("240x320", body)

    def test_split(self):
        self.assertEqual([len(x) for x in split(list(range(7)), 3)], [3, 3, 1])

    def test_missing_marker(self):
        class F:
            requests = 0
            def get(self, url, **kw):
                import urllib.error
                raise urllib.error.HTTPError(url, 404, "nf", None, None)
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "dedomil", "games")
            done, skipped, fail = dedomil.crawl_games([1, 2], out, F())
            self.assertEqual((done, fail), (0, 0))
            self.assertEqual(json.load(open(os.path.join(d, "dedomil", "missing.json"))), [1, 2])
            done, skipped, fail = dedomil.crawl_games([1, 2], out, F())
            self.assertEqual(skipped, 2)


if __name__ == "__main__":
    unittest.main()
