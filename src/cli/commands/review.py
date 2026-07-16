import os
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass
from datetime import datetime
from src.core.paths import get_book_root, get_clean_dir, get_translated_dir, get_reviews_dir, get_chapter_root
from src.qa.integrity_check import check_file_integrity
from src.qa.glossary_check import load_glossary, check_file_glossary
from src.utils.status_helper import update_status

def run(args):
    """
    Execute review subcommand: validate translations statelessly against selected check.
    """
    book_slug = args.book
    chapter = args.chapter
    
    # Check dependency: translation must be complete
    import json
    chapter_root = get_chapter_root(book_slug, chapter)
    chapter_json_path = chapter_root / "chapter.json"
    if chapter_json_path.is_file():
        try:
            with open(chapter_json_path, "r", encoding="utf-8") as f:
                chapter_data = json.load(f)
            translate_status = chapter_data.get("phases", {}).get("translate", {}).get("status", "")
            if translate_status != "completed":
                print(f"Error: Chapter '{chapter}' translation status is '{translate_status}'. Translation is not complete.")
                return 1
        except Exception as e:
            print(f"Warning: Could not read chapter.json for dependency verification: {e}")

    is_gate = getattr(args, "gate", False)
    if is_gate and not isinstance(is_gate, bool):
        is_gate = False

    is_all = getattr(args, "all", False)
    if is_all and not isinstance(is_all, bool):
        is_all = False

    if is_gate or is_all:
        from src.qa.review_gate import run_review_gate
        print(f"\n============================================================")
        print(f"  RUNNING QA REVIEW GATE: BOOK '{book_slug}' CHAPTER '{chapter}'")
        print(f"============================================================\n")
        exit_code, summary = run_review_gate(book_slug, chapter)
        print("Gate Execution Summary:")
        print(f"  - Structural Integrity: {summary['integrity'].upper()}")
        print(f"  - Glossary Consistency: {summary['glossary'].upper()}")
        print(f"  - Math & Encoding Integrity: {summary['math_encoding'].upper()}")
        print(f"  - Translation Quality QA: {summary['translation_qa'].upper()}")
        print(f"  - Review Gate Status: {summary['review_gate'].upper()}")
        print(f"\nGate report written to: {summary['gate_report']}")

        
        if exit_code == 0:
            update_status(book_slug, chapter, phase="review", status_str="completed", 
                          extra_metadata={"checks": {"integrity": summary["integrity"], "glossary": summary["glossary"], "translation_qa": summary["translation_qa"], "review_gate": summary["review_gate"]}})
        else:
            update_status(book_slug, chapter, phase="review", status_str="failed", error_msg="Review gate failed check(s)",
                          extra_metadata={"checks": {"integrity": summary["integrity"], "glossary": summary["glossary"], "translation_qa": summary["translation_qa"], "review_gate": summary["review_gate"]}})
        return exit_code

    check_type = getattr(args, "check", "integrity")

    clean_dir = get_clean_dir(book_slug, chapter)
    translated_dir = get_translated_dir(book_slug, chapter)
    reviews_dir = get_reviews_dir(book_slug, chapter)

    if not clean_dir.is_dir():
        err_msg = f"Clean directory {clean_dir} does not exist."
        print(f"Error: {err_msg}")
        update_status(book_slug, chapter, phase=f"review_{check_type}", status_str="failed", error_msg=err_msg)
        return 1

    if not translated_dir.is_dir():
        err_msg = f"Translated directory {translated_dir} does not exist."
        print(f"Error: {err_msg}")
        update_status(book_slug, chapter, phase=f"review_{check_type}", status_str="failed", error_msg=err_msg)
        return 1

    clean_files = sorted([f for f in os.listdir(clean_dir) if f.endswith(".html")])
    if not clean_files:
        err_msg = f"No HTML files found in clean directory {clean_dir}."
        print(f"Error: {err_msg}")
        update_status(book_slug, chapter, phase=f"review_{check_type}", status_str="failed", error_msg=err_msg)
        return 1

    if check_type == "integrity":
        exit_code = run_integrity_check(book_slug, chapter, clean_files, clean_dir, translated_dir, reviews_dir)
        if exit_code == 0:
            update_status(book_slug, chapter, phase="review_integrity", status_str="completed")
        else:
            update_status(book_slug, chapter, phase="review_integrity", status_str="failed", error_msg="Integrity check failed")
        return exit_code
    elif check_type == "glossary":
        exit_code = run_glossary_check(book_slug, chapter, clean_files, translated_dir, reviews_dir)
        if exit_code == 0:
            update_status(book_slug, chapter, phase="review_glossary", status_str="completed")
        else:
            update_status(book_slug, chapter, phase="review_glossary", status_str="failed", error_msg="Glossary check failed")
        return exit_code
    else:
        print(f"Error: Check type '{check_type}' is not supported.")
        return 1

