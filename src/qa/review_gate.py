import os
import json
from datetime import datetime
from pathlib import Path
from src.core.paths import get_book_root, get_chapter_root, get_clean_dir, get_translated_dir, get_reviews_dir
from src.qa.integrity_check import check_file_integrity
from src.qa.glossary_check import load_glossary, check_file_glossary

def run_review_gate(book_slug, chapter):
    """
    Execute integrity and glossary QA checks, update chapter.json metadata, and write
    consolidated gate report. Returns (exit_code, summary_dict).
    """
    clean_dir = get_clean_dir(book_slug, chapter)
    translated_dir = get_translated_dir(book_slug, chapter)
    reviews_dir = get_reviews_dir(book_slug, chapter)
    glossary_path = get_book_root(book_slug) / "glossary.csv"
    chapter_json_path = get_chapter_root(book_slug, chapter) / "chapter.json"

    # Ensure directories
    os.makedirs(reviews_dir, exist_ok=True)

    clean_files = []
    if clean_dir.is_dir():
        clean_files = sorted([f for f in os.listdir(clean_dir) if f.endswith(".html")])

    # 1. Evaluate inputs
    has_clean = len(clean_files) > 0
    has_translated = translated_dir.is_dir() and len(os.listdir(translated_dir)) > 0
    has_glossary = glossary_path.is_file()

    # 2. Run Integrity Checks
    integrity_status = "pending"
    integrity_failures = []
    
    if not has_clean or not translated_dir.is_dir():
        integrity_status = "pending"
    else:
        all_integrity_pass = True
        for fname in clean_files:
            clean_path = clean_dir / fname
            trans_path = translated_dir / fname
            res = check_file_integrity(clean_path, trans_path)
            if res["status"] != "PASS":
                all_integrity_pass = False
                integrity_failures.append({
                    "file": fname,
                    "issues": res.get("issues", [])
                })
        integrity_status = "passed" if all_integrity_pass else "failed"

    # 3. Run Glossary Checks
    glossary_status = "pending"
    glossary_failures = []

    if not has_glossary or not has_clean or not translated_dir.is_dir():
        glossary_status = "pending"
    else:
        glossary = load_glossary(glossary_path)
        all_glossary_pass = True
        for fname in clean_files:
            trans_path = translated_dir / fname
            if not trans_path.is_file():
                all_glossary_pass = False
                glossary_failures.append({
                    "file": fname,
                    "violations": [{"reason": "Missing translated file"}]
                })
                continue

            res = check_file_glossary(trans_path, glossary)
            if res["status"] != "PASS":
                all_glossary_pass = False
                glossary_failures.append({
                    "file": fname,
                    "violations": res.get("violations", [])
                })
        glossary_status = "passed" if all_glossary_pass else "failed"

    # 4. Run Math/Encoding Checks
    math_encoding_status = "pending"
    math_encoding_failures = []
    
    if not has_clean or not translated_dir.is_dir():
        math_encoding_status = "pending"
    else:
        from src.qa.math_encoding_qa import run_math_encoding_qa
        all_math_pass = True
        for fname in clean_files:
            trans_path = translated_dir / fname
            if not trans_path.is_file():
                all_math_pass = False
                math_encoding_failures.append({
                    "file": fname,
                    "issues": ["Missing translated file"]
                })
                continue
            res = run_math_encoding_qa(trans_path)
            if res["status"] != "PASS":
                all_math_pass = False
                math_encoding_failures.append({
                    "file": fname,
                    "issues": res.get("issues", [])
                })
        math_encoding_status = "passed" if all_math_pass else "failed"

    # 5. Run Translation Quality Checks
    translation_qa_status = "pending"
    translation_qa_failures = []
    
    if not has_clean or not translated_dir.is_dir():
        translation_qa_status = "pending"
    else:
        from src.qa.translation_qa import check_file_translation_qa
        all_trans_qa_pass = True
        for fname in clean_files:
            trans_path = translated_dir / fname
            if not trans_path.is_file():
                all_trans_qa_pass = False
                translation_qa_failures.append({
                    "file": fname,
                    "issues": ["Missing translated file"]
                })
                continue
            res = check_file_translation_qa(trans_path)
            if res["status"] != "PASS":
                all_trans_qa_pass = False
                translation_qa_failures.append({
                    "file": fname,
                    "issues": res.get("issues", [])
                })
        translation_qa_status = "passed" if all_trans_qa_pass else "failed"

    # 6. Determine overall Gate status
    if (integrity_status == "failed" or glossary_status == "failed" or 
        math_encoding_status == "failed" or translation_qa_status == "failed"):
        gate_status = "failed"
    elif (integrity_status == "pending" or glossary_status == "pending" or 
          math_encoding_status == "pending" or translation_qa_status == "pending"):
        gate_status = "pending"
    else:
        gate_status = "passed"

    # 7. Write chapter-N-review-gate.md
    gate_report_path = reviews_dir / f"chapter-{chapter}-review-gate.md"
    write_gate_report(
        gate_report_path, book_slug, chapter, gate_status, 
        integrity_status, glossary_status, math_encoding_status, translation_qa_status,
        integrity_failures, glossary_failures, math_encoding_failures, translation_qa_failures
    )

    # 8. Update chapter.json
    update_chapter_json(chapter_json_path, integrity_status, glossary_status, math_encoding_status, translation_qa_status, gate_status)

    exit_code = 0 if gate_status == "passed" else 1

    return exit_code, {
        "integrity": integrity_status,
        "glossary": glossary_status,
        "math_encoding": math_encoding_status,
        "translation_qa": translation_qa_status,
        "review_gate": gate_status,
        "gate_report": gate_report_path
    }

