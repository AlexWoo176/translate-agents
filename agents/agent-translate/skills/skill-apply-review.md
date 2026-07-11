# Skill: Áp dụng Bản vá từ Review Report (Apply Review Fixes)

**Mô tả:** Đây là quy trình CHUẨN MỰC và DUY NHẤT để Translate Agent sửa lỗi dựa trên phản hồi của Review Agent. Tuyệt đối KHÔNG tự ý viết các script Python nháp (scratch) để sửa HTML.

---

## Khi nào sử dụng Skill này?
Bạn phải gọi Skill này ngay khi nhận được thông báo từ Review Agent rằng: *"Đã sinh Báo cáo Nghiệm thu (Review Report) và phát hiện ra các lỗi Mới."*

## Các bước thực hiện:

**Bước 1: Không tự sửa code thủ công**
Báo cáo của Review Agent (`*-semantic-review-round-X.md`) đã chứa sẵn bảng mapping giữa `Bản dịch hiện tại` và `Đề xuất sửa`. Bạn không cần phải làm gì thủ công cả.

**Bước 2: Gọi Tool tự động hóa**
Translate Agent có đặc quyền sử dụng script `apply-review-fixes.py`. Hãy chạy lệnh sau trong Terminal:

```bash
python3 agents/agent-translate/scripts/apply-review-fixes.py <đường-dẫn-đến-file-báo-cáo-review> <đường-dẫn-đến-file-html-tương-ứng>
```

*(Ví dụ: `python3 agents/agent-translate/scripts/apply-review-fixes.py data/entrepreneurship/chapter-2/06-reviews/2-1-overview-of-the-entrepreneurial-journey-semantic-review-round-2.md data/entrepreneurship/chapter-2/05-translated/2-1-overview-of-the-entrepreneurial-journey.html`)*

**Bước 3: Đọc kết quả**
Script sẽ tự động:
1. Parse bảng Markdown.
2. Tìm và thay thế chính xác các lỗi trong file HTML.
3. Cập nhật lại trạng thái thành `Đã sửa` và ghi nhận `Đồng ý, đã sửa theo đề xuất.` vào cột phản hồi trong file Markdown.

Nếu script báo `Cảnh báo: Không tìm thấy đoạn text`, lúc đó bạn mới được phép mở file HTML ra để kiểm tra chéo xem có phải Review Agent đã trích xuất sai nguyên bản không, và có thể dùng `multi_replace_file_content` để can thiệp thủ công.

---
**🚨 SUPREME RULE (Luật Tối thượng của Translate Agent):**
KHÔNG sinh ra file rác. Việc sử dụng các file `scratch_*.py` trong môi trường dự án là HÀNH VI VI PHẠM nguyên tắc quản lý mã nguồn sạch. Luôn sử dụng Tool có sẵn!
