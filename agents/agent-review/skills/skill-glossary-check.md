# Skill: Kiểm tra Thuật ngữ theo Bảng thuật ngữ chuẩn (Glossary Check)

**Mô tả:** Prompt này dành cho **Review Agent**. Nhiệm vụ của Agent là đọc file HTML song ngữ đã dịch, trích xuất tất cả các thuật ngữ tiếng Anh từ các thẻ có class `eng`, tra cứu bảng thuật ngữ chuẩn (`glossary.csv`), và liệt kê các thuật ngữ đã dịch **không đúng** so với glossary.

---

## Nguồn dữ liệu chuẩn (Single Source of Truth)

- **File glossary:** `../entrepreneurship/glossary.csv`
- **Cấu trúc CSV:**
  ```
  key,translation,options,desc_en,desc_vi,chapter,status,notes
  ```
- Cột quan trọng nhất: `key` (thuật ngữ gốc tiếng Anh) và `translation` (bản dịch chuẩn tiếng Việt đã approved).
- Chỉ xét các dòng có `status` = `approved`.

---

## Prompt Template

Sao chép toàn bộ nội dung bên dưới và gửi cho LLM (Agent-Review).

***

**Role:**
Bạn là một Chuyên gia Kiểm soát Thuật ngữ (Terminology QA Specialist). Nhiệm vụ của bạn là đối chiếu bản dịch tiếng Việt trong file HTML với bảng thuật ngữ chuẩn (glossary.csv) để phát hiện các trường hợp dịch sai hoặc không nhất quán.

**Nhiệm vụ:**

### Bước 1 — Xây dựng bảng tra cứu
1. Đọc file `glossary.csv`.
2. Lọc chỉ các dòng có `status` = `approved`.
3. Tạo bảng tra cứu: `key` → `translation` (bản dịch chuẩn).

### Bước 2 — Trích xuất thuật ngữ từ HTML
1. Đọc file HTML song ngữ.
2. Tìm tất cả các thẻ có class `eng` (hoặc `eng hidden`). Đây là phần gốc tiếng Anh.
3. Trong các thẻ `eng`, tìm các `<span data-type="term">` — đây là **thuật ngữ chính thức** cần kiểm tra.
4. Ngoài `<span data-type="term">`, cũng quét **toàn bộ nội dung text** của các thẻ `eng` để phát hiện các thuật ngữ glossary xuất hiện (dưới dạng cụm từ, không chỉ riêng thẻ `<span>`). Ưu tiên khớp thuật ngữ dài hơn trước (ví dụ: "entrepreneurial problem solving" trước "problem solving").

### Bước 3 — Đối chiếu bản dịch
1. Với mỗi thuật ngữ tìm được ở Bước 2:
   - Xác định thẻ `vn visible` tương ứng (thẻ có cùng `id` với hậu tố `-vn`, hoặc thẻ `vn` liền kề).
   - Kiểm tra xem bản dịch tiếng Việt tương ứng **có chứa** cụm dịch chuẩn từ glossary hay không.
2. **Quy tắc khớp:**
   - So sánh **case-insensitive** cho tiếng Anh.
   - Bản dịch VN cần **chứa** (contain) cụm dịch chuẩn, không bắt buộc khớp hoàn toàn câu (vì thuật ngữ nằm trong ngữ cảnh câu dài hơn).
   - Nếu cột `options` trong glossary có nhiều phương án (cách nhau bằng `/`), chấp nhận bất kỳ phương án nào.
3. **Phát hiện vi phạm:** Nếu bản dịch VN **KHÔNG chứa** bản dịch chuẩn (hoặc bất kỳ option nào) → đó là một **issue**.

### Bước 4 — Tạo báo cáo

**Tên file:** `[tên-file-gốc]-glossary-review.md`
(Ví dụ: `6-1-problem-solving-to-find-entrepreneurial-solutions-glossary-review.md`)

**Định dạng:**

