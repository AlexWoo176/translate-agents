import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup, Comment
from src.core.paths import get_reviews_dir, get_translated_dir

def parse_review_markdown(file_path):
    """
    Parse a review markdown table.
    Expected columns: ID | Thẻ Gốc | Bản dịch hiện tại | Phản biện | Đề xuất sửa | Trạng thái
    Returns a list of parsed rows and the raw line strings list.
    """
    rows = []
    if not os.path.isfile(file_path):
        return rows, []

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    in_table = False
    for idx, line in enumerate(lines):
        striped = line.strip()
        # Look for table header
        if striped.startswith("| ID |") or striped.startswith("|---"):
            in_table = True
            continue
        
        if in_table and striped.startswith("|"):
            parts = [col.strip() for col in line.split("|")][1:-1]
            if len(parts) >= 6:
                rows.append({
                    "line_idx": idx,
                    "id": parts[0],
                    "the_goc": parts[1].strip("`"),
                    "current": parts[2].strip("`"),
                    "commentary": parts[3].strip("`"),
                    "suggestion": parts[4].strip("`"),
                    "status": parts[5].strip()
                })
        elif in_table and not striped:
            in_table = False

    return rows, lines

def replace_text_in_element(element, old_text, new_text):
    """
    Safely replace old_text with new_text inside the string children of element,
    preserving inline HTML structure tags.
    """
    replaced = False
    for child in element.descendants:
        if isinstance(child, str) and not isinstance(child, Comment):
            if old_text in child:
                new_str = child.replace(old_text, new_text)
                child.replace_with(new_str)
                replaced = True
    return replaced

def extract_target_id(the_goc, row_id):
    """
    Extract element ID candidate from 'the_goc' or row_id.
    """
    # Selector match e.g. p#fs-1234
    match = re.search(r'#([a-zA-Z0-9_\-]+)', the_goc)
    if match:
        return match.group(1)
    
    # Check if the_goc itself is alphanumeric with hyphens
    clean_goc = the_goc.strip()
    if re.match(r'^[a-zA-Z0-9_\-]+$', clean_goc):
        return clean_goc
        
    return None

