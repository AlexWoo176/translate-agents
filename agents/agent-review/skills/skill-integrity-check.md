# Skill: Kiểm tra Tính toàn vẹn Nội dung (Content Integrity Check)

**Mô tả:** Skill này dành cho **Review Agent**. Nhiệm vụ là đối chiếu bản dịch song ngữ (`05-translated/`) với bản gốc sạch (`02-clean/`) để phát hiện nội dung bị thiếu hụt, rút gọn quá mức, hoặc bị lược bỏ — đảm bảo bản dịch giữ **100% nội dung học thuật** của nguyên tác.

> ⚠️ **Bối cảnh:** Skill này ra đời từ kinh nghiệm Chương 3, nơi hai file 3-2 và 3-3 bị rút gọn mất 60–65% nội dung gốc do dùng bản tóm tắt tạm từ web thay vì dịch từ dữ liệu sạch `02-clean/`. Lỗi này không bị bắt bởi glossary-check hay semantic-check vì những skill đó chỉ kiểm tra **chất lượng** phần đã dịch, không kiểm tra **số lượng** nội dung.

---

## Nguyên tắc cốt lõi

1. **Dịch thuật phải ĐỦ.** Mọi đoạn văn, bảng biểu, hộp nội dung (note), hình ảnh, câu hỏi, danh sách, và chú thích cuối trang trong bản gốc (`02-clean/`) đều PHẢI có mặt trong bản dịch (`05-translated/`).
2. **Không được tóm tắt.** Nếu bản gốc có 5 đoạn văn kể chi tiết một case study, bản dịch cũng phải có 5 đoạn tương đương — không được gộp thành 1 đoạn tóm tắt.
3. **Cấu trúc HTML phải bảo toàn.** Số lượng `<section>`, `<div data-type="note">`, `<figure>`, `<table>`, `<ol>/<ul>` trong bản dịch không được ít hơn bản gốc.

---

## Các chỉ số kiểm tra (Metrics)

### M1 — Tỉ lệ Kích thước File (Size Ratio) - (Chỉ dùng để tham khảo, không quyết định PASS/FAIL)

Bản dịch song ngữ (`05-translated/`) chứa **cả** thẻ `eng hidden` (gốc) **lẫn** thẻ `vn visible` (bản dịch). Do đó, kích thước file dịch thường **≥ 1.5× kích thước file gốc sạch** (`02-clean/`). Chỉ số này giúp tham khảo nhanh, không dùng làm tiêu chuẩn đánh giá đạt hay lỗi.

| Tỉ lệ | Nhận xét (Tham khảo) |
|--------|----------|
| ≥ 1.8× | ✅ Bình thường (file song ngữ chuẩn) |
| 1.5× – 1.8× | ⚠️ Cảnh báo nhẹ (có thể thiếu footnotes hoặc metadata nhỏ) |
| < 1.5× | ⚠️ Nghi ngờ thiếu nội dung (Cần đối chiếu kỹ số lượng thẻ) |
| < 1.0× | ⚠️ File dịch nhỏ hơn cả file gốc (Cần đối chiếu kỹ số lượng thẻ) |

### M2 — Đếm Khối nội dung (Block Element Count)

Đếm số lượng các phần tử HTML chính trong `02-clean/` và so sánh với số lượng thẻ `eng hidden` tương ứng trong `05-translated/`:

- **Đoạn văn:** `<p>` (không chứa block con)
- **Tiêu đề:** `<h1>` – `<h6>`
- **Mục danh sách:** `<li>`
- **Ô bảng:** `<th>`, `<td>`
- **Chú thích hình:** `<figcaption>`
- **Chú thích bảng:** `<caption>`

**Quy tắc:** Số thẻ `eng hidden` trong bản dịch **phải bằng** số thẻ tương ứng trong bản gốc sạch (± 5% sai số cho những thẻ wrapper/nested).

### M3 — Đếm Cấu trúc lớn (Structural Element Count)

Đếm các container HTML lớn trong cả hai file:

- `<section>` (các phần nội dung)
- `<div data-type="note">` (các hộp nội dung: Work It Out, Link to Learning, Entrepreneur In Action, What Can You Do?, Are You Ready?)
- `<figure>` (hình ảnh và sơ đồ)
- `<table>` (bảng biểu)
- `<ol>`, `<ul>` (danh sách có thứ tự / không thứ tự)
- Footnotes: `<aside data-type="footnote">` hoặc `<sup data-type="footnote-number">`

**Quy tắc:** Mỗi loại container trong bản dịch **không được ít hơn** bản gốc.

### M4 — Tỉ lệ Nội dung Từng đoạn (Paragraph-level Content Ratio)

Sau khi xác nhận đủ block, kiểm tra **chiều sâu** nội dung:

