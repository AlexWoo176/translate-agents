import os
import re
import csv
import json
import argparse
from pathlib import Path
from bs4 import BeautifulSoup

# Define English stopwords for density detection
ENGLISH_STOPWORDS = {
    'the', 'and', 'of', 'to', 'in', 'is', 'that', 'it', 'for', 'on', 'with', 'as', 'this',
    'are', 'by', 'an', 'be', 'at', 'or', 'if', 'suppose', 'reject', 'fail', 'null', 'hypothesis',
    'probability', 'sample', 'mean', 'standard', 'deviation', 'confidence', 'interval', 'population',
    'distribution', 'test', 'value', 'data', 'we', 'from', 'which', 'random', 'variable', 'following',
    'under', 'between', 'each', 'results', 'conclude', 'evidence', 'interpret', 'suppose', 'determine',
    'calculate', 'find', 'using', 'given', 'show', 'table', 'where', 'then', 'there', 'has', 'have', 'been'
}

# Vietnamese diacritics pattern (lower & upper)
VN_DIACRITICS_RE = re.compile(
    r'[áàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ'
    r'ÁÀẢÃẠÂẤẦẨẪẬĂẮẰẲẴẶÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ]'
)

# Common allowable tech terms & symbols that shouldn't trigger alerts
ALLOWED_TERMS = {
    'h0', 'ha', 'p-value', 'z-score', 'x̄', 'μ', 'σ', 'α', 'beta', 'df', 'chi-square',
    'openstax', 'creative commons', 'attribution', 'license', 'sd', 'n1', 'n2', 'ti-83', 'ti-84'
}

def get_norm_words(text):
    clean = re.sub(r'[^a-zA-Z\s]', '', text.lower())
    return clean.split()

def calculate_jaccard(text1, text2):
    w1 = set(get_norm_words(text1))
    w2 = set(get_norm_words(text2))
    if not w1 and not w2:
        return 1.0
    return len(w1.intersection(w2)) / len(w1.union(w2))

def detect_english_residue(text):
    text_stripped = text.strip()
    if not text_stripped or len(text_stripped) < 4:
        return False, 0.0
        
    words = get_norm_words(text_stripped)
    if not words:
        return False, 0.0
        
    # Check stopword overlap
    stopwords_found = [w for w in words if w in ENGLISH_STOPWORDS]
    stopword_ratio = len(stopwords_found) / len(words)
    
    # Check Vietnamese diacritics count
    vn_chars = VN_DIACRITICS_RE.findall(text_stripped)
    vn_ratio = len(vn_chars) / len(text_stripped)
    
    # Heuristics:
    # 1. No Vietnamese diacritics, and at least 3 English words, and stopword density > 10%
    if len(vn_chars) == 0 and len(words) >= 3 and stopword_ratio >= 0.10:
        # Check if the words are mostly allowed tech terms
        non_allowed = [w for w in words if w not in ALLOWED_TERMS and not w.isdigit()]
        if len(non_allowed) >= 2:
            return True, stopword_ratio
            
    return False, stopword_ratio

def parse_chapter_range(chapters_arg):
    if '-' in chapters_arg:
        start, end = chapters_arg.split('-')
        return list(range(int(start), int(end) + 1))
    return [int(chapters_arg)]

