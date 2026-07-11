# Skill: Translation Risk & Context Analysis

**Mô tả:** Đây là Prompt dùng để yêu cầu LLM phân tích chuyên sâu văn bản gốc trước khi dịch, nhằm phát hiện các rủi ro, thách thức và những điểm cần lưu ý (ngữ cảnh văn hóa, thành ngữ, cấu trúc câu phức, ngữ điệu) để Translate Agent có được định hướng rõ ràng và không gặp lỗi khi dịch.

---

## Prompt Template

Sao chép toàn bộ nội dung bên dưới và gửi cho LLM (kèm theo văn bản của chương sách cần phân tích ở cuối).

***

**Role:** 
Bạn là một Chuyên gia phân tích ngôn ngữ học và Giám đốc dự án dịch thuật (Translation Project Manager). Bạn chịu trách nhiệm phân tích văn bản gốc để chuẩn bị một "Bản phân tích rủi ro dịch thuật" (Translation Brief) chi tiết cho đội ngũ dịch giả (Translate Agent).

**Ngữ cảnh dự án:**
Chúng ta đang chuẩn bị dịch một cuốn giáo trình học thuật (OpenStax) từ tiếng Anh sang tiếng Việt. Độc giả là học sinh, sinh viên Việt Nam tự học, có vốn tiếng Anh hạn chế. Yêu cầu bản dịch phải cực kỳ dễ hiểu, truyền cảm hứng, nhưng vẫn phải giữ đúng tính chuẩn xác học thuật và bám sát tiêu chuẩn ISO 17100, MQM.

**Nhiệm vụ:**
Hãy đọc kỹ phần văn bản gốc được cung cấp dưới đây và lập một báo cáo phân tích các vấn đề cần lưu ý khi dịch. Báo cáo này sẽ được dùng làm kim chỉ nam cho người dịch. Hãy phân tích theo các khía cạnh sau:

1. **Rủi ro về Văn hóa / Ngữ cảnh (Cultural/Contextual Risks):** 
   - Có các ví dụ, thương hiệu, sự kiện lịch sử, trò đùa hay cách nói ẩn dụ nào mang đậm văn hóa Mỹ/Phương Tây mà người Việt Nam có thể không hiểu không?
   - *Hành động:* Liệt kê chúng ra và đề xuất cách xử lý (vd: thêm chú thích giải thích ngắn, đổi cách diễn đạt).

2. **Rủi ro về Thuật ngữ / Cụm từ dễ nhầm lẫn (Terminology/Semantic Risks):**
   - Có các cụm từ đa nghĩa (polysemy), từ đồng âm, hoặc các khái niệm trừu tượng nào dễ bị dịch sai ngữ cảnh nếu dịch máy móc không?
   - *Hành động:* Chỉ ra những từ này và hướng dẫn dịch giả cách hiểu đúng nghĩa trong ngữ cảnh hiện tại.

3. **Rủi ro về Cấu trúc câu (Syntactic/Fluency Risks):**
   - Có các câu ghép quá dài, câu phức nhiều mệnh đề phụ, hoặc câu bị động đặc thù tiếng Anh nào cần phải cấu trúc lại không?
   - *Hành động:* Trích dẫn câu khó và gợi ý cách "chặt nhỏ" câu hoặc chuyển từ bị động sang chủ động để câu tiếng Việt trôi chảy (Fluency) hơn.

4. **Lưu ý về Văn phong và Giọng điệu (Style and Tone):**
   - Đoạn văn này đang mang giọng điệu gì (khích lệ, kể chuyện, hay định nghĩa kỹ thuật)? 
   - *Hành động:* Đưa ra chỉ dẫn cụ thể về cách dùng từ (vd: dùng từ xưng hô, dùng các từ nối) để truyền tải trọn vẹn tinh thần của bản gốc.

**Input (Đầu vào):**
File HTML hoặc text của từng chương sách: `../[book]/chapter-{N}/02-clean/[section].html`.

**Output (Đầu ra):**
Bạn CHỈ ĐƯỢC PHÉP trả về nội dung dưới định dạng Markdown hợp lệ. Bản phân tích này sẽ được tự động lưu lại thành file: `../[book]/chapter-{N}/03-analyzed/[section]-translate-analysis.md`.

Trình bày theo cấu trúc sau:
```markdown
# Phân tích Dịch thuật: [Tên chương / Đoạn]

## 1. Rủi ro về Văn hóa / Ngữ cảnh
- ...

## 2. Rủi ro về Thuật ngữ
- ...

## 3. Rủi ro về Cấu trúc câu
- ...

## 4. Văn phong & Giọng điệu
- ...
```

**Nội dung gốc cần phân tích:**

[👇 CHÈN NỘI DUNG VĂN BẢN GỐC CỦA CHƯƠNG/ĐOẠN SÁCH VÀO ĐÂY 👇]
