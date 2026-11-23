# monika-v1

Công cụ lập chỉ mục metadata game Java/Symbian cho dự án Monika. Repo này **chỉ chứa mã và workflow**. Dữ liệu thu được ghi vào một repo riêng tư.

- `crawler/` — trình thu thập chậm (mặc định 2 giây mỗi yêu cầu), chạy lại được, không tải file game.
- `crawler/filters.py` — lọc nội dung người lớn, 18+, cờ bạc.
- `crawler/normalize.py`, `crawler/match.py` — chuẩn hóa tên, độ phân giải, loại bản (gốc / Việt hóa / mod) và đối chiếu trùng giữa các nguồn.
- `crawler/draft.py` — sinh nháp bài đăng từ dữ liệu và mô tả tự viết.
- `.github/workflows/` — chạy tay bằng `workflow_dispatch`.

Cần Secrets: `DATA_REPO_TOKEN` (fine-grained token, chỉ quyền ghi nội dung repo dữ liệu), `PD_KEY` (chỉ cho workflow lập chỉ mục Pixeldrain).

Chạy thử cục bộ: `python -m unittest discover -s tests`.
