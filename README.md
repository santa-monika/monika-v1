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
