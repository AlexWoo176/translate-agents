import os
import sys

def parse_glossary_review(file_path):
    rows = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    in_table = False
    for i, line in enumerate(lines):
        if line.strip().startswith('| ID |') or line.strip().startswith('|---|'):
            in_table = True
            continue
        if in_table and line.strip().startswith('|'):
            cols = [col.strip() for col in line.split('|')][1:-1]
            if len(cols) >= 9:
                # col 3: Bản dịch hiện tại
                # col 6: Đề xuất sửa -> Sửa thành: `...`
                current = cols[3].strip('`')
                suggestion_raw = cols[6]
                if 'Sửa thành: `' in suggestion_raw:
                    suggestion = suggestion_raw.split('Sửa thành: `')[1].strip('` ')
                else:
                    suggestion = suggestion_raw.strip('`')
                    
                status = cols[8]
                rows.append({
                    'line_num': i,
                    'current': current,
                    'suggestion': suggestion,
                    'status': status
                })
        elif in_table and not line.strip():
            in_table = False
    return rows, lines

def apply(review_path, html_path):
    rows, md_lines = parse_glossary_review(review_path)
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    changes = 0
    for row in rows:
        if row['status'].lower() == 'mới':
            curr = row['current']
            sugg = row['suggestion']
            if curr in html_content and sugg:
                html_content = html_content.replace(curr, sugg)
                
                parts = md_lines[row['line_num']].split('|')
                parts[-3] = ' Đã sửa theo chuẩn '
                parts[-2] = ' Đã sửa '
                md_lines[row['line_num']] = '|'.join(parts)
                changes += 1
            else:
                print(f"⚠️ Không tìm thấy '{curr}' trong HTML")
                
    if changes > 0:
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        with open(review_path, 'w', encoding='utf-8') as f:
            f.writelines(md_lines)
        print(f"✅ Đã sửa {changes} lỗi trong {os.path.basename(html_path)}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        apply("../entrepreneurship/chapter-6/06-reviews/6-1-problem-solving-to-find-entrepreneurial-solutions-glossary-review.md", "../entrepreneurship/chapter-6/05-translated/6-1-problem-solving-to-find-entrepreneurial-solutions.html")
        apply("../entrepreneurship/chapter-6/06-reviews/6-2-creative-problem-solving-process-glossary-review.md", "../entrepreneurship/chapter-6/05-translated/6-2-creative-problem-solving-process.html")
        apply("../entrepreneurship/chapter-6/06-reviews/6-4-lean-processes-glossary-review.md", "../entrepreneurship/chapter-6/05-translated/6-4-lean-processes.html")
    else:
        apply(sys.argv[1], sys.argv[2])