def run_integrity_check(book_slug, chapter, clean_files, clean_dir, translated_dir, reviews_dir):
    """
    Performs tag structure and block hierarchy matching reviews.
    """
    print(f"\n============================================================")
    print(f"  INTEGRITY CHECK: BOOK '{book_slug}' CHAPTER '{chapter}'")
    print(f"============================================================\n")

    results = {}
    any_fail = False
    passed_count = 0
    failed_count = 0

    for fname in clean_files:
        clean_path = clean_dir / fname
        trans_path = translated_dir / fname

        print(f"Checking {fname}...")
        res = check_file_integrity(clean_path, trans_path)
        results[fname] = res

        if res["status"] == "PASS":
            print(f"  [PASS]")
            passed_count += 1
        else:
            print(f"  [FAIL]")
            for issue in res["issues"]:
                print(f"    * {issue}")
            failed_count += 1
            any_fail = True

    os.makedirs(reviews_dir, exist_ok=True)
    report_file = reviews_dir / f"chapter-{chapter}-integrity-report.md"

    try:
        report_content = generate_report_markdown(book_slug, chapter, results)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"\nReport written to: {report_file}")
    except Exception as e:
        print(f"Error writing report: {e}")
        return 1

    print("\nSummary:")
    print(f"  - Files passed: {passed_count}")
    print(f"  - Files failed: {failed_count}")

    if any_fail:
        print("\nIntegrity check outcome: FAIL")
        return 1
    else:
        print("\nIntegrity check outcome: PASS")
        return 0

def run_glossary_check(book_slug, chapter, clean_files, translated_dir, reviews_dir):
    """
    Performs terminology consistency reviews matching key mappings.
    """
    glossary_path = get_book_root(book_slug) / "glossary.csv"
    if not glossary_path.is_file():
        print(f"Error: Glossary file '{glossary_path}' does not exist.")
        return 1

    glossary = load_glossary(glossary_path)
    print(f"Loaded {len(glossary)} approved glossary terms.")

    print(f"\n============================================================")
    print(f"  GLOSSARY CHECK: BOOK '{book_slug}' CHAPTER '{chapter}'")
    print(f"============================================================\n")

    results = {}
    any_fail = False
    passed_count = 0
    failed_count = 0

    for fname in clean_files:
        trans_path = translated_dir / fname

        print(f"Checking {fname}...")
        if not trans_path.is_file():
            print(f"  [FAIL] Missing translation file.")
            results[fname] = {
                "status": "FAIL",
                "violations": [{"term": "N/A", "translation": "N/A", "block_id": "N/A", "reason": "Missing translation file"}],
                "detected": []
            }
            failed_count += 1
            any_fail = True
            continue

        res = check_file_glossary(trans_path, glossary)
        results[fname] = res

        if res["status"] == "PASS":
            print(f"  [PASS] Checked {len(res['detected'])} terms.")
            passed_count += 1
        else:
            print(f"  [FAIL] Detected {len(res['violations'])} glossary violations.")
            for violation in res["violations"]:
                print(f"    * {violation['reason']} (Block ID: {violation['block_id']})")
            failed_count += 1
            any_fail = True

            # Write per-file glossary review report
            try:
                os.makedirs(reviews_dir, exist_ok=True)
                file_report_path = reviews_dir / f"{fname.replace('.html', '')}-glossary-review.md"
                file_report_content = generate_file_glossary_report(book_slug, chapter, fname, res)
                with open(file_report_path, "w", encoding="utf-8") as f:
                    f.write(file_report_content)
                print(f"    Report written to: {file_report_path}")
            except Exception as e:
                print(f"    Error writing per-file report: {e}")

    # Write chapter-wide glossary summary report
    try:
        os.makedirs(reviews_dir, exist_ok=True)
        summary_path = reviews_dir / f"chapter-{chapter}-glossary-summary.md"
        summary_content = generate_summary_glossary_report(book_slug, chapter, results)
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary_content)
        print(f"\nConsolidated chapter glossary summary written to: {summary_path}")
    except Exception as e:
        print(f"Error writing chapter summary: {e}")
        return 1

    print("\nSummary:")
    print(f"  - Files passed: {passed_count}")
    print(f"  - Files failed: {failed_count}")

    if any_fail:
        print("\nGlossary check outcome: FAIL")
        return 1
    else:
        print("\nGlossary check outcome: PASS")
        return 0

