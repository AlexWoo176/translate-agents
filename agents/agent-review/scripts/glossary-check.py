#!/usr/bin/env python3
"""
glossary-check — Kiểm tra thuật ngữ dịch trong HTML song ngữ.

Đối chiếu tất cả <span data-type="term"> trong file HTML đã dịch
với glossary.csv (Single Source of Truth), xuất báo cáo review
theo chuẩn skill-glossary-check.md của Review Agent.

Usage:
    python3 glossary-check.py <chapter-number>
    python3 glossary-check.py 1          # Chương 1
    python3 glossary-check.py 1 --dry    # Chỉ print, không ghi file
    python3 glossary-check.py all        # Tất cả chapters

Output:
    chapter-N/06-reviews/
    ├── chapter-N-glossary-summary.md
    ├── X-Y-section-name-glossary-review.md  (per file, nếu có issues)
    └── ...

Requires: Python 3.8+ (no external dependencies)
"""

import csv
import re
import os
import sys
import argparse
from datetime import datetime


def find_project_root():
    """Walk up from this script to find project root (has 'package.json')."""
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.exists(os.path.join(d, "package.json")):
            return d
        d = os.path.dirname(d)
    return None


PROJECT_ROOT = find_project_root()

def load_env():
    env = {}
    if PROJECT_ROOT:
        env_path = os.path.join(PROJECT_ROOT, ".env")
        if os.path.isfile(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            env[parts[0].strip()] = parts[1].strip()
    return env

def get_books_root(env):
    books_root = env.get("BOOKS_ROOT", "../books")
    if not os.path.isabs(books_root) and PROJECT_ROOT:
        return os.path.abspath(os.path.join(PROJECT_ROOT, books_root))
    return books_root

ENV = load_env()
BOOKS_ROOT = get_books_root(ENV)
# DATA_DIR will be determined dynamically based on the book argument


# ── 1. Glossary Loader ───────────────────────────────────────────────
def load_glossary(csv_path):
    """Load glossary.csv → dict: key_lower → {translation, options}"""
    glossary = {}
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key_raw = (row.get("key") or row.get("term") or "").strip()
            key = key_raw.lower()
            translation = (row.get("translation") or "").strip()
            options_raw = (row.get("options") or "").strip()
            options = [o.strip().lower() for o in options_raw.split("/") if o.strip()]
            for t in translation.split("/"):
                t_clean = t.strip().lower()
                if t_clean and t_clean not in options:
                    options.append(t_clean)
            if key:
                glossary[key] = {
                    "key_raw": key_raw,
                    "translation": translation,
                    "options": options,
                }
    return glossary


# ── 2. HTML Term Extractor ───────────────────────────────────────────
def strip_html(text):
    """Remove HTML tags."""
    return re.sub(r'<[^>]+>', '', text).strip()


def extract_term_pairs(html):
    """
    Extract eng/vn term pairs from bilingual HTML.
    Finds <span data-type="term"> in eng hidden blocks,
    pairs with same term-id in vn visible blocks.
    """
    term_tag_pattern = re.compile(
        r'<span\s+([^>]*?data-type="term"[^>]*)>(.*?)</span>',
        re.DOTALL | re.IGNORECASE
    )

    term_occurrences = {}

    for match in term_tag_pattern.finditer(html):
        attrs_str = match.group(1)
        inner_text = strip_html(match.group(2)).strip()
        pos = match.start()

        cls = ""
        term_id = ""
        cls_match = re.search(r'class="([^"]*)"', attrs_str)
        id_match = re.search(r'id="([^"]*)"', attrs_str)
        if cls_match:
            cls = cls_match.group(1)
        if id_match:
            term_id = id_match.group(1)

        no_emphasis = "no-emphasis" in cls

        # Determine if in eng hidden or vn visible block
        before = html[max(0, pos - 5000):pos]
        eng_positions = [m.end() for m in re.finditer(r'class="[^"]*eng[^"]*hidden[^"]*"', before)]
        vn_positions = [m.end() for m in re.finditer(r'class="[^"]*vn[^"]*visible[^"]*"', before)]

        last_eng = eng_positions[-1] if eng_positions else -1
        last_vn = vn_positions[-1] if vn_positions else -1

        is_eng = last_eng > last_vn
        is_vn = last_vn > last_eng

        occ = {
            "pos": pos, "text": inner_text,
            "is_eng": is_eng, "is_vn": is_vn,
            "term_id": term_id, "no_emphasis": no_emphasis,
        }

        if term_id:
            term_occurrences.setdefault(term_id, []).append(occ)

    # Pair eng ↔ vn by term_id
    pairs = []
    for term_id, occs in term_occurrences.items():
        eng_occs = [o for o in occs if o["is_eng"]]
        vn_occs = [o for o in occs if o["is_vn"]]

        if eng_occs and vn_occs:
            pairs.append({
                "term_id": term_id,
                "eng_term": eng_occs[0]["text"].lower(),
                "eng_term_raw": eng_occs[0]["text"],
                "vn_term": vn_occs[0]["text"],
                "no_emphasis": eng_occs[0]["no_emphasis"],
            })
        elif eng_occs:
            eng = eng_occs[0]
            vn_text = _find_vn_paragraph_text(html, eng["pos"])
            pairs.append({
                "term_id": term_id,
                "eng_term": eng["text"].lower(),
                "eng_term_raw": eng["text"],
                "vn_term": vn_text,
                "no_emphasis": eng["no_emphasis"],
            })

    return pairs


def _find_vn_paragraph_text(html, eng_pos):
    """Fallback: find VN paragraph text near an eng term."""
    before = html[max(0, eng_pos - 5000):eng_pos]
    id_matches = list(re.finditer(r'id="([^"]*)"', before))
    if not id_matches:
        return ""
    para_id = id_matches[-1].group(1)
    vn_pat = re.compile(
        r'id="' + re.escape(para_id) + r'-vn"[^>]*>(.*?)</(?:p|td|th|li|h[1-6])>',
        re.DOTALL | re.IGNORECASE
    )
    m = vn_pat.search(html)
    return strip_html(m.group(1)) if m else ""


# ── 3. Checker ────────────────────────────────────────────────────────
def check_file(html_path, glossary):
    """Check one HTML file against glossary. Returns (issues, correct, skipped)."""
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    pairs = extract_term_pairs(html)
    issues, correct, skipped = [], [], []

    for pair in pairs:
        eng = pair["eng_term"]
        eng_raw = pair["eng_term_raw"]
        vn = pair["vn_term"]
        term_id = pair["term_id"]

        if pair["no_emphasis"]:
            skipped.append({"eng": eng_raw, "term_id": term_id, "reason": "no-emphasis"})
            continue

        if eng not in glossary:
            skipped.append({"eng": eng_raw, "term_id": term_id, "reason": "không có trong glossary"})
            continue

        gl = glossary[eng]
        expected = gl["translation"]
        options = gl["options"]

        vn_lower = vn.lower()
        matched = any(opt in vn_lower for opt in options)

        entry = {"eng": eng_raw, "expected": expected, "actual": vn, "term_id": term_id}
        if matched:
            correct.append(entry)
        else:
            entry["options"] = " / ".join(gl["options"])
            issues.append(entry)

    return issues, correct, skipped


# ── 4. Report Generator ──────────────────────────────────────────────
def generate_report(filename, chapter_num, issues, correct, skipped, book="entrepreneurship"):
    """Generate glossary review report in standard review-agent format."""
    total = len(issues) + len(correct)
    rate = f"{len(correct)}/{total} = {(len(correct) / total * 100):.0f}%" if total > 0 else "N/A"

    lines = [
        f"# Báo cáo Kiểm tra Thuật ngữ: {filename}",
        "",
        f"**File kiểm tra:** `chapter-{chapter_num}/05-translated/{filename}`",
        f"**File glossary:** `data/{book}/glossary.csv`",
        f"**Thời gian:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Trạng thái Toàn cục:** Đang mở",
        "",
        "## Tổng kết",
        f"- Tổng thuật ngữ glossary xuất hiện trong file: **{total}**",
        f"- Thuật ngữ dịch đúng: **{len(correct)}**",
        f"- Thuật ngữ dịch sai / không nhất quán: **{len(issues)}**",
        f"- Bỏ qua (no-emphasis / không có trong glossary): **{len(skipped)}**",
        f"- Tỉ lệ đúng: **{rate}**",
        "",
    ]

    if issues:
        lines += [
            "## Danh sách Vi phạm",
            "",
            "| ID | Thuật ngữ EN (term_en) | Bản dịch chuẩn (glossary) | Bản dịch hiện tại trong HTML | Vị trí (id thẻ) | Phản biện | Đề xuất sửa | Phản hồi Translate Agent | Trạng thái |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for i, iss in enumerate(issues, 1):
            act = iss["actual"][:80].replace("|", "\\|") if iss["actual"] else "(trống)"
            tid = f'`{iss["term_id"]}`' if iss["term_id"] else ""
            lines.append(
                f'| G-{i:03d} | `{iss["eng"]}` | `{iss["expected"]}` | `{act}` '
                f'| {tid} | Bản dịch không khớp glossary chuẩn '
                f'| Sửa thành: `{iss["expected"]}` | | Mới |'
            )
        lines.append("")

    if correct:
        lines += [
            "## Thuật ngữ dịch đúng (tham khảo)",
            "",
            "| Thuật ngữ EN | Bản dịch chuẩn | Bản dịch trong HTML | Xác nhận |",
            "|---|---|---|---|",
        ]
        for c in correct:
            act_short = c["actual"][:40] if c["actual"] else ""
            lines.append(f'| `{c["eng"]}` | `{c["expected"]}` | `{act_short}` | ✅ |')
        lines.append("")

    if skipped:
        lines += [
            "## Bỏ qua",
            "",
            "| Thuật ngữ | Lý do |",
            "|---|---|",
        ]
        seen = set()
        for s in skipped:
            k = f'{s["eng"]}|{s["reason"]}'
            if k in seen:
                continue
            seen.add(k)
            lines.append(f'| `{s["eng"]}` | {s["reason"]} |')
        lines.append("")

    return "\n".join(lines)


def generate_summary(chapter_num, html_files, file_summaries, totals):
    """Generate consolidated summary report for the chapter."""
    grand_total = totals["issues"] + totals["correct"]
    grand_rate = f'{(totals["correct"] / grand_total * 100):.0f}%' if grand_total > 0 else "N/A"

    lines = [
        f"# Tổng kết Kiểm tra Thuật ngữ — Chương {chapter_num}",
        "",
        f"**Thời gian:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Trạng thái:** Đang mở",
        "",
        "## Tổng quan",
        "",
        "| Hạng mục | Số lượng |",
        "|---|---|",
        f"| Tổng file HTML | {len(html_files)} |",
        f'| Tổng thuật ngữ kiểm tra | {grand_total} |',
        f'| Thuật ngữ dịch đúng | {totals["correct"]} |',
        f'| Thuật ngữ dịch sai | {totals["issues"]} |',
        f'| Bỏ qua | {totals["skipped"]} |',
        f"| **Tỉ lệ đúng** | **{grand_rate}** |",
        "",
        "## Chi tiết theo file",
        "",
        "| File | Tổng | Đúng | Sai | Bỏ qua | Tỉ lệ | Review |",
        "|---|---|---|---|---|---|---|",
    ]
    for fs in file_summaries:
        link = f'[Xem]({fs["file"].replace(".html", "-glossary-review.md")})' if fs["issues"] > 0 else "—"
        lines.append(
            f'| `{fs["file"]}` | {fs["total"]} | {fs["correct"]} '
            f'| {fs["issues"]} | {fs["skipped"]} | {fs["rate"]} | {link} |'
        )
    lines.append("")
    return "\n".join(lines)


# ── 5. Runner ─────────────────────────────────────────────────────────
def run_chapter(chapter_num, glossary, dry_run=False, book="entrepreneurship"):
    data_dir = os.path.join(BOOKS_ROOT, book)
    if not os.path.exists(data_dir):
        # Fallback to sibling directories
        fallback = os.path.abspath(os.path.join(PROJECT_ROOT, "..", book))
        if os.path.exists(fallback):
            data_dir = fallback
        elif book == "statistics":
            stats_fallback = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "book-statistics"))
            if os.path.exists(stats_fallback):
                data_dir = stats_fallback
    chapter_dir = os.path.join(data_dir, f"chapter-{chapter_num}")
    html_dir = os.path.join(chapter_dir, "05-translated")
    out_dir = os.path.join(chapter_dir, "06-reviews")

    if not os.path.isdir(html_dir):
        print(f"⚠️  Không tìm thấy: {html_dir}")
        return

    html_files = sorted([f for f in os.listdir(html_dir) if f.endswith(".html")])
    if not html_files:
        print(f"⚠️  Không có file HTML trong: {html_dir}")
        return

    print(f"\n{'=' * 60}")
    print(f"  CHƯƠNG {chapter_num} — {len(html_files)} files")
    print(f"{'=' * 60}")

    totals = {"issues": 0, "correct": 0, "skipped": 0}
    file_summaries = []

    for fname in html_files:
        html_path = os.path.join(html_dir, fname)
        issues, correct, skipped = check_file(html_path, glossary)

        totals["issues"] += len(issues)
        totals["correct"] += len(correct)
        totals["skipped"] += len(skipped)

        total = len(issues) + len(correct)
        rate = f"{(len(correct) / total * 100):.0f}%" if total > 0 else "N/A"

        file_summaries.append({
            "file": fname, "total": total,
            "correct": len(correct), "issues": len(issues),
            "skipped": len(skipped), "rate": rate,
        })

        status = "✅" if len(issues) == 0 else f"⚠️ {len(issues)} lỗi"
        print(f"  {fname}: {total} terms, {len(correct)} đúng, {len(issues)} sai → {status}")
        for iss in issues:
            print(f"    ❌ {iss['eng']}: '{iss['actual'][:40]}' → chuẩn: '{iss['expected'][:40]}'")

        # Write individual review
        if not dry_run and total > 0:
            os.makedirs(out_dir, exist_ok=True)
            report = generate_report(fname, chapter_num, issues, correct, skipped, book)
            out_path = os.path.join(out_dir, fname.replace(".html", "-glossary-review.md"))
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(report)

    # Write summary
    if not dry_run:
        os.makedirs(out_dir, exist_ok=True)
        summary = generate_summary(chapter_num, html_files, file_summaries, totals)
        summary_path = os.path.join(out_dir, f"chapter-{chapter_num}-glossary-summary.md")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)
        print(f"\n  📄 Saved: {summary_path}")

    grand_total = totals["issues"] + totals["correct"]
    grand_rate = f'{(totals["correct"] / grand_total * 100):.0f}%' if grand_total > 0 else "N/A"
    print(f"\n  Tổng: {grand_total} terms, {totals['correct']} đúng, {totals['issues']} sai → {grand_rate}")

    return totals


