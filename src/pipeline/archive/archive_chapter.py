import os
import json
from pathlib import Path
from src.core.paths import get_chapter_root, get_translated_dir
from src.exporters.export_chapter import export_single_file

def archive_chapter(book_slug: str, chapter, force: bool = False):
    """
    Archive translated chapter files into bilingual and vn-only folders, converting
    HTML pages to HTML, Markdown, and PDF formats. Enforces QA gate checks.
    """
    chapter_root = get_chapter_root(book_slug, chapter)
    translated_dir = get_translated_dir(book_slug, chapter)
    chapter_json_path = chapter_root / "chapter.json"

    chapter_data = {}
    if chapter_json_path.is_file():
        try:
            with open(chapter_json_path, "r", encoding="utf-8") as f:
                chapter_data = json.load(f)
        except Exception:
            pass

    translate_status = chapter_data.get("phases", {}).get("translate", {}).get("status", "")
    if translate_status != "completed" and not force:
        return 1, f"Translation is not complete (translate phase status is '{translate_status}'). Archiving blocked."

    if not translated_dir.is_dir():
        return 1, f"Translated HTML directory '{translated_dir}' does not exist."

    translated_files = sorted([f for f in os.listdir(translated_dir) if f.endswith(".html")])
    if not translated_files:
        return 1, f"No translated HTML files found in '{translated_dir}'."

    qa_section = chapter_data.get("qa", {})
    gate_status = qa_section.get("review_gate", "pending")

    if gate_status != "passed":
        if not force:
            return 1, f"QA review gate is not passed (status is '{gate_status}'). Archiving blocked. Use --force to override."
        else:
            # Record override
            if "qa" not in chapter_data:
                chapter_data["qa"] = {}
            chapter_data["qa"]["review_gate_forced"] = True

    # 2. Execute Exporters
    bil_html_success = True
    bil_md_success = True
    bil_pdf_success = True

    vn_html_success = True
    vn_md_success = True
    vn_pdf_success = True

    pdf_deps_missing = False

    for fname in translated_files:
        source_html = translated_dir / fname
        res = export_single_file(source_html, book_slug, chapter, fname)

        if not res["bilingual"]["html"]:
            bil_html_success = False
        if not res["bilingual"]["md"]:
            bil_md_success = False
        if not res["bilingual"]["pdf"]:
            bil_pdf_success = False
            pdf_deps_missing = True

        if not res["vn-only"]["html"]:
            vn_html_success = False
        if not res["vn-only"]["md"]:
            vn_md_success = False
        if not res["vn-only"]["pdf"]:
            vn_pdf_success = False
            pdf_deps_missing = True

    # 3. Update chapter.json archive details
    if "archive" not in chapter_data:
        chapter_data["archive"] = {}
    if "bilingual" not in chapter_data["archive"]:
        chapter_data["archive"]["bilingual"] = {}
    if "vn-only" not in chapter_data["archive"]:
        chapter_data["archive"]["vn-only"] = {}

    chapter_data["archive"]["bilingual"]["html"] = bil_html_success
    chapter_data["archive"]["bilingual"]["md"] = bil_md_success
    chapter_data["archive"]["bilingual"]["pdf"] = bil_pdf_success

    chapter_data["archive"]["vn-only"]["html"] = vn_html_success
    chapter_data["archive"]["vn-only"]["md"] = vn_md_success
    chapter_data["archive"]["vn-only"]["pdf"] = vn_pdf_success

    try:
        with open(chapter_json_path, "w", encoding="utf-8") as f:
            json.dump(chapter_data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not update chapter.json: {e}")

    warning_msg = ""
    if pdf_deps_missing:
        warning_msg = " Warning: PDF export failed or skipped due to missing system PDF rendering engines (WeasyPrint, pdfkit, or xhtml2pdf)."

    result_summary = {
        "bilingual": {
            "html": bil_html_success,
            "md": bil_md_success,
            "pdf": bil_pdf_success
        },
        "vn-only": {
            "html": vn_html_success,
            "md": vn_md_success,
            "pdf": vn_pdf_success
        },
        "review_gate_forced": chapter_data.get("qa", {}).get("review_gate_forced", False)
    }

    return 0, result_summary
