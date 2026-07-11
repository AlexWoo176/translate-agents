# Skill: Term Extraction (Glossary Generation)

**Mô tả:** Đây là Prompt dùng để yêu cầu LLM (như ChatGPT, Claude, hoặc hệ thống AI nội bộ) tự động quét các file văn bản/HTML gốc và trích xuất các thuật ngữ quan trọng để xây dựng tệp `glossary.json` trước khi tiến hành dịch thuật.

---

## Bước 1: Trích xuất tự động (Script)

Trước khi dùng Prompt, hãy chạy script JS để quét HTML tự động và tạo file CSV nháp:

```bash
node agents/agent-analyze/scripts/term-extract.js 1
```

Script này sẽ:
- Quét toàn bộ thẻ `<span data-type="term">` trong `chapter-1/02-clean/`.
- Tự động bỏ qua các tên riêng (`class="no-emphasis"`).
- Xuất file CSV nháp tại `../[book]/chapter-1/03-analyzed/chapter-1-new-glossary.csv`.

## Bước 2: Nhờ LLM dịch (Prompt Template)

Sao chép toàn bộ nội dung bên dưới và gửi cho LLM. Kèm theo file CSV nháp được tạo ra ở Bước 1 để AI dịch những cột còn trống.

***

**Role:** 
Bạn là một chuyên gia ngôn ngữ học và biên dịch viên cấp cao, chuyên dịch sách giáo trình đại học từ tiếng Anh sang tiếng Việt. Bạn đang làm việc trong một dự án chuyển ngữ sách mở (OpenStax).

**Ngữ cảnh dự án:**
Đối tượng độc giả là học sinh, sinh viên Việt Nam tự học, có vốn tiếng Anh hạn chế, học tập trong môi trường kinh phí thấp. Chúng tôi áp dụng quy tắc "Glossary-first" (xây dựng bảng thuật ngữ trước) để đảm bảo tính nhất quán xuyên suốt toàn bộ cuốn sách.

**Nhiệm vụ:**
Dưới đây là bảng thuật ngữ CSV vừa được trích xuất tự động từ chương sách. Nhiệm vụ của bạn là:
1. Đọc lướt nội dung HTML/văn bản của chương (nếu được cung cấp ngữ cảnh) để hiểu bối cảnh.
2. Với những thuật ngữ có trạng thái `"proposal"` (tức là chưa có trong từ điển chuẩn gốc), hãy đề xuất bản dịch tiếng Việt chuẩn xác.
3. TUYỆT ĐỐI dựa vào NGỮ CẢNH của toàn chương, không dịch word-by-word (từng chữ một).
4. Các dòng có trạng thái `"approved"` hoặc có ghi chú `"Tên riêng"` thì GIỮ NGUYÊN, không được tự ý sửa bản dịch.
5. Tuân thủ các quy tắc thuật ngữ:
   - Giữ nguyên các từ tiếng Anh đã phổ biến rộng rãi tại Việt Nam (vd: SMART Goals, Business Model Canvas, Brainstorming).
   - Đảm bảo tính học thuật nhưng văn phong phải thực tế, không dùng từ ngữ quá cổ kính hay xa lạ.
6. **Bổ sung chú thích (desc_vi/desc_en) cho Tên riêng & Thuật ngữ đặc thù:** Đối với các từ là Tên riêng (thương hiệu, tên tổ chức, v.v.) hoặc các thuật ngữ khó (ví dụ: *Amazon Mom*), BẮT BUỘC phải viết tóm tắt giải thích đối tượng đó là gì vào cột `desc_vi` (Ví dụ: "một chương trình thành viên của Amazon dành cho phụ huynh"). Điều này giúp các Agent sau này dịch chuẩn xác bối cảnh.

**Định dạng đầu ra:**
Bạn CHỈ ĐƯỢC PHÉP trả về nội dung dưới định dạng CSV (không kèm theo lời giải thích nào khác ngoài CSV, bọc trong markdown block ` ```csv `). 
Cấu trúc yêu cầu như sau:
```csv
key,translation,options,desc_en,desc_vi,chapter,status,notes
"thuật ngữ gốc","bản dịch chuẩn","phương án 1 / phương án 2","Mô tả tiếng Anh (nếu có)","Mô tả tiếng Việt (nếu có)","X","proposal",""
"entrepreneurial mindset","tư duy khởi nghiệp","","","","1","approved",""
```
**Lưu ý:**
- Chỉ thay đổi cột `translation` và `options` (nếu có nhiều lựa chọn) đối với các từ mang status `"proposal"`.
- Trả về toàn bộ danh sách CSV đầy đủ để tôi dễ dàng đối chiếu.

**Nội dung CSV cần dịch thuật:**

[👇 CHÈN NỘI DUNG FILE `chapter-N-new-glossary.csv` VÀO ĐÂY 👇]
