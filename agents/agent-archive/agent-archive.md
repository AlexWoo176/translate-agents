# Agent Archive

## Mô tả chức năng

**Agent-Archive** là agent đảm nhiệm Phase cuối cùng trong dự án dịch thuật sách (theo Master Workflow). Nhiệm vụ chính của agent này là:

1. **Lưu trữ tri thức (Knowledge Base):**
   - Tổng hợp các thuật ngữ mới phát sinh chưa có trong `glossary.csv`.
   - Ghi lại các quyết định về văn phong đặc biệt hoặc cách xử lý văn hóa phương Tây.
   - Ghi chép các pattern lỗi hay gặp để cập nhật vào Knowledge Items (KI).
2. **Đóng gói & Xuất bản (Build & Release):**
   - Tổng hợp và xuất bản ra Web Platform (Preview HTML), PDF, EPUB sau khi hoàn thành quy trình dịch và review.
   - Khởi tạo thư mục `.html` self-contained với đầy đủ css, js (book-reader), hình ảnh (assets) và nội dung (translated html) để có thể host dễ dàng trên các nền tảng như Vercel, GitHub Pages hoặc Netlify.

## Các Scripts

- `scripts/build-preview.py`: Script tự động copy toàn bộ các file cần thiết từ thư mục dự án vào một thư mục gốc `.html`. Cấu trúc của `.html` bảo toàn đường dẫn tương đối để các file HTML không bị lỗi resource. Mở `index.html` trong `.html` sẽ tự động redirect tới bài đọc đầu tiên của Chapter 1.