def apply_review_fixes(book_slug, chapter, review_file_path=None, dry_run=False):
    """
    Orchestrate fix applications for a chapter.
    """
    reviews_dir = get_reviews_dir(book_slug, chapter)
    translated_dir = get_translated_dir(book_slug, chapter)

    if not reviews_dir.is_dir():
        return 1, f"Reviews directory '{reviews_dir}' does not exist."
    if not translated_dir.is_dir():
        return 1, f"Translated HTML directory '{translated_dir}' does not exist."

    # Identify review files to process
    review_files = []
    if review_file_path:
        p = Path(review_file_path)
        if p.is_file():
            review_files.append(p)
        else:
            return 1, f"Specified review file '{review_file_path}' does not exist."
    else:
        # Scan reviews directory for markdown files
        for f in os.listdir(reviews_dir):
            if f.endswith(".md"):
                # Ignore system reports
                if not any(x in f for x in ["-integrity-report", "-glossary-summary", "-review-gate", "-fix-diff"]):
                    review_files.append(reviews_dir / f)

    if not review_files:
        return 0, "No active review markdown files found to process."

    applied_fixes = []
    skipped_fixes = []

    for rfile in review_files:
        # Map review file to HTML file
        # E.g. 01-introduction-semantic-review-round-1.md -> 01-introduction.html
        base_name = rfile.name
        if "-semantic-review-round-" in base_name:
            html_name = base_name.split("-semantic-review-round-")[0] + ".html"
        else:
            html_name = base_name.replace(".md", ".html")
            
        html_path = translated_dir / html_name
        if not html_path.is_file():
            print(f"Warning: Corresponding HTML file '{html_path}' not found for review '{rfile.name}'. Skipping.")
            continue

        # Parse review rows
        rows, md_lines = parse_review_markdown(rfile)
        active_rows = [r for r in rows if r["status"].lower() in ["mới", "yêu cầu sửa lại", "new", "re-review", "open"]]

        if not active_rows:
            continue

        # Read HTML soup
        with open(html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        html_modified = False

        for row in active_rows:
            current_text = row["current"]
            suggestion_text = row["suggestion"]
            the_goc = row["the_goc"]
            row_id = row["id"]

            if not current_text or not suggestion_text:
                skipped_fixes.append({
                    "file": html_name,
                    "row_id": row_id,
                    "the_goc": the_goc,
                    "current": current_text,
                    "suggestion": suggestion_text,
                    "reason": "Empty current text or suggestion"
                })
                continue

            target_id = extract_target_id(the_goc, row_id)
            target_el = None

            # 1. Prefer applying by target id
            if target_id:
                # Find all elements matching target_id or target_id-vn
                candidates = []
                for suffix in ["", "-vn"]:
                    candidate_id = f"{target_id}{suffix}"
                    el = soup.find(id=candidate_id)
                    if el:
                        classes = el.get("class", [])
                        if isinstance(classes, str):
                            classes = classes.split()
                        elif classes is None:
                            classes = []
                        if "vn" in classes and "visible" in classes:
                            candidates.append(el)
                if len(candidates) == 1:
                    target_el = candidates[0]

            # 2. Check and perform replacements
            if target_el:
                # Target element identified by ID
                if replace_text_in_element(target_el, current_text, suggestion_text):
                    html_modified = True
                    applied_fixes.append({
                        "file": html_name,
                        "row_id": row_id,
                        "the_goc": the_goc,
                        "current": current_text,
                        "suggestion": suggestion_text,
                        "mode": "ID match"
                    })
                    # Update status in markdown
                    line_idx = row["line_idx"]
                    parts = md_lines[line_idx].split("|")
                    parts[6] = " Đã sửa "
                    md_lines[line_idx] = "|".join(parts)
                else:
                    skipped_fixes.append({
                        "file": html_name,
                        "row_id": row_id,
                        "the_goc": the_goc,
                        "current": current_text,
                        "suggestion": suggestion_text,
                        "reason": f"Text '{current_text}' not found inside element with ID '{target_el.get('id')}'"
                    })
            else:
                # Fallback: scan all .vn.visible elements
                vn_visible_elements = []
                for el in soup.find_all(class_=lambda x: x and "vn" in x.split() and "visible" in x.split()):
                    if current_text in el.get_text():
                        vn_visible_elements.append(el)

                if len(vn_visible_elements) == 1:
                    # Exactly one element match
                    if replace_text_in_element(vn_visible_elements[0], current_text, suggestion_text):
                        html_modified = True
                        applied_fixes.append({
                            "file": html_name,
                            "row_id": row_id,
                            "the_goc": the_goc,
                            "current": current_text,
                            "suggestion": suggestion_text,
                            "mode": "Text match"
                        })
                        line_idx = row["line_idx"]
                        parts = md_lines[line_idx].split("|")
                        parts[6] = " Đã sửa "
                        md_lines[line_idx] = "|".join(parts)
                    else:
                        skipped_fixes.append({
                            "file": html_name,
                            "row_id": row_id,
                            "the_goc": the_goc,
                            "current": current_text,
                            "suggestion": suggestion_text,
                            "reason": "Text replacement failed inside node"
                        })
                elif len(vn_visible_elements) > 1:
                    skipped_fixes.append({
                        "file": html_name,
                        "row_id": row_id,
                        "the_goc": the_goc,
                        "current": current_text,
                        "suggestion": suggestion_text,
                        "reason": f"Ambiguous: text found in {len(vn_visible_elements)} different .vn.visible blocks"
                    })
                else:
                    skipped_fixes.append({
                        "file": html_name,
                        "row_id": row_id,
                        "the_goc": the_goc,
                        "current": current_text,
                        "suggestion": suggestion_text,
                        "reason": "Current text not found in any .vn.visible block"
                    })

        # Save updates if modified and not dry run
        if html_modified and not dry_run:
            # Create backup file first
            backup_path = html_path.parent / (html_path.name + ".bak")
            shutil.copy2(html_path, backup_path)

            # Save modified HTML
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(str(soup))

            # Save updated review markdown
            with open(rfile, "w", encoding="utf-8") as f:
                f.writelines(md_lines)

    # 3. Generate chapter-N-fix-diff.md
    diff_report_path = reviews_dir / f"chapter-{chapter}-fix-diff.md"
    write_diff_report(diff_report_path, book_slug, chapter, applied_fixes, skipped_fixes, dry_run)

    return 0, {
        "applied": applied_fixes,
        "skipped": skipped_fixes,
        "diff_report": diff_report_path
    }

def write_diff_report(report_path, book_slug, chapter, applied, skipped, dry_run):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    lines = [
        f"# Review Fixes Diff Report: Chapter {chapter}",
        "",
        f"- **Book:** {book_slug}",
        f"- **Applied At:** {timestamp}",
        f"- **Dry Run Mode:** {'Active' if dry_run else 'Inactive'}",
        "",
        "## Applied Fixes Summary",
        "",
        "| File Name | Row ID | Element ID / Selector | Original Text | Suggestion | Mode |",
        "|---|---|---|---|---|---|",
    ]

    for f in applied:
        lines.append(
            f"| `{f['file']}` | {f['row_id']} | `{f['the_goc']}` | `{f['current']}` | `{f['suggestion']}` | {f['mode']} |"
        )

    lines.append("")
    lines.append("## Ambiguous / Skipped Fixes (Not Applied)")
    lines.append("")
    lines.append("| File Name | Row ID | Element ID / Selector | Original Text | Suggestion | Reason |")
    lines.append("|---|---|---|---|---|---|")

    for f in skipped:
        lines.append(
            f"| `{f['file']}` | {f['row_id']} | `{f['the_goc']}` | `{f['current']}` | `{f['suggestion']}` | {f['reason']} |"
        )
    lines.append("")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
