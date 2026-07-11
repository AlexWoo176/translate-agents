# Agent: Export

## Mô tả

**Agent-Export** đảm nhiệm việc xuất bản bản dịch tiếng Việt ra định dạng DOCX để bàn giao hoặc in ấn.

> ⚠️ **Trạng thái hiện tại: SKELETON** — Argument parsing và validation đã hoàn thiện. Logic export DOCX thực tế **chưa được implement**. Script sẽ chạy và validate args, nhưng không tạo file DOCX.

---

## Lệnh sử dụng

```bash
# Xuất tất cả chương
node agents/agent-export/scripts/export-docx.js all [bookName]

# Xuất một chương cụ thể
node agents/agent-export/scripts/export-docx.js <chapter-number> [bookName]

# Xuất một file HTML cụ thể
node agents/agent-export/scripts/export-docx.js <path/to/file.html> [bookName]
```

**Tham số:**
| Tham số | Mô tả | Bắt buộc |
|---------|-------|---------|
| `target` | `all`, số chương (vd: `1`), hoặc path file HTML | ✅ |
| `bookName` | Tên sách (mặc định: `entrepreneurship`) | Không |

---

## Input / Output

- **Input:** Các file HTML trong `../<bookName>/chapter-N/05-translated/`
- **Output:** DOCX files trong `../<bookName>/docx/`
- **Dependency:** `html-to-docx` (đã có trong root `package.json`)

---

## Kế hoạch implement (TODO)

Khi implement thực sự, script cần:

1. Đọc file HTML từ `05-translated/` (lọc ra chỉ `vn visible` content, loại `eng hidden`)
2. Strip các class `eng hidden` / `vn visible` khỏi HTML trước khi convert
3. Gọi `html-to-docx` để convert từng file HTML → DOCX
4. Lưu output vào `../<bookName>/docx/chapter-N/`
5. Báo cáo số file đã export

---

## Tài liệu tham chiếu

- [`agent-archive.md`](../agent-archive/agent-archive.md) — Quy trình đóng gói và lưu trữ
- [`skill-translate.md`](../agent-translate/skills/skill-translate.md) — Cấu trúc `eng hidden` / `vn visible`
- [`master-workflow.md`](../../workflow/master-workflow.md) — Vị trí export trong pipeline tổng thể
