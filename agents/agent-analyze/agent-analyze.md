# Agent: Analyze

**Mô tả:** Đây là Agent đảm nhiệm vai trò của một Chuyên gia ngôn ngữ học và Giám đốc dự án dịch thuật (Translation Project Manager). Nhiệm vụ của Agent là phân tích chuyên sâu các dữ liệu gốc (HTML sạch) để chuẩn bị "Hành trang dịch thuật" một cách kỹ lưỡng nhất trước khi đưa cho Translate Agent thực thi. Điều này giúp đảm bảo tính nhất quán của thuật ngữ và hạn chế tối đa các sai sót về văn hóa, ngữ cảnh.

**Giai đoạn hoạt động (Phase):**
Agent này hoạt động chủ yếu ở hai giai đoạn:

- **Phase 2: Khởi tạo Hành trang Dịch (Term Extraction)**
- **Phase 3: Phân tích Rủi ro Văn hóa & Ngữ cảnh (Translation Analysis)**

---

## Danh sách Kỹ năng (Skills) và Thứ tự thực thi

Agent Analyze sử dụng chuỗi các kỹ năng sau đây một cách tuần tự để thiết lập tiêu chuẩn dịch thuật cho toàn bộ cuốn sách:

### 1. Kỹ năng Trích xuất Thuật ngữ (Term Extraction)

- **File Prompt:** `[skill-glossary-extraction.md](skills/skill-glossary-extraction.md)`
- **Cách sử dụng:**
  - Ở Phase 2, Agent sử dụng Prompt này quét qua các file HTML đã làm sạch (`../[book]/chapter-{N}/02-clean/`) để nhận diện các từ khóa chuyên ngành, thuật ngữ cốt lõi (ví dụ các từ trong thẻ `<span data-type="term">`).
  - Ghi nhận và đề xuất bản dịch cho các thuật ngữ mới vào file **`../[book]/chapter-{N}/03-analyzed/chapter-{N}-new-terms.csv`**. Bước này giúp con người (Giám đốc dự án) đối chiếu với `glossary.csv` gốc (Single Source of Truth) để bổ sung những từ còn thiếu, từ đó tránh việc tự động ghi đè làm hỏng tệp glossary chuẩn.

### 2. Kỹ năng Phân tích Dịch thuật (Translation Analysis)

- **File Prompt:** `[skill-translation-analysis.md](skills/skill-translation-analysis.md)`
- **Cách sử dụng:**
  - Ở Phase 3, trước khi dịch từng chương, Agent sẽ đọc qua toàn bộ văn bản tiếng Anh của chương đó.
  - Sử dụng Prompt phân tích để đánh giá chuyên sâu 4 khía cạnh: Rủi ro văn hóa, Rủi ro thuật ngữ, Cấu trúc câu, và Văn phong/Giọng điệu.
  - Sinh ra các báo cáo phân tích rủi ro dạng Markdown (ví dụ `[section]-translate-analysis.md`) được lưu vào thư mục **`../[book]/chapter-{N}/03-analyzed/`**. Báo cáo này đóng vai trò như kim chỉ nam bắt buộc để Translate Agent làm theo.
