# Dự Án Bột

## 1. Giới thiệu

Đây là một dự án phi lợi nhuận mang tên **Bột**. Mục đích của dự án là dịch các tài liệu, sách giáo khoa từ OpenStax (nguồn tài nguyên học liệu mở, miễn phí và hợp pháp) sang tiếng Việt nhằm đảm bảo công bằng và mở rộng cơ hội giáo dục cho mọi người.

Repo `translate-agents` đóng vai trò là **động cơ dịch thuật không trạng thái (Stateless Translation Engine)**, cung cấp các công cụ và tập lệnh để tự động hóa quy trình dịch thuật. Dữ liệu và tiến độ của từng cuốn sách cụ thể sẽ được lưu trữ độc lập tại thư mục dự án song song (ví dụ: `../books/{book}`).

Các cuốn sách đã và đang được triển khai dịch thuật:
1. **[Entrepreneurship](https://openstax.org/books/entrepreneurship/pages/1-2-entrepreneurial-vision-and-goals)** (Dự án khởi điểm)
2. **[Introductory Statistics 2e](https://openstax.org/books/introductory-statistics-2e)** (Dự án hiện tại)

---

## 2. Nguyên tắc cốt lõi

- **Bảo toàn dữ liệu (Data Versioning)**: Mỗi một bước trong pipeline đều phải lưu lại kết quả ở một thư mục riêng biệt. Tuyệt đối không ghi đè dữ liệu của bước trước đó để có thể dễ dàng debug và tái sử dụng.
- **Không trạng thái (Stateless Engine)**: Repo `translate-agents` không chứa tệp tin cấu hình tiến độ (`tasks.md`), bảng thuật ngữ (`glossary.csv`), hoặc các tệp tin HTML thô/dịch của sách. Tất cả tài nguyên này bắt buộc phải nằm ở thư mục của sách (`../books/{book_slug}`).

---

## 3. Kiến trúc Pipeline

```text
[ Scrape ] ---> [ Cleanup ] ---> [ Analysis ] ---> [ Translate ] ---> [ Review ] ---> [ Archive ]
```

Các giai đoạn chi tiết:

### Bước 1: Scrape (`skill-scrape`)
- **Nhiệm vụ**: Thu thập toàn bộ file HTML gốc (bao gồm mọi thẻ rác, JS, CSS) từ trang OpenStax.
- **Dữ liệu đầu ra**: Lưu tại `../books/{book}/raw/`

### Bước 2: Cleanup (`skill-cleanup`)
- **Nhiệm vụ**: Làm sạch file HTML khổng lồ, loại bỏ head, menu, footer, JS, CSS. Chỉ giữ lại phần lõi nội dung (văn bản sách, hình ảnh).
- **Dữ liệu đầu ra**: Lưu tại `../books/{book}/clean/`

### Bước 3: Analysis
- **Nhiệm vụ**: Phân tích HTML đã làm sạch, đánh giá rủi ro văn hóa, thuật ngữ, cấu trúc câu cho từng chương.
- **Dữ liệu đầu ra**: Lưu tại `../books/{book}/chapter-{N}/03-analyzed/` (Markdown báo cáo).

### Bước 4: Translate
- **Nhiệm vụ**: LLM dịch HTML song ngữ dựa trên `glossary.csv` và báo cáo Analysis.
- **Dữ liệu trung gian**: `../books/{book}/chapter-{N}/04-prep/` (HTML sau khi nhân đôi cấu trúc song ngữ, chờ dịch)
- **Dữ liệu đầu ra**: Lưu tại `../books/{book}/chapter-{N}/05-translated/`

### Bước 5: Review
- **Nhiệm vụ**: Hiệu đính, so sánh chéo bản dịch với bản gốc, đảm bảo thuật ngữ đồng nhất.
- **Dữ liệu đầu ra**: Lưu tại `../books/{book}/chapter-{N}/06-reviews/`

### Bước 6: Archive
- **Nhiệm vụ**: Ghép các chunk lại thành file hoàn chỉnh (HTML/PDF) và lưu trữ xuất bản.
- **Dữ liệu đầu ra**: Lưu tại `../books/{book}/chapter-{N}/07-archive/`

---

## 4. Cấu trúc thư mục

Thư mục sách nằm song song với thư mục `translate-agents` (được quản lý dưới dạng thư mục `../books/{book}`):

```text
../books/{book}/                    # vd: introductory-statistics-2e
├── glossary.csv                   # 📌 Bảng thuật ngữ — single source of truth (toàn sách)
├── tasks.md                       # Quản lý tiến độ toàn sách
├── raw/                           # HTML thô sau bước Scrape
├── clean/                         # HTML sạch sau bước Cleanup
├── assets/                        # Hình ảnh của toàn bộ cuốn sách (webp)
├── css/                           # 🎨 CSS dùng chung cho mọi chapter (single file)
│   └── style.css
├── _book-level/                   # Preface, Index, Appendix (không thuộc chapter nào)
│
└── chapter-{N}/                   # vd: chapter-1 ... chapter-13
    ├── 03-analyzed/               # Báo cáo phân tích rủi ro dịch thuật
    ├── 04-prep/                   # HTML đã nhân đôi cấu trúc song ngữ (chờ dịch)
    ├── 05-translated/             # HTML song ngữ đã dịch (eng hidden / vn visible)
    ├── 06-reviews/                # Báo cáo QA / review
    └── 07-archive/                # Sản phẩm cuối cùng
        ├── bilingual/             # Bản song ngữ (HTML/Markdown)
        └── vn-only/               # Bản tiếng Việt thuần (HTML/Markdown)
```

- `/agents/`: Nơi chứa mã nguồn các Agent và các **Skills** (như `skill-scrape`, `skill-cleanup`).
- `/tools/`: Các script tiện ích (build, convert...).
- `/src/`: Mã nguồn cốt lõi của công cụ dịch thuật và bộ kiểm định chất lượng (QA).

---
*Dự án Bột - Vì một nền giáo dục mở và công bằng.*
