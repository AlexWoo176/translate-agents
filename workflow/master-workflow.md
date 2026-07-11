# Master Workflow: Dự án Dịch thuật Bột

Đây là sơ đồ và hướng dẫn vận hành toàn bộ quy trình dịch thuật một cuốn sách, với nguyên tắc cốt lõi là **Human-in-the-Loop (Con người kiểm soát - HITL)**.
Các AI Agents sẽ đóng vai trò thực hiện công việc nặng nhọc (Scrape, dịch, thống kê), nhưng **Con người** mới là người ra quyết định tại các điểm mù (blind spots) của AI.

---

## Phase 0: Lên Kế hoạch & Điều phối (Project Planning)

### 🤖 Agent-Plan

- Đóng vai trò là Technical Project Manager (TPM).
- Nhận diện yêu cầu tổng thể của dự án và thiết kế luồng làm việc.
- Sinh ra hoặc cập nhật file `tasks.md` cục bộ tại thư mục từng chương (ví dụ: `../[book]/chapter-{N}/tasks.md`) để phân công việc cụ thể cho từng Agent khác theo định dạng 1-dòng súc tích, tránh việc tải file task tổng lớn gây loãng ngữ cảnh (context drift).
- Đảm bảo tính toán đúng điểm rơi của các trạm kiểm duyệt (đặc biệt là tự động cài cắm `agent-review` sau mỗi task dịch).

### 🛑 Human-in-the-Loop: Duyệt Kế hoạch

- **Nhiệm vụ:** Đọc lướt qua file `tasks.md` cục bộ của chương vừa được sinh ra.
- **Quyết định:** Nếu các task chia đúng luồng và có đủ các chốt QA ➜ Duyệt cho phép hệ thống bắt đầu chạy Phase 1. Nếu thiếu sót ➜ Bổ sung task thủ công hoặc yêu cầu Agent-Plan lập lại.

---

## Phase 1: Thu thập & Làm sạch dữ liệu

### 🤖 Agent-Scrape

- Thu thập toàn bộ file HTML và hình ảnh gốc từ nguồn OpenStax.
- Chạy kỹ năng `skill-cleanup` để lọc thẻ rác (head, script, style, nav) và cập nhật đường dẫn hình ảnh thành local.
- Lưu kết quả vào `../[book]/chapter-{N}/02-clean/`.

### 🛑 Human-in-the-Loop: Kiểm định Data

- **Nhiệm vụ:** Mở ngẫu nhiên vài file HTML trong thư mục `clean`.
- **Câu hỏi ra quyết định:**
  - *HTML đã thực sự sạch sẽ chưa? Còn thẻ rác nào sót lại làm nhiễu AI sau này không?*
  - *Hình ảnh có tải thành công và hiển thị đúng không?*
- **Quyết định:** Nếu OK ➜ Duyệt qua Phase 2. Nếu LỖI ➜ Yêu cầu kỹ sư chỉnh sửa script cleanup.

---

## Phase 2: Khởi tạo Hành trang Dịch (Term Extraction)

### 🤖 Agent-Analyze

- Quét toàn bộ HTML trong `../[book]/chapter-{N}/02-clean/` tìm các thẻ `<span data-type="term">` và các từ khóa học thuật xuất hiện dày đặc.
- Tổng hợp thành file từ điển chuẩn **`glossary.csv`** (nguồn duy nhất — single source of truth). Đặc biệt, **Agent phải tự động đề xuất các phương án dịch (options)** kèm theo giải nghĩa ngữ cảnh cho mỗi thuật ngữ.

### 🛑 Human-in-the-Loop: Chốt Thuật ngữ

- **Nhiệm vụ:** Agent trình bày danh sách các từ khó kèm theo các lựa chọn dịch (Options). Người dùng KHÔNG phải tự gõ nghĩa từ đầu.
- **Tình huống ra quyết định (Ví dụ):**
  - *Thuật ngữ:* "Bootstrapping"
    - [1] Khởi nghiệp tự lực (Dễ hiểu, phổ thông)
    - [2] Khởi nghiệp không gọi vốn (Sát nghĩa tài chính)
    - [3] Giữ nguyên tiếng Anh (Chuyên môn cao)
- **Quyết định:** Con người chỉ việc chọn phương án (hoặc bổ sung nếu chưa ưng ý). Phương án được chọn sẽ chốt cứng vào cột `translation` của **`glossary.csv`**. Toàn bộ quá trình dịch sau này bắt buộc phải theo bảng từ này.

---

## Phase 3: Phân tích Rủi ro Văn hóa (Translation Analysis)

### 🤖 Agent-Analyze

- Quét từng chương sách để đánh giá cấu trúc câu phức tạp, thành ngữ, văn phong, và cách xưng hô.
- Khởi tạo báo cáo `[section]-translate-analysis.md` lưu vào `../[book]/chapter-{N}/03-analyzed/`.

### 🛑 Human-in-the-Loop: Quyết định Văn phong & Ngữ cảnh

- **Nhiệm vụ:** Agent sẽ flag (gắn cờ cảnh báo) các đoạn văn mang đậm tính chất văn hóa phương Tây.
- **Tình huống ra quyết định (Ví dụ):**
  - *Agent hỏi:* Có một câu đùa về văn hóa bóng chày ở Mỹ, dịch sát nghĩa độc giả Việt sẽ không hiểu. Tôi có nên dịch thoát ý không?
  - *Agent hỏi:* Chương này xưng hô "Bạn - Chúng ta" hay "Các em - Thầy cô"?
