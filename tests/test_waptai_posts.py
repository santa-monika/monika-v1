import json, os, tempfile, unittest
from datetime import datetime, timezone
from crawler import waptai_posts as wp, waptai_images as wi


def rec(kind, sid, **kw):
    r = {"source_id": sid, "kind": kind, "filter": {"status": "ok"}, "page_url": f"https://java.waptai.com/x{sid}/", "title": f"t{sid}",
         "categories": [], "images": [], "downloads": [], "comic_pages": []}
    r.update(kw)
    return r


def put(d, r):
    os.makedirs(os.path.join(d, "waptai", "posts"), exist_ok=True)
    json.dump(r, open(os.path.join(d, "waptai", "posts", f"{r['source_id']}.json"), "w"))


class T(unittest.TestCase):
    def test_truyen_guide_app_va_anh_kho(self):
        with tempfile.TemporaryDirectory() as d:
            put(d, rec("truyen", 1, comic_pages=[{"src": "https://java.waptai.com/wp-content/uploads/a-1.jpg", "caption": "x"},
                                                  {"src": "https://java.waptai.com/wp-content/uploads/a-2.jpg", "caption": "y"}]))
            put(d, rec("truyen", 2, comic_pages=[{"src": "https://java.waptai.com/wp-content/uploads/b-1.jpg", "caption": "x"}]))
            put(d, rec("meo", 3))
            put(d, rec("meo", 4))
            put(d, rec("phan_mem", 5, downloads=[{"own_host": True, "ext": "jar", "url": "u", "resolution": "240x320", "models": ""}],
                       images=[{"src": "https://java.waptai.com/picture/p.png", "w": 120}],
                       local={"files": [{"url": "u", "file": "5/p.jar", "pixeldrain_id": "PD123456", "bytes_clean": 2048, "resolution": "240x320"}]}))
            idx = {"https://java.waptai.com/wp-content/uploads/a-1.jpg": {"pixeldrain_id": "IMG11111", "name": "waptai-img-0123456789ab.jpg"}}
            td = {"1": {"id": 1, "title": "Đôrêmon chế: A", "desc": "d", "body": "b"}, "2": {"id": 2, "title": "B", "desc": "d", "body": "b", "flag": "can-duyet"}}
            gd = {"3": {"id": 3, "title": "Mẹo", "desc": "d", "body_html": "<p>x</p>"}, "4": {"id": 4, "title": "Bỏ", "desc": "d", "body_html": "", "flag": "bo"}}
            ad = {"5": {"id": 5, "title": "App", "cat": "Đời sống", "desc": "d", "body": "p1\n\np2"}}
            posts, skipped = wp.build(d, {}, datetime(2026, 1, 1, tzinfo=timezone.utc), None, idx, ad, td, gd)
            by = {p["title"]: p for p in posts}
            self.assertEqual(set(by), {"App", "Đôrêmon chế: A", "Mẹo"})
            self.assertEqual(by["App"]["meta"]["type"], "app")
            self.assertIn("/v1/p/PD123456/p.jar", by["App"]["meta"]["v1"])
            tr = by["Đôrêmon chế: A"]
            self.assertEqual(tr["labels"], ["Bài viết", "Truyện tranh & manga"])
            self.assertIn("api.justmonika.top/v1/pi/IMG11111/waptai-img-0123456789ab.jpg", tr["html"])
            self.assertIn("java.waptai.com/wp-content/uploads/a-2.jpg", tr["html"])  # chua chuyen thi con hotlink tam
            self.assertEqual(by["Mẹo"]["meta"]["cat"], "Thủ thuật & mẹo")
            self.assertEqual(len(skipped), 2)

    def test_ten_anh_theo_noi_dung(self):
        self.assertEqual(wi.ext_of(b"\xff\xd8\xff\xe0abc"), "jpg")
        self.assertIsNone(wi.ext_of(b"<html>"))


if __name__ == "__main__":
    unittest.main()
