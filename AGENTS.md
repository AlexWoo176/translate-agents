# AGENTS.md
- Luôn gọi tôi là bro. 
## Repo Reality

- Trust the scripts under `agents/*/scripts` over the root `README.md`. The README describes a per-chapter pipeline, but the current executable scrape/cleanup flow still writes to `../<book>/raw`, `clean`, and `assets`; later phases operate inside `../entrepreneurship/chapter-*`.
- This repo is effectively single-book today. Multiple automation scripts hardcode `../entrepreneurship` or OpenStax Entrepreneurship URLs: `agents/agent-analyze/scripts/term-extract.js`, `agents/agent-review/scripts/glossary-check.py`, and `agents/agent-scrape/scripts/skill-scrape.js`.
- There is no repo-wide `test`, `lint`, `typecheck`, CI, or formatter config at the root. Verify by running the specific script you changed on a narrow input.

## High-Value Paths

- Source glossary: `../entrepreneurship/glossary.csv`.
- Canonical progress tracker for the book: `../entrepreneurship/tasks.md`.
- Workflow intent: `workflow/master-workflow.md`.
- Translation rules the repo already depends on: `book-reader/skills/skill-translate.md`.

## Commands

- Install root JS dependency set with `bun install` at repo root. Root `package.json` is minimal and matches `bun.lock`.
- Scrape raw OpenStax HTML: `node agents/agent-scrape/scripts/skill-scrape.js entrepreneurship <start-url>`.
- Clean raw HTML and download assets: `node agents/agent-scrape/scripts/skill-cleanup.js entrepreneurship [--force]`. Thêm `--force` nếu `assets/` đã có file (xem Gotchas).
- Extract chapter glossary candidates: `node agents/agent-analyze/scripts/term-extract.js <book-name> <chapter-number>`.
- Prepare one HTML file for bilingual translation: `node agents/agent-translate/scripts/prep_html.js <input-html> <output-html>`.
- Run glossary QA for one chapter or all chapters: `python3 agents/agent-review/scripts/glossary-check.py <chapter-number|all>`.
- Start a new semantic review round for one translated file: `python3 agents/agent-review/scripts/start-review-round.py ../entrepreneurship/chapter-<N>/05-translated/<file>.html`.
- Apply accepted review edits back into HTML: `python3 agents/agent-translate/scripts/apply-review-fixes.py <review.md> <translated.html>`. Dùng `--dry-run` để preview match/no-match trước khi ghi. Script exit 1 nếu bất kỳ row nào không match.
- Export translated HTML to DOCX (skeleton — chưa implement): `node agents/agent-export/scripts/export-docx.js <file|chapter-number|all> [bookName]`. Output goes to `../<bookName>/docx/`.
- Run smoke tests after any script change: `powershell -ExecutionPolicy Bypass -File scripts/smoke-test.ps1`.

## Gotchas

- `skill-cleanup.js` **sẽ từ chối chạy (exit 1)** nếu `assets/` không rỗng và không có flag `--force`. Khi chắc chắn muốn xóa toàn bộ assets: thêm `--force`. Không có cách undo sau khi xóa.
- `skill-scrape.js` accepts a `bookName` argument for output, but its link filter is hardcoded to `https://openstax.org/books/entrepreneurship/pages/`. Reusing it for another book needs code changes.
- `prep_html.js` is file-by-file only; there is no verified chapter-wide wrapper script.
- `apply-review-fixes.py` **exit 1 và không ghi bất kỳ file nào** nếu có row nào trong bảng review không tìm thấy text khớp chính xác trong HTML. Dùng `--dry-run` để kiểm tra match trước.
- `start-review-round.py` chỉ nhận file nằm trong `05-translated/` — truyền path từ thư mục khác sẽ exit 1.
- `agents/agent-archive/scripts/build-preview.py` validates that `book_dir` exists before proceeding. Pass an explicit path: `python3 build-preview.py ../entrepreneurship`.
- `agents/agent-export/scripts/export-docx.js` là **skeleton** — arg validation hoạt động đúng nhưng chưa tạo file DOCX thực tế.
- Lệnh `build` yêu cầu flag `--copy-to-web` nếu muốn copy kết quả biên dịch từ thư mục preview cục bộ `.html` sang thư mục phát hành `web-site` thực tế.

## Working Conventions

- Preserve the repo's append-only review history: semantic review files are round-based in `06-reviews`, created via `start-review-round.py` rather than overwritten.
- For translation edits, keep `eng hidden` blocks untouched and only change `vn visible` content while preserving inline tags and IDs, per `book-reader/skills/skill-translate.md`.
- Chủ động cập nhật tệp `scratch/session_checkpoint.md` song song với `task.md` ngay sau khi hoàn thành mỗi Milestone lớn của dự án, không đợi đến cuối phiên chat hoặc khi có yêu cầu từ bro.


## Token Optimization Protocols

- **Giao thức 1 (Đọc Code):** Chỉ dùng `grep_search` định vị dòng trước, sau đó dùng `view_file` kèm `StartLine` và `EndLine` giới hạn trong khoảng 30-50 dòng. Cấm đọc tệp lớn hơn 100 dòng trực tiếp từ đầu đến cuối.
- **Giao thức 2 (Sửa Code):** Luôn dùng `replace_file_content` hoặc `multi_replace_file_content` để thay thế cục bộ (diff). Nghiêm cấm dùng `write_to_file` để ghi đè (Overwrite) lên các tệp mã nguồn hiện có.
- **Giao thức 3 (Reset Phiên chat):** Khi cuộc hội thoại vượt quá 20 lượt tương tác, Agent bắt buộc phải tạo tệp tóm tắt tiến độ tại `scratch/session_checkpoint.md` và cung cấp prompt hướng dẫn Người dùng khởi động lại phiên chat mới để giải phóng bộ nhớ đệm (context window).