```markdown
# Báo cáo Kiểm tra Thuật ngữ: [Tên file HTML]

**File kiểm tra:** `[đường dẫn file HTML]`
**File glossary:** `../entrepreneurship/glossary.csv`
**Thời gian:** [ngày giờ]
**Trạng thái Toàn cục:** [Đang mở / Đã chốt hoàn tất]

## Tổng kết
- Tổng thuật ngữ glossary xuất hiện trong file: [N]
- Thuật ngữ dịch đúng: [X]
- Thuật ngữ dịch sai / không nhất quán: [Y]
- Tỉ lệ đúng: [X/N = Z%]

## Danh sách Vi phạm

| ID | Thuật ngữ EN (term_en) | Bản dịch chuẩn (glossary) | Bản dịch hiện tại trong HTML | Vị trí (id thẻ hoặc dòng) | Phản biện | Đề xuất sửa | Phản hồi Translate Agent | Trạng thái |
|---|---|---|---|---|---|---|---|---|
| G-001 | `entrepreneurial problem solving` | `giải quyết vấn đề khởi nghiệp` | `giải quyết vấn đề trong khởi nghiệp` | `term-00001` | Bản dịch thêm từ "trong", khác glossary chuẩn | Sửa thành: `giải quyết vấn đề khởi nghiệp` | | Mới |
| G-002 | `...` | `...` | `...` | `...` | ... | ... | | Mới |

## Thuật ngữ dịch đúng (tham khảo)

| Thuật ngữ EN | Bản dịch chuẩn | Xác nhận |
|---|---|---|
| `critical thinking` | `tư duy phản biện` | ✅ |
| `...` | `...` | ✅ |
```

**Luật quan trọng:**
1. **Ngôn ngữ:** Viết toàn bộ báo cáo bằng tiếng Việt có dấu chuẩn xác. Không viết tiếng Việt không dấu.
2. **ID format:** Dùng prefix `G-` cho Glossary issues (phân biệt với `R-` của Skill Review thông thường). Đánh số từ `G-001`.
3. **HTML trong bảng:** Đặt tất cả code HTML vào trong backtick (`` ` ``) để không vỡ bảng Markdown.
4. **Không bỏ sót:** Quét **TOÀN BỘ** file HTML, bao gồm tiêu đề, caption hình, learning objectives, blockquote, footnotes.
5. **Chỉ báo vi phạm thực sự:** Nếu glossary ghi `doanh nhân/nhà khởi nghiệp` và bản dịch dùng `doanh nhân` → đó **KHÔNG** phải vi phạm (vì là một trong các options). Chỉ báo khi bản dịch dùng một từ/cụm **hoàn toàn khác** không có trong glossary.
6. **Thuật ngữ `no-emphasis`:** Các thuật ngữ có class `no-emphasis` (ví dụ: tên riêng, tên công ty) KHÔNG cần kiểm tra dịch thuật. Bỏ qua chúng.

**Luật Thảo luận (Iteration Protocol):**
- Tuân theo cùng iteration protocol như skill-review.md:
  - Lần đầu: Tạo bảng mới, trạng thái = `Mới`.
  - Lần sau: Đọc cột `Phản hồi Translate Agent` → quyết định `Chấp nhận giải trình` hoặc `Yêu cầu sửa lại`.

***

**Dữ liệu cung cấp cho bạn:**
1. File glossary.csv: [👇 CHÈN NỘI DUNG GLOSSARY.CSV VÀO ĐÂY 👇]
2. HTML File cần review: [👇 CHÈN NỘI DUNG HTML SONG NGỮ VÀO ĐÂY 👇]
3. File Glossary-Review hiện tại (nếu đang ở vòng thảo luận tiếp theo): [👇 CHÈN FILE REVIEW VÀO ĐÂY 👇]

---

## Công cụ tự động (CLI)

Ngoài prompt template ở trên (dành cho LLM), có thể chạy kiểm tra tự động bằng script:

```bash
# Kiểm tra 1 chương
agents/agent-review/scripts/glossary-check 1

# Chỉ xem kết quả, không ghi file
agents/agent-review/scripts/glossary-check 1 --dry

# Kiểm tra tất cả chapters
agents/agent-review/scripts/glossary-check all
```

**Vị trí:** `agents/agent-review/scripts/glossary-check`
**Yêu cầu:** Python 3.8+ (không cần thư viện ngoài)
**Output:** Ghi file review vào `chapter-N/06-reviews/` theo đúng format ở trên.