def main():
    parser = argparse.ArgumentParser(description="Audit Vietnamese translated pages for English residue.")
    parser.add_argument("--book", default="introductory-statistics-2e", help="Book slug name")
    parser.add_argument("--chapters", default="1-11", help="Chapter range or single chapter, e.g., '1-11'")
    args = parser.parse_args()

    book_slug = args.book
    chapters = parse_chapter_range(args.chapters)

    # Core workspace layout paths
    book_root = Path(f"D:/OPENSTAX/books/{book_slug}")
    web_site_root = Path(f"D:/OPENSTAX/web-site/{book_slug}")

    if not book_root.is_dir():
        print(f"Error: Book directory {book_root} does not exist.")
        return 1

    findings = []
    scanned_stats = {
        "chapters": [],
        "files_scanned": 0,
        "files_with_issues": set(),
        "stages": {
            "05-translated": {"scanned": 0, "findings": 0, "P0": 0, "P1": 0, "P2": 0},
            "07-archive-bilingual": {"scanned": 0, "findings": 0, "P0": 0, "P1": 0, "P2": 0},
            "07-archive-vn-only": {"scanned": 0, "findings": 0, "P0": 0, "P1": 0, "P2": 0},
            "preview-html": {"scanned": 0, "findings": 0, "P0": 0, "P1": 0, "P2": 0},
            "web-site": {"scanned": 0, "findings": 0, "P0": 0, "P1": 0, "P2": 0}
        }
    }

    finding_counter = 1

    for ch in chapters:
        ch_slug = f"chapter-{ch}"
        ch_root = book_root / ch_slug
        if not ch_root.is_dir():
            continue

        scanned_stats["chapters"].append(ch_slug)
        print(f"Auditing chapter {ch}...")

        # --- Stage 1: 05-translated/ ---
        trans_dir = ch_root / "05-translated"
        prep_dir = ch_root / "04-prep"
        if trans_dir.is_dir():
            for f in trans_dir.glob("*.html"):
                scanned_stats["files_scanned"] += 1
                scanned_stats["stages"]["05-translated"]["scanned"] += 1
                
                # Check paired prep file to identify CAUSE_TRANSLATION_SKIPPED
                prep_file = prep_dir / f.name if prep_dir.is_dir() else None
                
                soup = BeautifulSoup(f.read_text(encoding="utf-8"), "html.parser")
                vn_elements = soup.find_all(class_="vn visible")
                
                for el in vn_elements:
                    if el.find(['script', 'style', 'math', 'code', 'semantics', 'annotation', 'mi', 'mo', 'mn', 'mrow', 'msup', 'msub']):
                        continue
                    el_id = el.get("id")
                    if not el_id:
                        continue
                    
                    vn_text = el.get_text().strip()
                    if not vn_text:
                        continue
                        
                    # Find matching English element
                    eng_id = el_id.replace("-vn", "")
                    eng_el = soup.find(id=eng_id)
                    eng_text = eng_el.get_text().strip() if eng_el else ""
                    
                    is_residue, density = detect_english_residue(vn_text)
                    similarity = calculate_jaccard(eng_text, vn_text) if eng_text else 0.0
                    
                    is_finding = False
                    severity = "P2"
                    likely_cause = "CAUSE_UNKNOWN"
                    issue_type = "untranslated_block"
                    
                    # Heuristics:
                    if similarity > 0.85 and len(vn_text) > 10:
                        # Check if it has translatable words (excluding purely numbers/math)
                        words = get_norm_words(vn_text)
                        non_allowed = [w for w in words if w not in ALLOWED_TERMS and not w.isdigit()]
                        if len(non_allowed) >= 2:
                            is_finding = True
                            severity = "P0" if len(vn_text) > 40 else "P1"
                            issue_type = "identical_to_source"
                            
                    elif is_residue:
                        is_finding = True
                        severity = "P1"
                        issue_type = "english_prose_detected"

                    if is_finding:
                        # Check if prep version was also identical
                        if prep_file and prep_file.is_file():
                            try:
                                prep_soup = BeautifulSoup(prep_file.read_text(encoding="utf-8"), "html.parser")
                                prep_el = prep_soup.find(id=el_id)
                                if prep_el and prep_el.get_text().strip() == vn_text:
                                    likely_cause = "CAUSE_TRANSLATION_SKIPPED"
                                else:
                                    likely_cause = "CAUSE_PARTIAL_TRANSLATION"
                            except Exception:
                                pass
                        
                        # Labels check (e.g. Example, Solution)
                        if vn_text.lower() in ["example", "solution", "try it", "problem"]:
                            severity = "P1"
                            issue_type = "unlocalized_label"
                            likely_cause = "CAUSE_TRANSLATION_SKIPPED"
                            
                        # Further filter P0/P1 based on allowable terms
                        if any(term in vn_text.lower() for term in ALLOWED_TERMS) and len(vn_text) < 20:
                            severity = "P2"
                            likely_cause = "CAUSE_ALLOWED_TECHNICAL_TERM"

                        finding = {
                            "finding_id": f"F-{finding_counter:04d}",
                            "severity": severity,
                            "chapter": ch_slug,
                            "stage": "05-translated",
                            "file": f.name,
                            "block_id": el_id,
                            "tag": el.name,
                            "issue_type": issue_type,
                            "likely_cause": likely_cause,
                            "english_snippet": eng_text[:150],
                            "source_snippet": eng_text[:150],
                            "vn_snippet": vn_text[:150],
                            "similarity_score": round(similarity, 3),
                            "recommended_action": "Rerun translation for block with clean glossary context." if severity != "P2" else "Review manually to see if English term is expected."
                        }
                        findings.append(finding)
                        scanned_stats["files_with_issues"].add(f.name)
                        scanned_stats["stages"]["05-translated"]["findings"] += 1
                        scanned_stats["stages"]["05-translated"][severity] += 1
                        finding_counter += 1

        # --- Stage 2: 07-archive/bilingual/html/ ---
        archive_bi_dir = ch_root / "07-archive" / "bilingual" / "html"
        if archive_bi_dir.is_dir():
            for f in archive_bi_dir.glob("*.html"):
                scanned_stats["stages"]["07-archive-bilingual"]["scanned"] += 1
                soup = BeautifulSoup(f.read_text(encoding="utf-8"), "html.parser")
                vn_elements = soup.find_all(class_="vn visible")
                
                for el in vn_elements:
                    if el.find(['script', 'style', 'math', 'code', 'semantics', 'annotation', 'mi', 'mo', 'mn', 'mrow', 'msup', 'msub']):
                        continue
                    vn_text = el.get_text().strip()
                    is_residue, density = detect_english_residue(vn_text)
                    if is_residue:
                        el_id = el.get("id", "N/A")
                        # Cross-reference with 05-translated to see if it is EXPORTER selected wrong block
                        # ...
                        finding = {
                            "finding_id": f"F-{finding_counter:04d}",
                            "severity": "P0" if len(vn_text) > 40 else "P1",
                            "chapter": ch_slug,
                            "stage": "07-archive-bilingual",
                            "file": f.name,
                            "block_id": el_id,
                            "tag": el.name,
                            "issue_type": "bilingual_archive_english_residue",
                            "likely_cause": "CAUSE_PARTIAL_TRANSLATION",
                            "english_snippet": "",
                            "source_snippet": "",
                            "vn_snippet": vn_text[:150],
                            "similarity_score": 0.0,
                            "recommended_action": "Rebuild archive files after fixing 05-translated source."
                        }
                        findings.append(finding)
                        scanned_stats["files_with_issues"].add(f.name)
                        scanned_stats["stages"]["07-archive-bilingual"]["findings"] += 1
                        scanned_stats["stages"]["07-archive-bilingual"][finding["severity"]] += 1
                        finding_counter += 1

        # --- Stage 3: 07-archive/vn-only/html/ ---
        archive_vn_dir = ch_root / "07-archive" / "vn-only" / "html"
        if archive_vn_dir.is_dir():
            for f in archive_vn_dir.glob("*.html"):
                scanned_stats["stages"]["07-archive-vn-only"]["scanned"] += 1
                soup = BeautifulSoup(f.read_text(encoding="utf-8"), "html.parser")
                # Parse all visual text tags
                for tag_name in ['p', 'span', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'td', 'th', 'dt', 'dd']:
                    for el in soup.find_all(tag_name):
                        if el.find(['script', 'style', 'math', 'code']):
                            continue
                        txt = el.get_text().strip()
                        is_residue, density = detect_english_residue(txt)
                        if is_residue:
                            finding = {
                                "finding_id": f"F-{finding_counter:04d}",
                                "severity": "P0" if len(txt) > 40 else "P1",
                                "chapter": ch_slug,
                                "stage": "07-archive-vn-only",
                                "file": f.name,
                                "block_id": el.get("id", "N/A"),
                                "tag": el.name,
                                "issue_type": "vn_only_archive_english_prose",
                                "likely_cause": "CAUSE_EXPORTER_SELECTED_WRONG_BLOCK",
                                "english_snippet": "",
                                "source_snippet": "",
                                "vn_snippet": txt[:150],
                                "similarity_score": 0.0,
                                "recommended_action": "Verify if exporter config parsed wrong classes."
                            }
                            findings.append(finding)
                            scanned_stats["files_with_issues"].add(f.name)
                            scanned_stats["stages"]["07-archive-vn-only"]["findings"] += 1
                            scanned_stats["stages"]["07-archive-vn-only"][finding["severity"]] += 1
                            finding_counter += 1

        # --- Stage 4: preview-html (.html/chapter-N/) ---
        preview_dir = book_root / ".html" / ch_slug
        if preview_dir.is_dir():
            for f in preview_dir.glob("*.html"):
                scanned_stats["stages"]["preview-html"]["scanned"] += 1
                soup = BeautifulSoup(f.read_text(encoding="utf-8"), "html.parser")
                # Scans visible .vn.visible elements
                vn_elements = soup.find_all(class_="vn visible")
                for el in vn_elements:
                    if el.find(['script', 'style', 'math', 'code', 'semantics', 'annotation', 'mi', 'mo', 'mn', 'mrow', 'msup', 'msub']):
                        continue
                    vn_text = el.get_text().strip()
                    is_residue, density = detect_english_residue(vn_text)
                    if is_residue:
                        finding = {
                            "finding_id": f"F-{finding_counter:04d}",
                            "severity": "P0" if len(vn_text) > 40 else "P1",
                            "chapter": ch_slug,
                            "stage": "preview-html",
                            "file": f.name,
                            "block_id": el.get("id", "N/A"),
                            "tag": el.name,
                            "issue_type": "preview_site_english_prose",
                            "likely_cause": "CAUSE_BUILD_OR_WEBSITE_STALE",
                            "english_snippet": "",
                            "source_snippet": "",
                            "vn_snippet": vn_text[:150],
                            "similarity_score": 0.0,
                            "recommended_action": "Rebuild HTML book workspace preview."
                        }
                        findings.append(finding)
                        scanned_stats["files_with_issues"].add(f.name)
                        scanned_stats["stages"]["preview-html"]["findings"] += 1
                        scanned_stats["stages"]["preview-html"][finding["severity"]] += 1
                        finding_counter += 1

        # --- Stage 5: web-site/ ---
        web_site_dir = web_site_root / ch_slug
        if web_site_dir.is_dir():
            for f in web_site_dir.glob("*.html"):
                scanned_stats["stages"]["web-site"]["scanned"] += 1
                soup = BeautifulSoup(f.read_text(encoding="utf-8"), "html.parser")
                vn_elements = soup.find_all(class_="vn visible")
                for el in vn_elements:
                    if el.find(['script', 'style', 'math', 'code', 'semantics', 'annotation', 'mi', 'mo', 'mn', 'mrow', 'msup', 'msub']):
                        continue
                    vn_text = el.get_text().strip()
                    is_residue, density = detect_english_residue(vn_text)
                    if is_residue:
                        finding = {
                            "finding_id": f"F-{finding_counter:04d}",
                            "severity": "P0" if len(vn_text) > 40 else "P1",
                            "chapter": ch_slug,
                            "stage": "web-site",
                            "file": f.name,
                            "block_id": el.get("id", "N/A"),
                            "tag": el.name,
                            "issue_type": "web_site_english_prose",
                            "likely_cause": "CAUSE_BUILD_OR_WEBSITE_STALE",
                            "english_snippet": "",
                            "source_snippet": "",
                            "vn_snippet": vn_text[:150],
                            "similarity_score": 0.0,
                            "recommended_action": "Rebuild site with --copy-to-web."
                        }
                        findings.append(finding)
                        scanned_stats["files_with_issues"].add(f.name)
                        scanned_stats["stages"]["web-site"]["findings"] += 1
                        scanned_stats["stages"]["web-site"][finding["severity"]] += 1
                        finding_counter += 1

    # Ensure reports folder exists
    reports_dir = book_root / "_book-level" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    csv_path = reports_dir / "english-residue-audit-chapters-1-11.csv"
    md_path = reports_dir / "english-residue-audit-chapters-1-11.md"

    # 1. Write CSV report
    csv_columns = [
        "finding_id", "severity", "chapter", "stage", "file", "block_id", "tag",
        "issue_type", "likely_cause", "english_snippet", "source_snippet", "vn_snippet",
        "similarity_score", "recommended_action"
    ]
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=csv_columns)
            writer.writeheader()
            for finding in findings:
                writer.writerow(finding)
    except Exception as e:
        print(f"Error writing CSV report: {e}")

    # 2. Write Markdown report
    p0_count = len([f for f in findings if f["severity"] == "P0"])
    p1_count = len([f for f in findings if f["severity"] == "P1"])
    p2_count = len([f for f in findings if f["severity"] == "P2"])
    
    # Calculate counts per chapter
    chapter_counts = {}
    for f in findings:
        chapter_counts[f["chapter"]] = chapter_counts.get(f["chapter"], 0) + 1
        
    sorted_chapters = sorted(chapter_counts.items(), key=lambda x: x[1], reverse=True)
    highest_issue_chapter = sorted_chapters[0][0] if sorted_chapters else "N/A"
    
    # Calculate counts per stage
    stage_counts = {}
    for f in findings:
        stage_counts[f["stage"]] = stage_counts.get(f["stage"], 0) + 1
        
    sorted_stages = sorted(stage_counts.items(), key=lambda x: x[1], reverse=True)
    highest_issue_stage = sorted_stages[0][0] if sorted_stages else "N/A"

    md_lines = [
        "# English Residue Audit Report (Chapters 1–11)",
        "",
        "This report summarizes the findings of a read-only audit scanning the Vietnamese translation outputs for English-language residue and untranslated content.",
        "",
        "## 1. Executive Summary",
        f"- **Chapters Audited**: {', '.join(scanned_stats['chapters'])}",
        "- **Stages Audited**: 05-translated, 07-archive-bilingual, 07-archive-vn-only, preview-html, web-site",
        f"- **Total Files Scanned**: {scanned_stats['files_scanned']}",
        f"- **Total Findings**: {len(findings)}",
        f"  - **P0 (Blocking)**: {p0_count}",
        f"  - **P1 (High)**: {p1_count}",
        f"  - **P2 (Manual)**: {p2_count}",
        f"- **Chapter with Highest Issues**: {highest_issue_chapter}",
        f"- **Stage with Highest Issues**: {highest_issue_stage}",
        "- **Top Suspected Cause**: CAUSE_TRANSLATION_SKIPPED",
        "",
        "## 2. Chapter Summary Table",
        "",
        "| Chapter | Files Scanned | Files with Issues | P0 Count | P1 Count | P2 Count | Recommended Action |",
        "| --- | --- | --- | --- | --- | --- | --- |"
    ]

    for ch_slug in scanned_stats["chapters"]:
        ch_findings = [f for f in findings if f["chapter"] == ch_slug]
        ch_files = {f["file"] for f in ch_findings}
        ch_p0 = len([f for f in ch_findings if f["severity"] == "P0"])
        ch_p1 = len([f for f in ch_findings if f["severity"] == "P1"])
        ch_p2 = len([f for f in ch_findings if f["severity"] == "P2"])
        
        md_lines.append(
            f"| {ch_slug} | - | {len(ch_files)} | {ch_p0} | {ch_p1} | {ch_p2} | "
            f"{'Fix P0/P1 blocks' if (ch_p0 + ch_p1 > 0) else 'None'} |"
        )

    md_lines.extend([
        "",
        "## 3. Stage Summary Table",
        "",
        "| Stage | Files Scanned | Findings Count | P0/P1/P2 Count | Likely Cause |",
        "| --- | --- | --- | --- | --- |"
    ])

    for stage_name, info in scanned_stats["stages"].items():
        md_lines.append(
            f"| {stage_name} | {info['scanned']} | {info['findings']} | "
            f"{info['P0']}/{info['P1']}/{info['P2']} | "
            f"{'CAUSE_TRANSLATION_SKIPPED' if stage_name == '05-translated' else 'CAUSE_BUILD_OR_WEBSITE_STALE'} |"
        )

    md_lines.extend([
        "",
        "## 4. Cause Analysis",
        "",
        "### CAUSE_TRANSLATION_SKIPPED",
        "The translation model skipped translating specific blocks, resulting in the Vietnamese text block remaining identical to the English source block.",
        "",
        "### CAUSE_PARTIAL_TRANSLATION",
        "Some sentences in a block were translated to Vietnamese, but one or more English sentences were left behind in the final text block.",
        "",
        "### CAUSE_EXPORTER_SELECTED_WRONG_BLOCK",
        "A bug in the export template selector mapped the wrong source element tags or bilingual wrapper blocks.",
        "",
        "### CAUSE_BUILD_OR_WEBSITE_STALE",
        "Old built files remained in preview or web-site output directories and were not overwritten because `--copy-to-web` was omitted.",
        "",
        "### CAUSE_ALLOWED_TECHNICAL_TERM",
        "Mathematical expressions, symbols, abbreviations (like p-value or z-score) that are expected to stay in standard form.",
        "",
        "## 5. Recommended Repair Strategy",
        "",
        "> [!IMPORTANT]",
        "> 1. **Do not run bulk repair commands** until P0 issues are manually checked.",
        "> 2. **Rerun translation** on skipped blocks using the CLI command targeting specific files/ids.",
        "> 3. **Force a rebuild** of the book preview and website with `build --copy-to-web` once translation fixes are archived.",
        "",
        "## 6. Detailed Findings",
        ""
    ])

    for finding in findings:
        md_lines.extend([
            f"### Finding {finding['finding_id']} ({finding['severity']})",
            f"- **Chapter**: {finding['chapter']}",
            f"- **Stage**: {finding['stage']}",
            f"- **File**: {finding['file']}",
            f"- **Block ID**: {finding['block_id']}",
            f"- **Tag**: {finding['tag']}",
            f"- **Issue Type**: {finding['issue_type']}",
            f"- **Likely Cause**: {finding['likely_cause']}",
            f"- **English snippet**: `{finding['english_snippet']}`",
            f"- **Vietnamese block snippet**: `{finding['vn_snippet']}`",
            f"- **Similarity**: {finding['similarity_score']}",
            f"- **Action**: {finding['recommended_action']}",
            ""
        ])

    try:
        md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
        print("Markdown report updated successfully!")
    except Exception as e:
        print(f"Error writing Markdown report: {e}")

    return 0

if __name__ == "__main__":
    main()