- **Quyết định:** Con người ghi chú trực tiếp vào file báo cáo Analysis. Translate Agent ở bước sau bắt buộc tuân theo chỉ thị này.

---

## Phase 4: Dịch thuật Song ngữ (Bilingual Translation)

### 🤖 Agent-Translate

- **Hành động 1:** Chạy script `skill-prep-translation.js` để nhân bản các thẻ HTML thành cấu trúc song ngữ — lưu vào `../[book]/chapter-{N}/04-prep/`.
- **Hành động 2:** Đọc **`glossary.csv`** + báo cáo rủi ro trong `../[book]/chapter-{N}/03-analyzed/`. Thực hiện dịch ghi đè văn bản vào các thẻ `vn visible`.
- **Hành động 3:** Đảm bảo dịch đủ các file, bao gồm cả discussion, review question, discuss questions ...etc.
- Lưu kết quả vào `../[book]/chapter-{N}/05-translated/`.

### 🛑 Human-in-the-Loop: Nghỉ ngơi

- Ở bước này, con người **không cần can thiệp**. Quá trình thao tác DOM và dịch thuật HTML hàng chục ngàn dòng sẽ do LLM xử lý 100% để đảm bảo tốc độ tối đa.

---

## Phase 5: Nghiệm thu (Review & QA)

### 🤖 Agent-Review

Thực hiện quy trình kiểm định chất lượng bản dịch (Quality Assurance) theo 3 bước tuần tự:

1. **Kiểm tra tính toàn vẹn (Integrity Check):**
   - Chạy script `python3 agents/agent-review/scripts/integrity-check.py <chapter-number>` để đối chiếu cấu trúc thẻ giữa `02-clean/` và `05-translated/`.
   - **Tiêu chí PASS:** Chỉ cần đảm bảo khớp đủ số lượng thẻ cấu trúc (tags) tương ứng từ bản gốc sạch sang bản dịch (không bị mất thẻ hoặc gộp đoạn văn). Không bắt buộc kiểm tra tỷ lệ dung lượng file.
2. **Kiểm tra thuật ngữ (Glossary Check):**
   - Chạy script `python3 agents/agent-review/scripts/glossary-check.py <chapter-number|all>` để đối chiếu bản dịch với Single Source of Truth (`glossary.csv`).
3. **Phản biện ngữ nghĩa (Semantic Review):**
   - Chạy script `python3 agents/agent-review/scripts/start-review-round.py ../entrepreneurship/chapter-<N>/05-translated/<file>.html` để khởi tạo file báo cáo review ngữ nghĩa `[file]-semantic-review-round-[N].md` trong thư mục `06-reviews/`.
   - Đối chiếu bản dịch với báo cáo rủi ro văn hóa/ngữ cảnh `[section]-translate-analysis.md` trong `03-analyzed/`. Phát hiện các lỗi dịch sai ý, dịch word-by-word vô nghĩa, mất ngữ cảnh văn hóa, xưng hô sai quy ước hoặc lỗi cặp song ngữ không cân bằng.
   - Các lỗi được ghi nhận dưới dạng bảng phản biện. Translate Agent hoặc kỹ sư sẽ chỉnh sửa bản dịch (chỉ chỉnh sửa `vn visible`, giữ nguyên `eng hidden` và các thẻ inline/ID).
   - Áp dụng các thay đổi đã thống nhất trở lại HTML bằng script `python3 agents/agent-translate/scripts/apply-review-fixes.py <review.md> <translated.html>`.

### 🛑 Human-in-the-Loop: Chốt hạ (Final Approval)

- **Nhiệm vụ:** Mở trình duyệt Web, đọc thử file HTML tiếng Việt hoàn chỉnh.
- **Quyết định:** Nếu bản dịch mượt mà, định dạng chuẩn ➜ Nhấn duyệt. Nếu sai sót cục bộ ➜ Tự tay tinh chỉnh phần tiếng Việt. Nếu sai sót hệ thống ➜ Báo lỗi, yêu cầu Translate Agent làm lại chương đó.

---

### 🤖 Agent-Archive

- Sau khi chapter qua vòng Review & QA, **ghi lại kinh nghiệm dịch thuật** của chapter đó vào Knowledge Base:
  - Các thuật ngữ mới phát sinh (chưa có trong `glossary.csv`) → bổ sung thêm row vào CSV.
  - Các quyết định văn phong đặc biệt (cách xưng hô, xử lý văn hóa Mỹ, v.v.) → ghi vào `agents/agent-analyze/translation-standard.md`.
  - Các pattern lỗi hay gặp (eng/vn trùng nội dung, mất thẻ, caption sai thứ tự) → cập nhật vào KI.

> ⚠️ **Chưa triển khai:** Xuất bản ra Web Platform, PDF, EPUB — để dành cho giai đoạn sau khi hoàn thành toàn bộ cuốn sách.

### 🛑 Human-in-the-Loop: Xác nhận lưu trữ

- **Nhiệm vụ:** Kiểm tra nhanh thư mục `archive/` — đủ 2 variant (bilingual + vn-only) và file `reviews/chapter-{N}-review.md` đã đánh dấu hoàn tất.
- **Quyết định:** Đánh dấu hoàn thành toàn bộ công việc trong `tasks.md` cục bộ của chương hiện tại và cập nhật trạng thái tổng quan trong file `tasks.md` gốc tại thư mục sách → chuyển sang chương tiếp theo.
