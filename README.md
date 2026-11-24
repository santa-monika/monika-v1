# monika-v1

Công cụ lập chỉ mục metadata game Java/Symbian cho dự án Monika. Repo này **chỉ chứa mã và workflow**. Dữ liệu thu được ghi vào một repo riêng tư.

- `crawler/` — trình thu thập chậm (mặc định 2 giây mỗi yêu cầu), chạy lại được, không tải file game.
- `crawler/filters.py` — lọc nội dung người lớn, 18+, cờ bạc.
- `crawler/normalize.py`, `crawler/match.py` — chuẩn hóa tên, độ phân giải, loại bản (gốc / Việt hóa / mod) và đối chiếu trùng giữa các nguồn.
- `crawler/draft.py` — sinh nháp bài đăng từ dữ liệu và mô tả tự viết.
- `.github/workflows/` — chạy tay bằng `workflow_dispatch`.

Cần Secrets: `DATA_REPO_TOKEN` (fine-grained token, chỉ quyền ghi nội dung repo dữ liệu), `PD_KEY` (chỉ cho workflow lập chỉ mục Pixeldrain).

Chạy thử cục bộ: `python -m unittest discover -s tests`.

## bisduckopath.blogspot.com (nguồn còn cập nhật)

`crawler/bisducko.py` + `crawler/mediafire.py` + workflow `crawl-bisducko` (chạy hằng ngày 03:17 giờ Việt Nam, hoặc chạy tay):

- `sync`: feed Blogger JSON (`--since` chỉ lấy bài mới sửa; chủ nhật quét đầy đủ để phát hiện bài bị gỡ) → `data/bisducko/posts/<id>.json`, giữ HTML gốc, phân loại (game, app, giao diện, bài viết; bỏ game online, mod/hack game online, 18+, cờ bạc, không phải Java).
- `resolve`: mở link MediaFire qua API công khai (có sha256, revision). Tệp đổi nội dung hoặc tệp mới của bài cũ được ghi vào `history` của bài ("bản vá").
- `fetch`: tải tệp mới/đã đổi, tách gói zip nhiều JAR, gỡ quảng cáo nhúng, dedupe sha256, up Pixeldrain (`bdk-<n>-...`).
- `build`: `posts.json` cho `tools/blogger-import.mjs`, `bdk-aliases.json` (khóa tải ổn định → tệp hiện hành, đẩy lên nhánh công khai `bdk-data`), `skipped.json`. `report`: bài mới, bản vá, lỗi, game thiếu JAR/ảnh.
- Game **Port** (chạy trên giả lập): meta `port: 1`, nhãn `PORT`, tiêu đề giữ `[Port]`; Worker ẩn khỏi app, chỉ hiện trên web.

Cần Secrets: `DATA_REPO_TOKEN`, `PD_KEY` (đã có). Chạy thử cục bộ: `python -m unittest discover -s tests`.