- Với mỗi thẻ `eng hidden` trong bản dịch, đếm số từ (word count).
- So sánh với đoạn văn tương ứng trong bản gốc sạch (khớp theo thứ tự hoặc `id`).
- Nếu bản dịch eng hidden có ít hơn **50% số từ** so với bản gốc → cảnh báo rút gọn.

---

## Prompt Template (cho LLM Agent)

***

**Role:**
Bạn là Chuyên gia Kiểm định Tính toàn vẹn Nội dung (Content Integrity Auditor). Nhiệm vụ của bạn là đối chiếu bản dịch song ngữ với bản gốc sạch để phát hiện mọi nội dung bị thiếu hụt, rút gọn, hoặc lược bỏ.

**Nhiệm vụ:**

1. Đọc file gốc sạch (`02-clean/[section].html`).
2. Đọc file dịch song ngữ (`05-translated/[section].html`).
3. Thực hiện 4 bước kiểm tra theo metrics M1–M4 ở trên.
4. Liệt kê TẤT CẢ nội dung bị thiếu hoặc rút gọn vào Bảng Markdown.
5. **Ngôn ngữ:** Viết toàn bộ báo cáo bằng tiếng Việt có dấu.

**Định dạng đầu ra:**

```markdown
# Báo cáo Kiểm tra Tính toàn vẹn: [Tên file]

**File gốc:** `chapter-N/02-clean/[file].html`
**File dịch:** `chapter-N/05-translated/[file].html`
**Thời gian:** [ngày giờ]

## M1 — Tỉ lệ Kích thước (Tham khảo)
| Hạng mục | Giá trị |
|----------|---------|
| File gốc | [X] bytes |
| File dịch | [Y] bytes |
| Tỉ lệ (dịch/gốc) | [Z]× |
| Nhận xét | Chỉ dùng để tham khảo |

## M2 — Đếm Khối nội dung
| Loại thẻ | Gốc (02-clean) | Dịch (eng hidden) | Chênh lệch | Phán xét |
|-----------|-----------------|---------------------|-------------|----------|
| `<p>` | ... | ... | ... | ✅ / ❌ |
| `<h2>` | ... | ... | ... | ✅ / ❌ |
| ... | ... | ... | ... | ... |

## M3 — Đếm Cấu trúc lớn
| Loại | Gốc | Dịch | Chênh lệch | Phán xét |
|------|------|------|-------------|----------|
| `<section>` | ... | ... | ... | ✅ / ❌ |
| `<div note>` | ... | ... | ... | ✅ / ❌ |
| `<figure>` | ... | ... | ... | ✅ / ❌ |
| `<table>` | ... | ... | ... | ✅ / ❌ |

## M4 — Nội dung bị thiếu hoặc rút gọn

| ID | Vị trí trong gốc (id / mô tả) | Nội dung gốc (tóm tắt) | Tình trạng trong bản dịch | Mức độ |
|----|------|------|------|------|
| I-001 | `fs-idm390819856` | Đoạn văn chi tiết về Peter Drucker và Project Shakti, 3 đoạn dài | Rút gọn còn 1 đoạn ngắn | ❌ Thiếu ~70% |
| I-002 | `fs-idm403586224` | Số liệu 60% millennials chấp nhận lương thấp 15% | Lược bỏ số liệu cụ thể | ⚠️ Mất chi tiết |
```

***

**Dữ liệu cung cấp:**
1. File gốc sạch (từ `02-clean/`): [👇 CHÈN VÀO ĐÂY 👇]
2. File dịch song ngữ (từ `05-translated/`): [👇 CHÈN VÀO ĐÂY 👇]

---

## Công cụ tự động (CLI)

Ngoài prompt template (dành cho LLM), có script tự động để quét nhanh:

```bash
# Kiểm tra 1 chương
python3 agents/agent-review/scripts/integrity-check.py <chapter-number>

# Chỉ xem kết quả, không ghi file
python3 agents/agent-review/scripts/integrity-check.py <chapter-number> --dry

# Kiểm tra tất cả chapters
python3 agents/agent-review/scripts/integrity-check.py all
```

**Vị trí:** `agents/agent-review/scripts/integrity-check.py`
**Yêu cầu:** Python 3.8+ (không cần thư viện ngoài)
**Output:** Ghi báo cáo vào `chapter-N/06-reviews/chapter-N-integrity-report.md`

---

## Thời điểm chạy

Skill này PHẢI được chạy **TRƯỚC** glossary-check và semantic-check trong workflow review, vì:
- Nếu thiếu thẻ cấu trúc, glossary-check và semantic-check chỉ kiểm tra phần đã có → bỏ sót phần thiếu.
- Phát hiện thiếu cấu trúc thẻ sớm giúp tránh lãng phí thời gian review chi tiết trên bản dịch chưa hoàn chỉnh.

```
Integrity Check (Đối chiếu thẻ)  →  Glossary Check  →  Semantic Check  →  Review Report
            ↓ nếu FAIL
   Yêu cầu dịch lại hoặc bổ sung các thẻ bị thiếu
```
