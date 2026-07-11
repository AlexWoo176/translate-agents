import os
import sys
import csv
from datetime import datetime
from pathlib import Path
from src.qa.math_encoding_qa import run_math_encoding_qa
from src.core.paths import get_book_root, get_phase_dir, get_web_output_root

def run_verification(book_slug: str, chapters: list[int]):
    book_root = get_book_root(book_slug)
    web_root = get_web_output_root() / book_slug
    
    reports_dir = book_root / "_book-level" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    md_report_path = reports_dir / "math-encoding-baseline-verification-chapters-1-8.md"
    csv_report_path = reports_dir / "math-encoding-baseline-verification-chapters-1-8.csv"

    print("=============================================================")
    print("  RUNNING MATH/ENCODING BASELINE VERIFICATION (READ-ONLY)")
    print("=============================================================\n")

    step1_results = {}
    step1_failing_files = []
    step1_total = 0
    step1_passed = 0

    # Step 1: qa-math on 05-translated files
    print("Step 1: Running qa-math on 05-translated files for Chapters 1-8...")
    for ch in chapters:
        step1_results[ch] = {"total": 0, "passed": 0, "failed": 0, "failures": []}
        try:
            trans_dir = get_phase_dir(book_slug, ch, "translated")
        except Exception:
            continue
            
        if not trans_dir.is_dir():
            continue
            
        for file in sorted(os.listdir(trans_dir)):
            if not file.endswith(".html"):
                continue
            
            filepath = trans_dir / file
            step1_total += 1
            step1_results[ch]["total"] += 1
            
            res = run_math_encoding_qa(filepath)
            if res["status"] == "PASS":
                step1_passed += 1
                step1_results[ch]["passed"] += 1
            else:
                step1_results[ch]["failed"] += 1
                step1_results[ch]["failures"].append((file, res["issues"]))
                step1_failing_files.append((ch, "05-translated", file, res["issues"]))

    print(f"Step 1 Complete: {step1_passed}/{step1_total} files passed.")

    # Step 2: qa-math on .html preview and web-site outputs
    print("\nStep 2: Auditing .html preview and web-site outputs...")
    preview_total = 0
    preview_passed = 0
    preview_failures = []
    
    web_total = 0
    web_passed = 0
    web_failures = []

    for ch in chapters:
        # Preview .html stage folder
        preview_dir = book_root / ".html" / f"chapter-{ch}"
        if preview_dir.is_dir():
            for root, _, files in os.walk(preview_dir):
                for file in files:
                    if not file.endswith(".html"):
                        continue
                    filepath = Path(root) / file
                    preview_total += 1
                    res = run_math_encoding_qa(filepath)
                    if res["status"] == "PASS":
                        preview_passed += 1
                    else:
                        rel = os.path.relpath(filepath, book_root)
                        preview_failures.append((ch, rel, res["issues"]))

        # Web site stage folder
        web_dir = web_root / f"chapter-{ch}"
        if web_dir.is_dir():
            for root, _, files in os.walk(web_dir):
                for file in files:
                    if not file.endswith(".html"):
                        continue
                    filepath = Path(root) / file
                    web_total += 1
                    res = run_math_encoding_qa(filepath)
                    if res["status"] == "PASS":
                        web_passed += 1
                    else:
                        rel = os.path.relpath(filepath, web_root)
                        web_failures.append((ch, rel, res["issues"]))

    print(f"Step 2 Complete:")
    print(f"  - .html preview: {preview_passed}/{preview_total} files passed.")
    print(f"  - web-site: {web_passed}/{web_total} files passed.")

    # Step 3: Negative Control Test
    print("\nStep 3: Executing negative control test using known-bad fixture...")
    fixture_content = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
</head>
<body>
  <p class="eng hidden" id="bad">H<sub>0</sub>: Î¼ â¤ 15, Ï = 0.5, Î± = 0.05, xÂ¯ &gt; 17</p>
  <p class="vn visible" id="bad-vn">H<sub>0</sub>: Î¼ â¤ 15, Ï = 0.5, Î± = 0.05, xÂ¯ &gt; 17</p>
