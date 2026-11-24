# monika-v1

Công cụ lập chỉ mục metadata game Java/Symbian cho dự án Monika. Repo này **chỉ chứa mã và workflow**. Dữ liệu thu được ghi vào một repo riêng tư.

- `crawler/` — trình thu thập chậm (mặc định 2 giây mỗi yêu cầu), chạy lại được, không tải file game.
- `crawler/filters.py` — lọc nội dung người lớn, 18+, cờ bạc.
- `crawler/normalize.py`, `crawler/match.py` — chuẩn hóa tên, độ phân giải, loại bản (gốc / Việt hóa / mod) và đối chiếu trùng giữa các nguồn.
- `crawler/waptai.py` — metadata java.waptai.com qua WordPress REST API (~10 yêu cầu cho ~950 bài), lọc game online / mod hack / 18+.
- `crawler/jarclean.py`, `crawler/waptai_jars.py` — tải JAR của waptai và gỡ mục nhúng (MIDlet phụ `WapTai.COM` mở https://waptai.com, class + icon đi kèm, dòng waptai trong MANIFEST). Chỉ sửa MANIFEST và xóa mục zip, các mục còn lại giữ nguyên byte. JAR có chữ ký số bị bỏ qua.
- `crawler/draft.py` — sinh nháp bài đăng từ dữ liệu và mô tả tự viết.
- `.github/workflows/` — chạy tay bằng `workflow_dispatch`.

Cần Secrets: `DATA_REPO_TOKEN` (fine-grained token, chỉ quyền ghi nội dung repo dữ liệu), `PD_KEY` (chỉ cho workflow lập chỉ mục Pixeldrain).

Chạy thử cục bộ: `python -m unittest discover -s tests`.
- `crawler/pd_upload.py` — đưa JAR sạch lên Pixeldrain của chủ dự án (dedupe sha256, ghi `pixeldrain_id` vào JSON bài).
- `crawler/waptai_images.py` — chuyển ảnh minh họa và trang truyện của waptai về Pixeldrain (tên `waptai-img-<sha12>.<đuôi>`, ghi `data/waptai/images.json`); Worker phát lại ở `/v1/pi/<ID>/<tên>`. Tải chậm (0,6 giây một ảnh), dừng ngay khi gặp 429.
- `crawler/waptai_posts.py` — dựng `posts.json` cho `tools/blogger-import.mjs` của monika-java: game, phần mềm (cần đủ JAR đã lên Pixeldrain), truyện (`Truyện tranh & manga`) và mẹo (`Thủ thuật & mẹo`), mô tả đều là bản viết lại. `--per-file 300` chia thành `posts-001.json`, `posts-002.json`... Bài nào ảnh chưa chuyển xong thì tạm hotlink nguồn.
- `crawler/waptai_clean_images.py` — xóa chữ `WapTai.COM` in sẵn trên ảnh chụp game rộng 176 px (khớp mặt nạ màu vàng của chữ, tô lại vùng chữ, up bản sạch lên Pixeldrain, ghi trường `clean` trong `images.json`). Cần `opencv-python-headless`. ~95% ảnh sạch, đôi chỗ để vệt mờ hoặc sót chữ; ảnh không nhận diện chắc giữ nguyên.
