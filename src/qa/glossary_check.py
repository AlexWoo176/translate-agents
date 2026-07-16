import os
import re
import csv
import unicodedata
from pathlib import Path
from bs4 import BeautifulSoup
from src.core.paths import get_book_root, get_translated_dir, get_reviews_dir

BLOCK_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "caption", "figcaption", "th", "td"]

STRUCTURAL_TERMS = {
    "figure", "table", "chapter", "preface", "references", "index", 
    "summary", "key terms", "key concepts", "introduction", "review questions", 
    "critical thinking questions", "learning outcomes", "learning objectives",
    "table of contents", "about openstax", "about the authors", "reviewers"
}

def normalize_vn_tones(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    # Map old tone-mark placements to new tone-mark placements
    text = text.replace("oá", "óa").replace("oà", "òa").replace("oả", "ỏa").replace("oã", "õa").replace("oạ", "ọa")
    text = text.replace("uý", "úy").replace("uỳ", "ùy").replace("uỷ", "ủy").replace("uỹ", "ũy").replace("uỵ", "ụy")
    text = text.replace("oé", "óe").replace("oè", "òe").replace("oẻ", "ỏe").replace("oẽ", "õe").replace("oẹ", "ọe")
    return unicodedata.normalize('NFC', text)


def is_term_match(term_clean: str, tagged_clean: str) -> bool:
    if not term_clean:
        return False
    # Exact full match or match with common English suffixes (s, es, d, ed, ing)
    pattern = r'^' + re.escape(term_clean) + r'(s|es|d|ed|ing)?$'
    if re.match(pattern, tagged_clean):
        return True
    if ' ' in term_clean:
        words = term_clean.split()
        last_word = words[-1]
        prefix = " ".join(words[:-1])
        pattern_phrase = r'^' + re.escape(prefix) + r'\s+' + re.escape(last_word) + r'(s|es|d|ed|ing)?$'
        if re.match(pattern_phrase, tagged_clean):
            return True
    return False


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
        # Remove URLs to avoid false positives for structural terms like "index" in links
        eng_text_for_struct = re.sub(r'https?://\S+', '', eng_text_lower)
        # Remove "figure out" to avoid false positives for structural term "figure"
        eng_text_for_struct = re.sub(r'\bfigured?\s+out\b', '', eng_text_for_struct)
        eng_text_for_struct = re.sub(r'\bfiguring\s+out\b', '', eng_text_for_struct)
        vn_text_norm = normalize_vn_tones(vn_text)

        # Pre-extract all tagged terms in the English block to restrict key term matching
        eng_terms_tagged = [
            unicodedata.normalize('NFC', span.get_text().strip().lower())
            for span in eng_el.find_all(lambda tag: tag.name == "span" and tag.get("data-type") == "term")
        ]

        tagged_to_glossary_rows = {}
        structural_rows_to_check = []

        for row in glossary:
            term = row["term"]
            term_lower = term.lower()

            if term_lower in STRUCTURAL_TERMS:
                # Structural/layout terms are matched against the raw paragraph text without URLs
                if re.search(r'\b' + re.escape(term_lower) + r'\b', eng_text_for_struct):
                    structural_rows_to_check.append(row)
            else:
                # Key terms must be explicitly wrapped in a term span in the English source
                term_clean = re.sub(r'\(.*?\)', '', term_lower).strip()
                if term_clean:
                    for tagged in eng_terms_tagged:
                        tagged_clean = re.sub(r'\(.*?\)', '', tagged).strip()
                        if is_term_match(term_clean, tagged_clean):
                            if tagged_clean not in tagged_to_glossary_rows:
                                tagged_to_glossary_rows[tagged_clean] = []
                            tagged_to_glossary_rows[tagged_clean].append(row)

        # Check structural terms (each must match)
        for row in structural_rows_to_check:
            term = row["term"]
            translation = row["translation"]

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
            else:
                translation_opts = []
                for opt in translation.split("/"):
                    opt_clean = opt.strip()
                    if opt_clean:
                        translation_opts.append(normalize_vn_tones(opt_clean))
                        opt_no_parentheses = re.sub(r'\(.*?\)', '', opt_clean).strip()
                        if opt_no_parentheses and opt_no_parentheses != opt_clean:
                            translation_opts.append(normalize_vn_tones(opt_no_parentheses))

                matched = any(opt in vn_text_norm for opt in translation_opts)
                if not matched:
                    violations.append({
                        "term": term,
                        "translation": translation,
                        "block_id": eng_id_str,
                        "reason": f"Term '{term}' ('{translation}') is missing in Vietnamese block"
                    })

        # Check key terms (at least one row must match per tagged term, resolving containment conflicts)
        for tagged_clean, rows in tagged_to_glossary_rows.items():
            # If any matched row is an exact match for the tag, check only those rows
            exact_matches = [r for r in rows if re.sub(r'\(.*?\)', '', r["term"].lower()).strip() == tagged_clean]
            if exact_matches:
                rows_to_check = exact_matches
            else:
                # Otherwise, keep only the rows matching the maximum term length to avoid containment conflicts
                max_len = max(len(re.sub(r'\(.*?\)', '', r["term"].lower()).strip().split()) for r in rows)
                rows_to_check = [r for r in rows if len(re.sub(r'\(.*?\)', '', r["term"].lower()).strip().split()) == max_len]

            any_matched = False
            for row in rows_to_check:
                term = row["term"]
                translation = row["translation"]

                if not translation:
                    continue

                translation_opts = []
                for opt in translation.split("/"):
                    opt_clean = opt.strip()
                    if opt_clean:
                        translation_opts.append(normalize_vn_tones(opt_clean))
                        opt_no_parentheses = re.sub(r'\(.*?\)', '', opt_clean).strip()
                        if opt_no_parentheses and opt_no_parentheses != opt_clean:
                            translation_opts.append(normalize_vn_tones(opt_no_parentheses))

                if any(opt in vn_text_norm for opt in translation_opts):
                    any_matched = True
                    break

            # If none matched, report violations for all rows in the filtered check group
            if not any_matched:
                for row in rows_to_check:
                    term = row["term"]
                    translation = row["translation"]

                    detected.append({
                        "term": term,
                        "translation": translation,
                        "block_id": eng_id_str,
                        "eng_text": eng_text.strip(),
                        "vn_text": vn_text.strip()
                    })

                    if not translation:
                        violations.append({
                            "term": term,
                            "translation": "[EMPTY]",
                            "block_id": eng_id_str,
                            "reason": f"Term '{term}' is in English block, but its approved translation is empty"
                        })
                    else:
                        violations.append({
                            "term": term,
                            "translation": translation,
                            "block_id": eng_id_str,
                            "reason": f"Term '{term}' ('{translation}') is missing in Vietnamese block"
                        })
            else:
                # If matched, we still register them as detected
                for row in rows_to_check:
                    term = row["term"]
                    translation = row["translation"]
                    detected.append({
                        "term": term,
                        "translation": translation,
                        "block_id": eng_id_str,
                        "eng_text": eng_text.strip(),
                        "vn_text": vn_text.strip()
                    })

    status = "FAIL" if violations else "PASS"

    return {
        "status": status,
        "violations": violations,
        "detected": detected
    }