def write_gate_report(
    report_path, book_slug, chapter, gate_status, 
    integrity_status, glossary_status, math_encoding_status, translation_qa_status,
    integrity_failures, glossary_failures, math_encoding_failures, translation_qa_failures
):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    status_emoji = "✅ PASSED" if gate_status == "passed" else ("❌ FAILED" if gate_status == "failed" else "⚠️ PENDING")
    
    lines = [
        f"# QA Review Gate Report: Chapter {chapter}",
        "",
        f"- **Book:** {book_slug}",
        f"- **Gate Status:** {status_emoji}",
        f"- **Verified At:** {timestamp}",
        "",
        "## Checkers Status",
        "",
        f"- **Structural Integrity:** {integrity_status.upper()}",
        f"- **Glossary Consistency:** {glossary_status.upper()}",
        f"- **Math & Encoding Integrity:** {math_encoding_status.upper()}",
        f"- **Translation Quality QA:** {translation_qa_status.upper()}",
        "",
    ]

    if integrity_failures:
        lines.append("## Structural Integrity Failures Details")
        lines.append("")
        for f in integrity_failures:
            lines.append(f"### File: `{f['file']}`")
            for issue in f["issues"]:
                lines.append(f"- {issue}")
            lines.append("")

    if glossary_failures:
        lines.append("## Glossary Consistency Violations Details")
        lines.append("")
        for f in glossary_failures:
            lines.append(f"### File: `{f['file']}`")
            for v in f["violations"]:
                lines.append(f"- {v.get('reason', 'Unknown error')}")
            lines.append("")

    if math_encoding_failures:
        lines.append("## Math & Encoding Integrity Failures Details")
        lines.append("")
        for f in math_encoding_failures:
            lines.append(f"### File: `{f['file']}`")
            for issue in f["issues"]:
                lines.append(f"- {issue}")
            lines.append("")

    if translation_qa_failures:
        lines.append("## Translation Quality QA Failures Details")
        lines.append("")
        for f in translation_qa_failures:
            lines.append(f"### File: `{f['file']}`")
            for issue in f["issues"]:
                lines.append(f"- {issue}")
            lines.append("")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def update_chapter_json(json_path, integrity_status, glossary_status, math_encoding_status, translation_qa_status, gate_status):
    if not json_path.is_file():
        chapter_data = {}
    else:
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                chapter_data = json.load(f)
        except Exception:
            chapter_data = {}

    if "qa" not in chapter_data:
        chapter_data["qa"] = {}

    chapter_data["qa"]["integrity"] = integrity_status
    chapter_data["qa"]["glossary"] = glossary_status
    chapter_data["qa"]["math_encoding"] = math_encoding_status
    chapter_data["qa"]["translation_qa"] = translation_qa_status
    chapter_data["qa"]["review_gate"] = gate_status

    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(chapter_data, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to write updates to chapter.json: {e}")