# ── 6. Main ───────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Glossary Check — Đối chiếu thuật ngữ dịch với glossary.csv"
    )
    parser.add_argument(
        "chapter",
        help="Số chương cần kiểm tra (ví dụ: 1, 5, preface) hoặc 'all' cho tất cả",
    )
    parser.add_argument(
        "--book", default="entrepreneurship",
        help="Tên sách (mặc định: entrepreneurship)",
    )
    parser.add_argument(
        "--dry", action="store_true",
        help="Chỉ in kết quả, không ghi file review",
    )
    parser.add_argument(
        "--glossary", default=None,
        help="Đường dẫn glossary.csv (mặc định: data/<book>/glossary.csv)",
    )
    args = parser.parse_args()

    data_dir = os.path.join(BOOKS_ROOT, args.book)
    if not os.path.exists(data_dir):
        # Fallback to sibling directories
        fallback = os.path.abspath(os.path.join(PROJECT_ROOT, "..", args.book))
        if os.path.exists(fallback):
            data_dir = fallback
        elif args.book == "statistics":
            stats_fallback = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "book-statistics"))
            if os.path.exists(stats_fallback):
                data_dir = stats_fallback

    csv_path = args.glossary or os.path.join(data_dir, "glossary.csv")
    if not os.path.isfile(csv_path):
        print(f"⚠️ Không tìm thấy glossary: {csv_path}. Sẽ bỏ qua kiểm tra thuật ngữ.")
        glossary = {}
    else:
        glossary = load_glossary(csv_path)
        print(f"✅ Loaded glossary: {len(glossary)} entries")

    if args.chapter.lower() == "all":
        # Find all chapter directories
        chapters = sorted([
            d.replace("chapter-", "")
            for d in os.listdir(data_dir)
            if d.startswith("chapter-") and os.path.isdir(os.path.join(data_dir, d, "05-translated"))
        ])
        if not chapters:
            print("❌ Không tìm thấy chapter nào có 05-translated/")
            sys.exit(1)
        print(f"📁 Tìm thấy {len(chapters)} chapters: {chapters}")
        for ch in chapters:
            run_chapter(ch, glossary, dry_run=args.dry, book=args.book)
    else:
        ch = args.chapter
        run_chapter(ch, glossary, dry_run=args.dry, book=args.book)

    if args.dry:
        print("\n📝 DRY RUN — không ghi file nào.")


if __name__ == "__main__":
    main()
