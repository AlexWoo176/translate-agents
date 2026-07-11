#!/usr/bin/env python3
"""
integrity-check.py — Kiểm tra tính toàn vẹn của bản dịch.

Đối chiếu file HTML dịch (05-translated) với file gốc sạch (02-clean)
để phát hiện việc dịch thiếu, rút gọn, hoặc lược bỏ nội dung học thuật.

Usage:
    python3 integrity-check.py <chapter-number>
    python3 integrity-check.py 3
    python3 integrity-check.py 3 --dry
    python3 integrity-check.py all
"""

import os
import sys
import re
import argparse
from datetime import datetime
from html.parser import HTMLParser

# ── Config ────────────────────────────────────────────────────────────
def find_project_root():
    """Walk up from this script to find project root (has 'package.json')."""
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.exists(os.path.join(d, "package.json")):
            return d
        d = os.path.dirname(d)
    return None

PROJECT_ROOT = find_project_root()

class TagCounter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = {}
        self.notes_count = 0
        self.eng_hidden_count = {}
        self.vn_visible_count = {}

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self.tags[tag] = self.tags.get(tag, 0) + 1
        
        # Count <div data-type="note">
        if tag == "div" and attrs_dict.get("data-type") == "note":
            self.notes_count += 1
            
        cls = attrs_dict.get("class", "")
        classes = [c.strip() for c in cls.split() if c.strip()]
        if "eng" in classes and "hidden" in classes:
            self.eng_hidden_count[tag] = self.eng_hidden_count.get(tag, 0) + 1
        elif "vn" in classes and "visible" in classes:
            self.vn_visible_count[tag] = self.vn_visible_count.get(tag, 0) + 1

def analyze_html(file_path):
    """Analyze tags, sizes, and structure of an HTML file."""
    if not os.path.isfile(file_path):
        return None
        
    size_bytes = os.path.getsize(file_path)
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    parser = TagCounter()
    parser.feed(content)
    
    # Simple word count (ignoring HTML tags)
    text_only = re.sub(r'<[^>]+>', ' ', content)
    words = [w for w in text_only.split() if w.strip()]
    word_count = len(words)
    
    return {
        "size_bytes": size_bytes,
        "tags": parser.tags,
        "notes_count": parser.notes_count,
        "eng_hidden_count": parser.eng_hidden_count,
        "vn_visible_count": parser.vn_visible_count,
        "word_count": word_count,
    }

