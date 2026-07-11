# Agent: Translate

**Mô tả:** Agent chịu trách nhiệm dịch thuật các nội dung HTML (giữ nguyên cấu trúc thẻ) từ tiếng Anh sang tiếng Việt dựa trên **`glossary.csv`** và báo cáo phân tích rủi ro, đồng thời có khả năng tương tác với Review Agent để giải trình hoặc chỉnh sửa bản dịch theo góp ý.

## Danh sách Kỹ năng (Skills)

Translate Agent được trang bị 2 kỹ năng (skills) chính yếu sau đây:

1. **[Dịch thuật (skill-translate)](skills/skill-translate.md)**: 
   - Input bắt buộc: `glossary.csv` + `[section]-translate-analysis.md` + HTML từ `04-prep/`.
   - Dịch nội dung từ tiếng Anh sang tiếng Việt, ghi đè vào thẻ `vn visible`.
   - Dịch từng cặp thẻ tuần tự, không cố dịch cả file một lượt.
   - Output: HTML đã dịch lưu vào `05-translated/`.

2. **[Xử lý Phản biện (skill-handle-review)](skills/skill-handle-review.md)**:
   - Tiếp nhận báo cáo lỗi (Critique) dạng bảng từ Review Agent.
   - Phân tích lỗi, ra quyết định **[CHẤP NHẬN SỬA]** hoặc **[TỪ CHỐI SỬA]** (kèm lý do).
   - Tự động cập nhật các sửa đổi vào trong file HTML đối với những lỗi được chấp nhận.

## Tài liệu tham chiếu (phải đọc)

- [`translation-standard.md`](../agent-analyze/translation-standard.md) — Tiêu chuẩn ISO 17100 + MQM
- [`student-profile.md`](../agent-analyze/student-profile.md) — Đối tượng độc giả
- [`Kinh nghiệm dịch giáo trình với AI.md`](skills/Kinh%20nghiệm%20dịch%20giáo%20trình%20với%20AI.md) — Quy trình phối hợp con người + AI
