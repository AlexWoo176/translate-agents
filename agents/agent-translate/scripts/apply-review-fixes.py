import os
import sys
import re
import argparse

def parse_markdown_table(file_path):
    # Trả về danh sách các hàng trong bảng
    rows = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    in_table = False
    for i, line in enumerate(lines):
        if line.strip().startswith('| ID |') or line.strip().startswith('|---|'):
            in_table = True
            continue
        if in_table and line.strip().startswith('|'):
            # Parse row
            cols = [col.strip() for col in line.split('|')][1:-1] # Bỏ cột rỗng đầu cuối
            if len(cols) >= 9:
                suggestion_raw = cols[6]
                if '`' in suggestion_raw:
                    suggestion = suggestion_raw.split('`')[1]
                else:
                    suggestion = suggestion_raw.replace('Sửa thành:', '').strip()
                
                rows.append({
                    'line_num': i,
                    'id': cols[0],
                    'original': cols[1].strip('`'),
                    'current': cols[3].strip('`'),
                    'position': cols[4].strip('`'),
                    'suggestion': suggestion,
                    'status': cols[8].strip()
                })
        elif in_table and not line.strip():
            in_table = False
            
    return rows, lines


def check_match(html_content, row):
    """Kiểm tra một row có match được trong HTML không. Trả về True/False."""
    current_text = row['current']
    suggestion_text = row['suggestion']
    term_id = row.get('position', '')

    if not current_text or not suggestion_text:
        return False

    if term_id:
        pattern = re.compile(
            rf'(<span[^>]*id="{term_id}"[^>]*>)\s*{re.escape(current_text)}\s*(</span>)'
        )
        matches = list(pattern.finditer(html_content))
        if matches:
            return True

    # Fallback: plain text match
    return current_text in html_content


def apply_fixes(review_path, html_path, dry_run=False):
    if not os.path.exists(review_path):
        print(f"❌ Không tìm thấy file review: {review_path}")
        sys.exit(1)
    if not os.path.exists(html_path):
        print(f"❌ Không tìm thấy file HTML: {html_path}")
        sys.exit(1)

    # 1. Parse review file
    rows, md_lines = parse_markdown_table(review_path)

    # 2. Read HTML
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # ── Lọc ra các rows cần xử lý ─────────────────────────────────────────
    active_rows = [r for r in rows if r['status'].lower() in ['mới', 'yêu cầu sửa lại']]

    if not active_rows:
        print("ℹ️ Không có row nào ở trạng thái 'Mới' hoặc 'Yêu cầu sửa lại'.")
        sys.exit(0)

    # ── Pre-flight: kiểm tra TẤT CẢ rows trước khi ghi bất kỳ gì ────────
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Kiểm tra {len(active_rows)} rows...\n")
    match_results = []
    has_no_match = False

    for row in active_rows:
        matched = check_match(html_content, row)
        status_label = "✅ MATCH" if matched else "❌ NO_MATCH"
        print(f"  {status_label}  [{row['id']}] tìm kiếm: \"{row['current'][:60]}\"")
        match_results.append((row, matched))
        if not matched:
            has_no_match = True

    matched_count = sum(1 for _, m in match_results if m)
    total = len(active_rows)

    # ── Strict: exit 1 nếu bất kỳ row nào NO_MATCH ───────────────────────
    if has_no_match:
        print(f"\n❌ Hủy thao tác: {total - matched_count}/{total} rows KHÔNG tìm thấy text khớp trong HTML.")
        print("   Kiểm tra lại cột 'Bản dịch hiện tại' trong bảng review — text phải khớp chính xác với file HTML.")
        print("   Không có file nào bị thay đổi.")
        sys.exit(1)

    # ── Dry-run: không ghi file ───────────────────────────────────────────
    if dry_run:
        print(f"\nDry-run: {matched_count}/{total} rows sẽ được áp dụng.")
        print("Không có file nào bị thay đổi (--dry-run mode).")
        sys.exit(0)

    # ── Apply: tất cả match, tiến hành ghi ───────────────────────────────
    changes_made = 0
    for row, _ in match_results:
        current_text = row['current']
        suggestion_text = row['suggestion']
        term_id = row.get('position', '')

        replaced = False
        if term_id and current_text and suggestion_text:
            pattern = re.compile(
                rf'(<span[^>]*id="{term_id}"[^>]*>)\s*{re.escape(current_text)}\s*(</span>)'
            )
            matches = list(pattern.finditer(html_content))
            if len(matches) == 2:
                m = matches[1]
                html_content = html_content[:m.start()] + m.group(1) + suggestion_text + m.group(2) + html_content[m.end():]
                replaced = True
            elif len(matches) == 1:
                m = matches[0]
                html_content = html_content[:m.start()] + m.group(1) + suggestion_text + m.group(2) + html_content[m.end():]
                replaced = True

        if not replaced and current_text in html_content and suggestion_text:
            html_content = html_content.replace(current_text, suggestion_text)
            replaced = True

        if replaced:
            # Cập nhật markdown line
            line_idx = row['line_num']
            old_line = md_lines[line_idx]

            # Cập nhật cột response và status
            parts = old_line.split('|')
            if len(parts) >= 10:
                parts[-3] = ' Đồng ý, đã sửa theo đề xuất. '  # Response
                parts[-2] = ' Đã sửa '  # Status
                md_lines[line_idx] = '|'.join(parts)
                changes_made += 1

    # Save HTML
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # Save MD
    with open(review_path, 'w', encoding='utf-8') as f:
        f.writelines(md_lines)

    print(f"\n✅ Đã áp dụng {changes_made}/{total} bản vá vào {os.path.basename(html_path)}")
    print(f"✅ Đã cập nhật trạng thái trong {os.path.basename(review_path)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Áp dụng các bản vá từ file review Markdown vào HTML đã dịch."
    )
    parser.add_argument("review_path", help="Đường dẫn file review .md")
    parser.add_argument("html_path", help="Đường dẫn file HTML cần vá")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ kiểm tra match/no-match, không ghi file nào."
    )
    args = parser.parse_args()
    apply_fixes(args.review_path, args.html_path, dry_run=args.dry_run)