def generate_report_markdown(book_slug, chapter, results):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Structural Integrity Verification Report: Chapter {chapter}",
        "",
        f"- **Book:** {book_slug}",
        f"- **Verified At:** {timestamp}",
        "",
        "## Overview",
        "",
        "| File Name | Clean Size | Translated Size | Status | Issues Found |",
        "|---|---|---|---|---|",
    ]

    for fname, res in results.items():
        clean_sz = f"{res.get('clean_size', 0) / 1024:.1f} KB" if "clean_size" in res else "-"
        trans_sz = f"{res.get('trans_size', 0) / 1024:.1f} KB" if "trans_size" in res else "-"
        status_str = "✅ PASS" if res["status"] == "PASS" else "❌ FAIL"
        issues_summary = "; ".join(res["issues"]) if res["issues"] else "None"
        
        lines.append(
            f"| `{fname}` | {clean_sz} | {trans_sz} | {status_str} | {issues_summary} |"
        )

    lines.append("")
    lines.append("## Verification Details")
    lines.append("")

    has_failures = False
    for fname, res in results.items():
        if res["status"] != "PASS":
            has_failures = True
            lines.append(f"### `{fname}`")
            lines.append("")
            for issue in res["issues"]:
                lines.append(f"- {issue}")
            lines.append("")

    if not has_failures:
        lines.append("All structural components verified successfully. No failures encountered.")
        lines.append("")

    return "\n".join(lines)

def generate_file_glossary_report(book_slug, chapter, filename, res):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Glossary Consistency Review: {filename}",
        "",
        f"- **Book:** {book_slug}",
        f"- **Chapter:** {chapter}",
        f"- **Checked At:** {timestamp}",
        "",
        "## Violations Found",
        "",
        "| Term | Expected Translation | Block ID | Detail |",
        "|---|---|---|---|",
    ]

    for v in res["violations"]:
        term = v.get("term", "")
        trans = v.get("translation", "")
        bid = v.get("block_id", "")
        reason = v.get("reason", "")
        lines.append(f"| `{term}` | `{trans}` | `{bid}` | {reason} |")

    lines.append("")
    return "\n".join(lines)

def generate_summary_glossary_report(book_slug, chapter, results):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Glossary Review Summary: Chapter {chapter}",
        "",
        f"- **Book:** {book_slug}",
        f"- **Verified At:** {timestamp}",
        "",
        "## Overview",
        "",
        "| File Name | Checked Terms | Violations | Status | Report Link |",
        "|---|---|---|---|---|",
    ]

    for fname, res in results.items():
        checked_terms = len(res.get("detected", []))
        violations = len(res.get("violations", []))
        status_str = "✅ PASS" if res["status"] == "PASS" else "❌ FAIL"
        report_link = f"[{fname.replace('.html', '')}-glossary-review.md](file:///path/to/report)" if violations > 0 else "-"
        
        lines.append(
            f"| `{fname}` | {checked_terms} | {violations} | {status_str} | {report_link} |"
        )

    lines.append("")
    return "\n".join(lines)
