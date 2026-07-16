import re
from bs4 import BeautifulSoup

BLOCK_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "caption", "figcaption", "th", "td"]

# English stopwords that absolutely do not exist as standard Vietnamese words
ENGLISH_STOPWORDS = {
    "the", "and", "of", "with", "from", "about", "would", "should", "could", 
    "been", "their", "they", "them", "these", "those", "which", "whose", 
    "were", "was", "are", "have", "has", "had"
}

CREDIT_KEYWORDS = {
    'credit:', 'modification of work by', 'license', 'cc by', 'flickr', 'wikimedia',
    'attribution', 'photo by', 'image courtesy of', 'public domain', 'nguồn ảnh:'
}

def is_reference(tag):
    """
    Check if a tag is inside a bibliography, reference, or citation container.
    """
    curr = tag
    while curr and curr.name != '[document]':
        tag_id = curr.get('id', '')
        if any(kw in tag_id.lower() for kw in ['reference', 'citation', 'bibliography', 'reading']):
            return True
        classes = curr.get('class', []) or []
        if isinstance(classes, str):
            classes = classes.split()
        if any(any(kw in cls.lower() for kw in ['reference', 'citation', 'bibliography', 'biblio', 'reading']) for cls in classes):
            return True
        curr = curr.parent
    return False

def is_credit_text(text):
    """
    Check if text contains standard credit/source keywords.
    """
    text_lower = text.lower()
    return any(kw in text_lower for kw in CREDIT_KEYWORDS)

def check_file_translation_qa(filepath):
    """
    Scan translated HTML file to verify translation quality:
      1. Check for untranslated blocks (VN is identical to EN).
      2. Check for English stopwords leaking into Vietnamese blocks.
      3. Check for length ratio anomalies (truncation or hallucination).
    """
    if not filepath.is_file():
        return {"status": "FAIL", "issues": [f"File {filepath} not found"]}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {"status": "FAIL", "issues": [f"Failed to read file: {e}"]}

    if not content.strip():
        return {"status": "PASS", "issues": []}

    try:
        soup = BeautifulSoup(content, "html.parser")
    except Exception as e:
        return {"status": "FAIL", "issues": [f"Failed to parse HTML: {e}"]}

    # 1. Identify and pair eng/vn blocks
    eng_blocks = []
    vn_blocks = []

    for tag_name in BLOCK_TAGS:
        for el in soup.find_all(tag_name):
            classes = el.get("class", []) or []
            if isinstance(classes, str):
                classes = classes.split()
            
            if "eng" in classes and "hidden" in classes:
                eng_blocks.append(el)
            elif "vn" in classes and "visible" in classes:
                vn_blocks.append(el)

    # Pair blocks by ID
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
                for idx, item in enumerate(unpaired_vn):
                    if item is paired:
                        unpaired_vn.pop(idx)
                        break
        if paired:
            pairs.append((eng_el, paired))

    # Sequential fallback matching
    for eng_el in eng_blocks:
        if any(p[0] is eng_el for p in pairs):
            continue
        if unpaired_vn:
            paired = unpaired_vn.pop(0)
            pairs.append((eng_el, paired))

    issues = []

    # 2. Run checks on matched pairs
    for eng_el, vn_el in pairs:
        eng_id_str = eng_el.get("id", "(no-id)")
        eng_text = eng_el.get_text().strip()
        vn_text = vn_el.get_text().strip()

        if not eng_text or not vn_text:
            continue

        # Determine if the block represents a bibliography entry or a credit
        is_ref_or_credit = is_reference(vn_el) or is_credit_text(vn_text) or "bibliography" in filepath.name.lower()

        # Check A: Identity Check (Exact match of English in Vietnamese block)
        if not is_ref_or_credit and eng_text.lower() == vn_text.lower():
            # Only flag if there are more than 3 words (to avoid single digits, symbols, or formulas)
            if len(eng_text.split()) > 3:
                snippet = vn_text[:50]
                issues.append(
                    f"Untranslated Block: VN block matches EN exactly for ID '{eng_id_str}': \"{snippet}...\""
                )
                continue

        # Check B: English Stopwords Leak Check
        if not is_ref_or_credit:
            # Create a clean version of VN text by removing em, i, code, math tags
            vn_soup_tmp = BeautifulSoup(str(vn_el), "html.parser")
            vn_tag_tmp = list(vn_soup_tmp.children)[0] if list(vn_soup_tmp.children) else vn_soup_tmp
            for remove_tag in vn_tag_tmp.find_all(["em", "i", "code", "math", "semantics"]):
                remove_tag.decompose()
            vn_text_clean = vn_tag_tmp.get_text()

            # Remove capitalized proper nouns / named entities (e.g. "Order of the Arrow", "Smithsonian Institution")
            # to avoid false positives for English stopwords inside them.
            vn_text_clean_no_proper = re.sub(
                r'\b[A-Z][a-zA-Z]*(?:\s+(?:of|the|and|in|on|at|for|to|with|by|de)\b\s*){1,2}[A-Z][a-zA-Z]*\b', 
                '', 
                vn_text_clean
            )
            # Remove single capitalized words to filter out isolated English names/titles
            vn_text_clean_no_proper = re.sub(r'\b[A-Z][a-zA-Z]*\b', '', vn_text_clean_no_proper)

            vn_words = set(re.findall(r"\b[a-zA-Z]+\b", vn_text_clean_no_proper.lower()))
            matched_stopwords = vn_words.intersection(ENGLISH_STOPWORDS)
            if matched_stopwords:
                # Report up to 3 leaked stopwords
                sw_list = ", ".join(list(matched_stopwords)[:3])
                snippet = vn_text_clean.strip()[:50]
                issues.append(
                    f"English Word Leak: Detected English stopwords ({sw_list}) inside VN block ID '{eng_id_str}': \"{snippet}...\""
                )

        # Check C: Length Ratio Checks (Truncation/Hallucination)
        eng_len = len(eng_text)
        vn_len = len(vn_text)
        
        if eng_len > 10:
            ratio = vn_len / eng_len
            if ratio < 0.3:
                issues.append(
                    f"Potential Truncation: VN text is too short compared to EN (ratio {ratio:.2f}) for ID '{eng_id_str}'"
                )
            elif ratio > 3.0:
                issues.append(
                    f"Potential Hallucination: VN text is too long compared to EN (ratio {ratio:.2f}) for ID '{eng_id_str}'"
                )

    status = "FAIL" if issues else "PASS"
    return {"status": status, "issues": issues}
