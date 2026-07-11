import os
import re
import csv
from pathlib import Path
from bs4 import BeautifulSoup
from src.core.paths import get_book_root, get_translated_dir, get_reviews_dir

BLOCK_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "caption", "figcaption", "th", "td"]

def load_glossary(csv_path, load_global=True):
    """
    Load glossary.csv, only extracting approved rows with non-empty terms.
    If a global_glossary.csv exists at the project root, it will be loaded first,
    and then the book-specific glossary will be loaded and merge into/override it.
    """
    from src.core.config import WORKSPACE_ROOT
    global_path = Path(WORKSPACE_ROOT) / "global_glossary.csv"
    
    glossary_dict = {}
    
    def parse_file(path):
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                term = row.get("term", "").strip()
                translation = row.get("translation", "").strip()
                status = row.get("status", "").strip().lower()
                context = row.get("context", "").strip()
                notes = row.get("notes", "").strip()

                if not term:
                    continue

                if status == "approved":
                    glossary_dict[term.lower()] = {
                        "term": term,
                        "translation": translation,
                        "context": context,
                        "notes": notes
                    }
                    
    # Load global glossary first (skip if load_global is False or running in test environment)
    import sys
    is_testing = "unittest" in sys.modules or "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv)
    if load_global and not is_testing:
        parse_file(global_path)
    # Load book-specific glossary second, overriding any matching global terms
    parse_file(csv_path)
    
    return list(glossary_dict.values())

def check_file_glossary(html_path, glossary):
    """
    Check a single HTML file's bilingual translation blocks against loaded glossary.
    """
    if not os.path.isfile(html_path):
        return {"status": "FAIL", "violations": [f"File {html_path} not found"], "detected": []}

    try:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {"status": "FAIL", "violations": [f"Failed to read file: {e}"], "detected": []}

    if not content.strip():
        return {"status": "FAIL", "violations": ["Empty file"], "detected": []}

    try:
        soup = BeautifulSoup(content, "html.parser")
    except Exception as e:
        return {"status": "FAIL", "violations": [f"Parse error: {e}"], "detected": []}

    # 1. Collect all block tags
    eng_blocks = []
    vn_blocks = []

    for tag_name in BLOCK_TAGS:
        for el in soup.find_all(tag_name):
            classes = el.get("class", [])
            if isinstance(classes, str):
                classes = classes.split()
            elif classes is None:
                classes = []

            if "eng" in classes and "hidden" in classes:
                eng_blocks.append(el)
            elif "vn" in classes and "visible" in classes:
                vn_blocks.append(el)

    # 2. Pair them by ID, fallback to sequential order
    vn_by_id = {}
    for el in vn_blocks:
        el_id = el.get("id")
        if el_id:
            vn_by_id[el_id] = el

    pairs = []
    unpaired_vn = list(vn_blocks)

    for eng_el in eng_blocks:
        eng_id = eng_el.get("id")
        paired = None
        if eng_id:
            vn_id = f"{eng_id}-vn"
            if vn_id in vn_by_id:
                paired = vn_by_id[vn_id]
                # Remove by identity to avoid value matching issues
                for idx, item in enumerate(unpaired_vn):
                    if item is paired:
                        unpaired_vn.pop(idx)
                        break
        if paired:
            pairs.append((eng_el, paired))

    # Sequential index matching fallback
    for eng_el in eng_blocks:
        if any(p[0] is eng_el for p in pairs):
            continue
        if unpaired_vn:
            paired = unpaired_vn.pop(0)
            pairs.append((eng_el, paired))

    violations = []
    detected = []

    # 3. Scan each pair for terms
    for eng_el, vn_el in pairs:
        eng_text = eng_el.get_text()
        vn_text = vn_el.get_text()
        eng_id_str = eng_el.get("id", "(no-id)")

        eng_text_lower = eng_text.lower()
        vn_text_lower = vn_text.lower()

        for row in glossary:
            term = row["term"]
            translation = row["translation"]

            # Case-insensitive word boundary match
            if re.search(r'\b' + re.escape(term.lower()) + r'\b', eng_text_lower):
                detected.append({
                    "term": term,
                    "translation": translation,
                    "block_id": eng_id_str,
                    "eng_text": eng_text.strip(),
                    "vn_text": vn_text.strip()
                })

                # Check if translation is empty
                if not translation:
                    violations.append({
                        "term": term,
                        "translation": "[EMPTY]",
                        "block_id": eng_id_str,
                        "reason": f"Term '{term}' is in English block, but its approved translation is empty"
                    })
                elif not re.search(r'\b' + re.escape(translation.lower()) + r'\b', vn_text_lower):
                    violations.append({
                        "term": term,
                        "translation": translation,
                        "block_id": eng_id_str,
                        "reason": f"Term '{term}' ('{translation}') is missing in Vietnamese block"
                    })

    status = "FAIL" if violations else "PASS"

    return {
        "status": status,
        "violations": violations,
        "detected": detected
    }
