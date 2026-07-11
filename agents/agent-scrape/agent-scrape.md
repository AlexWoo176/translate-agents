# Agent: Scrape

**Mô tả:** Đây là Agent đảm nhiệm vai trò kỹ thuật phần mềm (Software Engineer) chuyên về Data Pipeline. Nhiệm vụ của Agent là tự động hóa việc thu thập toàn bộ dữ liệu thô (HTML, hình ảnh) từ giáo trình OpenStax trên nền tảng Web, sau đó tiền xử lý và làm sạch dữ liệu để các Agent khác (Analyze, Translate) có thể đọc hiểu và làm việc dễ dàng mà không bị nhiễu bởi các thẻ HTML rác.

**Giai đoạn hoạt động (Phase):**
Agent này hoạt động chủ yếu ở **Phase 1: Thu thập & Làm sạch dữ liệu (Data Preparation)** trong `master-workflow.md`.

---

## Danh sách Kỹ năng (Skills) và Thứ tự thực thi

Agent Scrape sử dụng chuỗi 2 kỹ năng sau đây một cách tuần tự để hoàn thành nhiệm vụ:

### 1. Kỹ năng Thu thập (Scraping)
- **File:** `[skill-scrape.js](scripts/skill-scrape.js)`
- **Cách sử dụng:**
  - Agent chạy script này để truy cập vào các URL của OpenStax.
  - Script sẽ bóc tách lấy nguyên xi nội dung HTML và toàn bộ hình ảnh đi kèm của chương sách.
  - Kết quả (dữ liệu thô) sẽ được lưu trữ tự động vào thư mục `../[book]/chapter-{N}/01-raw/`.

### 2. Kỹ năng Làm sạch (Cleanup)
- **File:** `[skill-cleanup.js](scripts/skill-cleanup.js)`
- **Cách sử dụng:**
  - Ngay sau khi scrape xong, Agent sẽ chạy script này để quét các file HTML trong thư mục `../[book]/chapter-{N}/01-raw/`.
  - Nhiệm vụ của script là "rửa" sạch HTML: loại bỏ toàn bộ các thẻ rác không cần thiết cho quá trình dịch (như `<head>`, `<script>`, `<style>`, `<nav>`, v.v.).
  - Script cũng tự động cập nhật lại đường dẫn (src) của các hình ảnh trỏ về file ảnh local (offline).
  - Kết quả cuối cùng là HTML tinh gọn được lưu vào thư mục `../[book]/chapter-{N}/02-clean/` — sẵn sàng cho công đoạn phân tích và dịch thuật.
