# Agent Scrape (Thu thập & Làm sạch dữ liệu)

**Agent Scrape** là Agent đầu tiên trong Data Pipeline của dự án **Bột**. Nhiệm vụ chính của Agent này là tương tác với hệ thống website của OpenStax (một Single Page Application), tự động thu thập mã nguồn HTML, tải hình ảnh và làm sạch dữ liệu để chuẩn bị cho quá trình Phân tích (Analysis) và Dịch thuật (Translation) ở các bước sau.

## 📂 Kiến trúc thư mục
Agent Scrape không thực hiện mọi việc trong một file duy nhất mà chia thành các **Skills** (Kỹ năng) riêng biệt để đảm bảo tính module và đáp ứng đúng nguyên tắc *Data Versioning* (không ghi đè dữ liệu).

```text
agents/agent-scrape/
├── package.json
├── README.md
└── skills/
    ├── skill-scrape.js   # Kỹ năng thu thập HTML thô
    └── skill-cleanup.js  # Kỹ năng bóc tách, tải ảnh và chuẩn hoá HTML
```

---

## 🛠 Các Kỹ năng (Skills) của Agent

### 1. Kỹ năng Thu thập ( `skill-scrape.js` )
Mở trình duyệt ẩn (Headless Browser) bằng thư viện `Puppeteer` để vượt qua cơ chế tải trang động (ReactJS) của OpenStax.
- **Nhiệm vụ:**
  - Tự động duyệt qua trang Mục lục (Table of Contents).
  - Trích xuất tất cả các liên kết (links) dẫn đến các chương sách.
  - Truy cập từng chương và tải toàn bộ mã nguồn HTML gốc.
- **Dữ liệu đầu vào:** URL của cuốn sách trên OpenStax.
- **Dữ liệu đầu ra:** Các file HTML thô (raw) lưu tại `../../../data/raw/`.

### 2. Kỹ năng Làm sạch & Quản lý Tài nguyên ( `skill-cleanup.js` )
Sử dụng thư viện `cheerio` và `axios` để xử lý HTML khổng lồ đã thu thập được ở bước 1.
- **Nhiệm vụ:**
  - **Bóc tách nội dung:** Tìm và chỉ trích xuất phần văn bản chính của bài học (trong thẻ `[data-type="page"]`), loại bỏ hoàn toàn các thẻ `<script>`, `<style>`, Header, Menu, Footer rác của hệ thống OpenStax.
  - **Tải Ảnh & Media:** Tự động tìm tất cả thẻ `<img>`, truy xuất URL gốc và tải ảnh về máy tính.
  - **Quy tắc đặt tên Ảnh:** Tự động đổi tên các file ảnh dài dòng thành định dạng chuẩn `img-[chương]-[thứ tự]` (Ví dụ: `img-1-1-1.webp`, `img-1-2-1.jpg`) giúp dễ dàng quản lý theo từng chương.
  - **Chuẩn hoá HTML:** Cập nhật lại thuộc tính `src` của ảnh trỏ về đường dẫn offline (`../assets/`), đồng thời thêm file `style.css` nội bộ để nội dung hiển thị đẹp mắt trên máy tính mà không cần kết nối mạng.
- **Dữ liệu đầu vào:** Các file HTML trong `../../../data/raw/`.
- **Dữ liệu đầu ra:** 
  - File HTML đã làm sạch lưu tại `../../../data/clean/`.
  - Hình ảnh đã đổi tên lưu tại `../../../data/assets/`.

---

## 🚀 Hướng dẫn sử dụng

Vì dự án có thể dịch nhiều sách khác nhau, mọi script đều yêu cầu cung cấp **[tên-sách]** làm tham số để đảm bảo dữ liệu của cuốn sách đó được lưu trong đúng thư mục riêng biệt (`data/[tên-sách]/`).

Cấu trúc thư mục dữ liệu chuẩn của một cuốn sách:
```text
data/[tên-sách]/
  ├── raw/       # Chứa mã nguồn HTML gốc
  ├── clean/     # Chứa nội dung HTML làm sạch + CSS nội bộ
  └── assets/    # Chứa hình ảnh đã được đổi tên chuẩn
```

Yêu cầu đã cài đặt **Node.js** và các thư viện cần thiết (`npm install`).

**Bước 1: Chạy Scrape để lấy HTML gốc**
Lệnh scrape yêu cầu 2 tham số: `[tên-sách]` và `[URL-bắt-đầu]`.
Ví dụ với cuốn *Entrepreneurship*:
```bash
node skills/skill-scrape.js entrepreneurship https://openstax.org/books/entrepreneurship/pages/1-introduction
```

**Bước 2: Chạy Cleanup để tải ảnh và làm sạch rác**
Lệnh cleanup chỉ yêu cầu 1 tham số là `[tên-sách]`:
```bash
node skills/skill-cleanup.js entrepreneurship
```

**Xem thử kết quả cục bộ:**
Bạn có thể khởi tạo một server tĩnh tại thư mục sách (`data/entrepreneurship`) để xem thử offline:
```bash
cd ../../data/entrepreneurship
bunx serve
```
Sau đó truy cập `http://localhost:3000/clean/[tên-file].html` để xem sách đã được làm sạch, định dạng chuẩn và hiển thị đầy đủ hình ảnh.