def check_file_integrity(clean_path, trans_path):
    """Compare clean vs translated HTML file for integrity issues."""
    clean_stats = analyze_html(clean_path)
    trans_stats = analyze_html(trans_path)
    
    if not clean_stats or not trans_stats:
        return None
        
    size_ratio = trans_stats["size_bytes"] / clean_stats["size_bytes"] if clean_stats["size_bytes"] > 0 else 0
    
    # We expect these blocks to be duplicated as eng hidden and vn visible
    block_tags = ["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "figcaption", "td", "th", "caption"]
    # We expect these to remain singular structural containers
    container_tags = ["section", "div", "figure", "table", "ol", "ul", "aside"]
    
    tag_issues = []
    
    # 1. Check block tags (clean count vs translated eng hidden count)
    for tag in block_tags:
        clean_cnt = clean_stats["tags"].get(tag, 0)
        trans_eng_cnt = trans_stats["eng_hidden_count"].get(tag, 0)
        
        if clean_cnt > 0 and trans_eng_cnt < clean_cnt:
            # Check if there's a significant deficit (> 5% discrepancy or >= 2 blocks missing)
            diff = clean_cnt - trans_eng_cnt
            pct = (diff / clean_cnt) * 100
            if diff >= 2 or pct > 5:
                tag_issues.append({
                    "tag": tag,
                    "clean_count": clean_cnt,
                    "translated_eng_count": trans_eng_cnt,
                    "diff": diff,
                    "pct": pct,
                    "type": "block"
                })
                
    # 2. Check container tags (clean count vs translated overall count)
    for tag in container_tags:
        clean_cnt = clean_stats["tags"].get(tag, 0)
        trans_cnt = trans_stats["tags"].get(tag, 0)
        
        # Div note counts have special treatment
        if tag == "div":
            clean_cnt = clean_stats["notes_count"]
            trans_cnt = trans_stats["notes_count"]
            tag_name = "div (note)"
        else:
            tag_name = tag
            
        if clean_cnt > 0 and trans_cnt < clean_cnt:
            diff = clean_cnt - trans_cnt
            pct = (diff / clean_cnt) * 100
            tag_issues.append({
                "tag": tag_name,
                "clean_count": clean_cnt,
                "translated_eng_count": trans_cnt, # For containers, compare total
                "diff": diff,
                "pct": pct,
                "type": "container"
            })
            
    # Judgment on tag issues only
    if tag_issues:
        status = "FAIL (Thiếu cấu trúc)"
    else:
        status = "PASS"
        
    return {
        "clean_size": clean_stats["size_bytes"],
        "trans_size": trans_stats["size_bytes"],
        "size_ratio": size_ratio,
        "clean_word_count": clean_stats["word_count"],
        "trans_word_count": trans_stats["word_count"],
        "tag_issues": tag_issues,
        "status": status,
        "clean_stats": clean_stats,
        "trans_stats": trans_stats,
    }

def run_chapter(chapter_num, dry_run=False, book="entrepreneurship"):
    data_dir = os.path.abspath(os.path.join(PROJECT_ROOT, "..", book))
    if not os.path.exists(data_dir) and book == "statistics":
        data_dir = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "book-statistics"))
    chapter_dir = os.path.join(data_dir, f"chapter-{chapter_num}")
    clean_dir = os.path.join(chapter_dir, "02-clean")
    trans_dir = os.path.join(chapter_dir, "05-translated")
    out_dir = os.path.join(chapter_dir, "06-reviews")
    
    if not os.path.isdir(clean_dir):
        print(f"⚠️ Không tìm thấy thư mục gốc sạch: {clean_dir}")
        return
        
    if not os.path.isdir(trans_dir):
        print(f"⚠️ Không tìm thấy thư mục bản dịch: {trans_dir}")
        return
        
    clean_files = sorted([f for f in os.listdir(clean_dir) if f.endswith(".html")])
    if not clean_files:
        print(f"⚠️ Không có file HTML trong: {clean_dir}")
        return
        
    print(f"\n{'=' * 60}")
    print(f"  KIỂM TRA TÍNH TOÀN VẸN CHƯƠNG {chapter_num} — {len(clean_files)} files")
    print(f"{'=' * 60}")
    
    results = {}
    any_fail = False
    
    for fname in clean_files:
        clean_path = os.path.join(clean_dir, fname)
        trans_path = os.path.join(trans_dir, fname)
        
        if not os.path.isfile(trans_path):
            print(f"❌ {fname}: Chưa có bản dịch trong 05-translated")
            any_fail = True
            results[fname] = {"status": "MISSING"}
            continue
            
        res = check_file_integrity(clean_path, trans_path)
        results[fname] = res
        
        if "FAIL" in res["status"]:
            any_fail = True
            
        status_symbol = "✅" if "PASS" in res["status"] else ("⚠️" if "WARN" in res["status"] else "❌")
        print(f"  {status_symbol} {fname}: R= {res['size_ratio']:.2f}x | {res['status']}")
        
        for issue in res["tag_issues"]:
            print(f"    - Thiếu tag <{issue['tag']}>: Gốc có {issue['clean_count']}, Dịch có {issue['translated_eng_count']} (thiếu {issue['diff']})")

    # Generate integrity report Markdown
    if not dry_run:
        os.makedirs(out_dir, exist_ok=True)
        report_path = os.path.join(out_dir, f"chapter-{chapter_num}-integrity-report.md")
        
        report_content = generate_markdown_report(chapter_num, results, book)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"\n  📄 Báo cáo lưu tại: {report_path}")
        
    return results