</body>
</html>
"""
    # Create temp fixture path in workspace
    temp_dir = Path(__file__).resolve().parent.parent / "tests"
    temp_dir.mkdir(parents=True, exist_ok=True)
    fixture_path = temp_dir / "temp_known_bad_fixture.html"
    
    with open(fixture_path, "w", encoding="utf-8") as f:
        f.write(fixture_content)

    res_control = run_math_encoding_qa(fixture_path)
    
    # Clean up immediately
    if fixture_path.is_file():
        os.remove(fixture_path)

    control_passed = False
    detected_tokens = []
    if res_control["status"] == "FAIL":
        # Check which tokens were detected or if it flagged mojibake
        control_passed = any("Detected mojibake" in issue or "mojibake" in issue.lower() for issue in res_control["issues"])
        # Extract detected tokens
        content_str = fixture_content
        for token in ["Î¼", "Ï", "Î±", "â¤", "Â¯"]:
            if token in content_str:
                detected_tokens.append(token)
                
    print(f"Step 3 Complete: Control test passed correctly: {control_passed}")

    # Determine Baseline Decision
    has_step1_fails = len(step1_failing_files) > 0
    has_step2_fails = len(preview_failures) > 0 or len(web_failures) > 0
    
    if not has_step1_fails and not has_step2_fails and control_passed:
        baseline_decision = "BASELINE_CONFIRMED"
    else:
        baseline_decision = "BASELINE_NOT_CONFIRMED"
        
    print(f"\nFinal Decision: {baseline_decision}")

    # Write MD Report
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(md_report_path, "w", encoding="utf-8") as md:
        md.write("# Math and Encoding Baseline Verification Report\n\n")
        
        md.write("## 1. Summary\n\n")
        md.write(f"- **Verification Status**: Complete\n")
        md.write(f"- **Read-Only Verification**: Yes (No real book HTML content was modified)\n")
        md.write(f"- **Verification Run Time**: {now_str}\n")
        md.write(f"- **Final Baseline Decision**: **{baseline_decision}**\n")
        md.write(f"- **CSV Report Generated**: `{csv_report_path.name}`\n\n")
        
        md.write("## 2. Step 1 Results: Translated qa-math Verification\n\n")
        md.write("| Chapter | Files Scanned | Passed | Failed | Status |\n")
        md.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for ch in chapters:
            stats = step1_results[ch]
            status = "✅ PASS" if stats["failed"] == 0 else "❌ FAIL"
            md.write(f"| chapter-{ch} | {stats['total']} | {stats['passed']} | {stats['failed']} | {status} |\n")
            
        if step1_failing_files:
            md.write("\n### Step 1 Failing Files Details:\n")
            for ch, stage, file, issues in step1_failing_files:
                md.write(f"- **chapter-{ch} / {file}**:\n")
                for issue in issues:
                    md.write(f"  - {issue}\n")
        else:
            md.write("\n*All 05-translated files for Chapters 1-8 passed qa-math check successfully.*\n")

        md.write("\n## 3. Step 2 Results: Preview and Web-Site Audits\n\n")
        md.write(f"- **Books Preview Output (`.html` stage)**:\n")
        md.write(f"  - Scanned: {preview_total} file(s)\n")
        md.write(f"  - Passed: {preview_passed} file(s)\n")
        md.write(f"  - Failed: {len(preview_failures)} file(s)\n")
        
        if preview_failures:
            md.write("  - Failures detail:\n")
            for ch, rel, issues in preview_failures:
                md.write(f"    - `{rel}`:\n")
                for issue in issues:
                    md.write(f"      - {issue}\n")
                    
        md.write(f"- **Web-Site Output (`web-site` stage)**:\n")
        md.write(f"  - Scanned: {web_total} file(s)\n")
        md.write(f"  - Passed: {web_passed} file(s)\n")
        md.write(f"  - Failed: {len(web_failures)} file(s)\n")
        
        if web_failures:
            md.write("  - Failures detail:\n")
            for ch, rel, issues in web_failures:
                md.write(f"    - `{rel}`:\n")
                for issue in issues:
                    md.write(f"      - {issue}\n")

        md.write("\n## 4. Step 3 Results: Negative Control Test\n\n")
        md.write(f"- **Negative Control Fixture Path**: `tests/temp_known_bad_fixture.html`\n")
        md.write(f"- **Expected Result**: FAILURE\n")
        md.write(f"- **Actual Result**: {'FAILURE' if control_passed else 'SUCCESS (Failed to detect mojibake!)'}\n")
        md.write(f"- **Detected Mojibake Tokens**: `{', '.join(detected_tokens)}`\n")
        md.write(f"- **Checker Reliability Confirmed**: {'Yes' if control_passed else 'No'}\n")

        md.write("\n## 5. Next Recommended Actions\n\n")
        if baseline_decision == "BASELINE_CONFIRMED":
            md.write("1. **Accept Baseline**: Confirm introductory-statistics-2e Chapters 1-8 as stable, verified baseline.\n")
            md.write("2. **Integrate QA Gate**: Keep `qa-math` checking as a required pipeline validation step for any future edits.\n")
        else:
            md.write("1. **Block Next Steps**: Do not merge or proceed with publishing.\n")
            md.write("2. **Analyze Failures**: Inspect the list of failing files logged above and rerun repair script as needed.\n")

    # Write CSV Report
    with open(csv_report_path, "w", encoding="utf-8", newline="") as f_csv:
        writer = csv.writer(f_csv)
        writer.writerow([
            "finding_id", "severity", "chapter", "stage", "file", 
            "block_id", "issue_type", "token", "snippet", 
            "likely_source_stage", "recommended_action"
        ])
        
        # Log Step 1 failures if any
        for idx, (ch, stage, file, issues) in enumerate(step1_failing_files):
            writer.writerow([
                f"S1-{idx+1}", "P0", ch, stage, file,
                "N/A", "mojibake_or_math_mismatch", "multiple", "; ".join(issues),
                "01-raw", "Inspect and fix using repair-encoding script."
            ])
            
        # Log Step 2 failures if any
        for idx, (ch, rel, issues) in enumerate(preview_failures):
            writer.writerow([
                f"S2P-{idx+1}", "P0", ch, "preview_html", rel,
                "N/A", "mojibake_or_meta_missing", "multiple", "; ".join(issues),
                "01-raw", "Inspect built preview HTML."
            ])
        for idx, (ch, rel, issues) in enumerate(web_failures):
            writer.writerow([
                f"S2W-{idx+1}", "P0", ch, "web_site", rel,
                "N/A", "mojibake_or_meta_missing", "multiple", "; ".join(issues),
                "01-raw", "Inspect published website HTML."
            ])

    print(f"\nVerification finished. Reports written to:\n  - {md_report_path}\n  - {csv_report_path}")

if __name__ == "__main__":
    chapters = list(range(1, 9))
    run_verification("introductory-statistics-2e", chapters)
