# Cloudflare Pages — Cấu hình từ `cyberk-io-static`

Tổng hợp toàn bộ cấu hình Cloudflare Pages để áp dụng sang dự án mới.

---

## 1. GitHub Actions — Auto Deploy (`deploy.yml`)

Tạo file `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloudflare Pages

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      deployments: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Deploy to Cloudflare Pages
        uses: cloudflare/pages-action@v1
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          projectName: <TÊN_PROJECT_CLOUDFLARE>   # ← đổi thành tên project mới
          directory: .                              # thư mục deploy (root hoặc dist/)
          branch: ${{ github.ref_name }}
```

### GitHub Secrets cần thiết

Vào **Settings → Secrets and variables → Actions** của repo mới, thêm 2 secret:

| Secret | Lấy ở đâu |
|--------|-----------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare Dashboard → My Profile → API Tokens → Create Token (dùng template "Edit Cloudflare Workers" hoặc custom với quyền Pages) |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Dashboard → bên phải trang Workers & Pages |

---

## 2. HTTP Headers (`_headers`)

Tạo file `_headers` ở root project:

```
/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  X-Robots-Tag: all

/assets/*
  Cache-Control: public, max-age=31536000, immutable

/css/*
  Cache-Control: public, max-age=86400

/js/*
  Cache-Control: public, max-age=86400

/404.html
  X-Robots-Tag: noindex, nofollow
```

**Giải thích:**
- `X-Frame-Options: DENY` — chặn iframe embedding (chống clickjacking)
- `X-Content-Type-Options: nosniff` — chặn MIME sniffing
- `Referrer-Policy` — kiểm soát referrer header
- `Permissions-Policy` — tắt camera/mic/geolocation
- `Cache-Control: immutable` cho assets — cache vĩnh viễn vì tên file có hash
- `Cache-Control: max-age=86400` cho css/js — cache 1 ngày

> [!TIP]
> Điều chỉnh đường dẫn `/assets/*`, `/css/*`, `/js/*` cho phù hợp với cấu trúc thư mục của dự án mới.

---

## 3. Redirects (`_redirects`)

Tạo file `_redirects` ở root project. Dưới đây là **template chung**, bỏ các redirect cụ thể của cyberk-io và thay bằng redirect của dự án mới:

```
# Redirect www về apex domain
https://www.<DOMAIN>.io/* https://<DOMAIN>.io/:splat 301

# Redirect .html extension sang clean URL
/about.html /about 301
/contact.html /contact 301

# Redirect route cũ → mới (ví dụ)
/old-path /new-path 301

# Trang đã xóa → redirect về home
/deprecated-page / 301
```

**Syntax:**
```
<source> <destination> <status_code>
```
- `301` = Permanent redirect (SEO-safe)
- `302` = Temporary redirect
- `:splat` = wildcard — bắt phần còn lại của URL

---

## 4. Cloudflare Ignore (`.cfignore`)

Tạo file `.cfignore` để loại trừ file/thư mục khỏi deployment:

```
# Ignore từ Cloudflare Pages deployment
node_modules/
.wrangler/
README.md
package.json
package-lock.json
# Thêm các thư mục build-tool nếu có
scripts/
docs/
```

> [!NOTE]
> Tương tự `.gitignore` nhưng chỉ áp dụng cho quá trình upload lên Cloudflare Pages. Giúp giảm kích thước deploy và tránh expose file nội bộ.

---

## 5. Checklist áp dụng sang dự án mới

- [ ] Tạo project trên Cloudflare Pages Dashboard (hoặc để GitHub Actions tự tạo lần đầu)
- [ ] Copy 4 file: `deploy.yml`, `_headers`, `_redirects`, `.cfignore`
- [ ] Thay `projectName: cyberk-io` → tên project mới trong `deploy.yml`
- [ ] Đổi domain trong `_redirects` (dòng www redirect)
- [ ] Thêm `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` vào GitHub Secrets
- [ ] Điều chỉnh đường dẫn cache trong `_headers` nếu cấu trúc thư mục khác
- [ ] Cập nhật `.cfignore` theo thư mục của dự án mới
- [ ] Push lên `main` → xem GitHub Actions chạy deploy

---

## 6. Cấu hình Cloudflare Dashboard (không cần code)

Những setting này làm trực tiếp trên Cloudflare Dashboard, không liên quan đến file:

| Setting | Gợi ý |
|---------|-------|
| **Build command** | Để trống (static site) hoặc `npm run build` |
| **Build output directory** | `.` (root) hoặc `dist/`, `out/` |
| **Root directory** | Để trống (mặc định là repo root) |
| **Environment variables** | Thêm nếu dự án cần (ví dụ API keys cho build time) |
| **Custom domain** | Thêm domain sau khi deploy thành công |