def generate_markdown_report(chapter_num, results, book):
    lines = [
        f"# Báo cáo Kiểm tra Tính toàn vẹn Dịch thuật — Chương {chapter_num}",
        "",
        f"**Thời gian:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Sách:** {book}",
        "",
        "## Bảng tổng quan",
        "",
        "| File | Size Gốc | Size Dịch | Tỉ lệ (Dịch/Gốc) | Tag Thiếu | Trạng thái |",
        "|---|---|---|---|---|---|",
    ]
    
    for fname, res in results.items():
        if res.get("status") == "MISSING":
            lines.append(f"| `{fname}` | — | — | — | — | ❌ CHƯA DỊCH |")
            continue
            
        ratio_str = f"{res['size_ratio']:.2f}×"
        clean_sz = f"{res['clean_size'] / 1024:.1f} KB"
        trans_sz = f"{res['trans_size'] / 1024:.1f} KB"
        
        status_cell = "✅ ĐẠT" if "PASS" in res["status"] else (f"⚠️ CẢNH BÁO" if "WARN" in res["status"] else "❌ THẤT BẠI")
        
        tag_issues_summary = []
        for iss in res["tag_issues"]:
            tag_issues_summary.append(f"<{iss['tag']}> (-{iss['diff']})")
        tag_issues_str = ", ".join(tag_issues_summary) if tag_issues_summary else "Không"
        
        lines.append(f"| `{fname}` | {clean_sz} | {trans_sz} | {ratio_str} | {tag_issues_str} | {status_cell} |")
        
    lines.append("")
    lines.append("## Chi tiết lỗi cấu trúc và nội dung")
    lines.append("")
    
    has_details = False
    for fname, res in results.items():
        if res.get("status") == "MISSING" or not res["tag_issues"]:
            continue
            
        has_details = True
        lines.append(f"### File: `{fname}`")
        lines.append("")
        lines.append("| Tag | Số lượng gốc (02-clean) | Số lượng dịch (eng hidden / total) | Chênh lệch | Mức độ thiếu hụt |")
        lines.append("|---|---|---|---|---|")
        
        for iss in res["tag_issues"]:
            lines.append(f"| `<{iss['tag']}>` | {iss['clean_count']} | {iss['translated_eng_count']} | -{iss['diff']} | {iss['pct']:.1f}% |")
        lines.append("")
        
    if not has_details:
        lines.append("Không phát hiện lỗi cấu trúc lớn ở bất kỳ file nào.")
        lines.append("")
        
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Integrity Check — Đối chiếu tính toàn vẹn cấu trúc dịch")
    parser.add_argument("chapter", help="Số chương cần kiểm tra (ví dụ: 3) hoặc 'all' cho tất cả")
    parser.add_argument("--book", default="entrepreneurship", help="Tên sách")
    parser.add_argument("--dry", action="store_true", help="Chỉ xem kết quả, không ghi file")
    args = parser.parse_args()
    
    data_dir = os.path.abspath(os.path.join(PROJECT_ROOT, "..", args.book))
    if not os.path.exists(data_dir) and args.book == "statistics":
        data_dir = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "book-statistics"))
    
    if args.chapter.lower() == "all":
        chapters = sorted([
            d.replace("chapter-", "")
            for d in os.listdir(data_dir)
            if d.startswith("chapter-") and os.path.isdir(os.path.join(data_dir, d, "02-clean"))
        ])
        for ch in chapters:
            run_chapter(ch, dry_run=args.dry, book=args.book)
    else:
        run_chapter(args.chapter, dry_run=args.dry, book=args.book)

if __name__ == "__main__":
    main()
