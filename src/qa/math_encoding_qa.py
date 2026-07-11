import re
import unicodedata
from bs4 import BeautifulSoup

# Centralized Mojibake Blacklist
MOJIBAKE_BLACKLIST = ["Î¼", "Ï", "Î±", "â¤", "â¥", "â ", "Â±", "Â¯"]

def has_mojibake(text: str) -> bool:
    """
    Check if text contains any of the blacklist items or context-corrupted 'â' or 'Â' sequences.
    """
    # 1. Blacklist check
    for token in MOJIBAKE_BLACKLIST:
        if token in text:
            return True
            
    # 2. Context-aware 'â' / 'Â' validation
    # Normalize to NFC to ensure standard Vietnamese tone representations are single code points
    normalized = unicodedata.normalize('NFC', text)
    
    # Check for lowercase â (\u00e2)
    idx = 0
    while True:
        idx = normalized.find('â', idx)
        if idx == -1:
            break
        if idx + 1 >= len(normalized):
            return True
        next_char = normalized[idx + 1].lower()
        if next_char not in ['n', 'm', 'u', 'y']:
            return True
        idx += 1
        
    # Check for uppercase Â (\u00c2)
    idx = 0
    while True:
        idx = normalized.find('Â', idx)
        if idx == -1:
            break
        if idx + 1 >= len(normalized):
            return True
        next_char = normalized[idx + 1].lower()
        if next_char not in ['n', 'm', 'u', 'y']:
            return True
        idx += 1
        
    return False

def check_file_encoding_meta(soup: BeautifulSoup) -> bool:
    """
    Check if the HTML contains <meta charset="utf-8"> inside the head.
    """
    head = soup.find('head')
    if not head:
        return False
    meta = head.find('meta', charset=lambda x: x and x.lower().replace('-', '') == 'utf8')
    if meta:
        return True
    return False

def extract_mathml_structure(element):
    """
    Extract a list of key MathML tags in pre-order traversal.
    """
    key_tags = {"math", "semantics", "mrow", "mfrac", "msqrt", "mover", "mi", "mn", "mo", "annotation-xml"}
    structure = []
    for el in element.descendants:
        if el.name in key_tags:
            structure.append(el.name)
    return structure

def check_mathml_parity(eng_el, vn_el):
    """
    Verify MathML nodes matching, structures matching, and no node converted to plain text.
    """
    eng_math = eng_el.find_all('math')
    vn_math = vn_el.find_all('math')
    
    if len(eng_math) != len(vn_math):
        return False, f"MathML count mismatch: English has {len(eng_math)}, Vietnamese has {len(vn_math)}."
        
    for idx, (eng_m, vn_m) in enumerate(zip(eng_math, vn_math)):
        eng_struct = extract_mathml_structure(eng_m)
        vn_struct = extract_mathml_structure(vn_m)
        if eng_struct != vn_struct:
            return False, f"MathML structure mismatch at index {idx}: English structural tags {eng_struct}, Vietnamese structural tags {vn_struct}."
            
    # Check that math tags from English source didn't get converted to plain text (e.g. text containing '<math' or raw text equivalents of structure)
    vn_text = vn_el.get_text()
    if len(eng_math) > 0 and len(vn_math) == 0:
        return False, "MathML nodes were entirely converted to plain text or lost."
        
    return True, ""

def check_formula_fragment_parity(eng_el, vn_el):
    """
    Check formula-like fragments and verify they are preserved in translation.
    """
    # Define simple string normalization helper to strip formatting for easy comparison
    def get_norm_text(el):
        # Convert entities
        text = el.get_text()
        text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        # Normalize spaces
        return re.sub(r'\s+', '', text)

    eng_text = get_norm_text(eng_el)
    vn_text = get_norm_text(vn_el)

    # 1. Hypotheses: H0, Ha, H_0, H_a (supporting subscripts and formatting tags)
    hyp_patterns = [
        (r'H0', 'H0'),
        (r'H_0', 'H_0'),
        (r'H<sub>0</sub>', 'H0'),
        (r'Ha', 'Ha'),
        (r'H_a', 'H_a'),
        (r'H<sub>a</sub>', 'Ha'),
    ]
    
    # Check hypothesis tokens in raw html representation to capture formatting like sub/sup/em
    eng_html = re.sub(r'\s+', '', str(eng_el))
    vn_html = re.sub(r'\s+', '', str(vn_el))
    
    # Check H0/Ha tags
    if 'H<sub>0</sub>' in eng_html and 'H<sub>0</sub>' not in vn_html:
        # Check standard text fallback H0 or H_0
        if 'H0' not in vn_text and 'H_0' not in vn_text:
            return False, "Hypothesis marker H0/H_0/H<sub>0</sub> is missing or damaged in Vietnamese."
            
    if 'H<sub>a</sub>' in eng_html and 'H<sub>a</sub>' not in vn_html:
         if 'Ha' not in vn_text and 'H_a' not in vn_text:
            return False, "Hypothesis marker Ha/H_a/H<sub>a</sub> is missing or damaged in Vietnamese."

    # 2. Statistical terms and variables (case-insensitive search)
    if 'p-value' in eng_text.lower() and 'p-value' not in vn_text.lower() and 'p-giátrị' not in vn_text.lower() and 'giátrịp' not in vn_text.lower() and 'giátrị-p' not in vn_text.lower():
        # In statistics textbooks, p-value can be translated as p-giá trị or giá trị p, but if both are missing, it's a failure
        return False, "p-value notation is missing or damaged in Vietnamese."


    # 3. Greek letters: μ, σ, α
    for greek in ['μ', 'σ', 'α']:
        if greek in eng_text and greek not in vn_text:
            return False, f"Greek symbol '{greek}' is missing or damaged in Vietnamese."

    # 4. Special statistics characters: x̄
    if 'x̄' in eng_text and 'x̄' not in vn_text:
        return False, "Special statistic variable 'x̄' is missing or damaged in Vietnamese."

    # 5. Operators: ≤, ≥, ≠, ±, =, >, <
    # We ignore standard letters/numbers, but math operators must be preserved
    operators = ['≤', '≥', '≠', '±', '=', '>', '<']
    for op in operators:
        if op in eng_text and op not in vn_text:
            return False, f"Math operator '{op}' is missing or damaged in Vietnamese."

    return True, ""

def run_math_encoding_qa(filepath) -> dict:
    """
    Execute all math/encoding checks on a single HTML file.
    Returns a dict with status and list of issues.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {"status": "FAIL", "issues": [f"Failed to read file: {e}"]}

    if not content.strip():
        return {"status": "FAIL", "issues": ["File is empty"]}

    try:
        soup = BeautifulSoup(content, "html.parser")
    except Exception as e:
        return {"status": "FAIL", "issues": [f"Parse error: {e}"]}

    issues = []

    # 1. Check meta charset utf-8
    if not check_file_encoding_meta(soup):
        issues.append("Missing <meta charset=\"utf-8\"> metadata in head.")

    # 2. Check mojibake blacklist
    # Check raw file contents first
    if has_mojibake(content):
        issues.append("Detected mojibake or encoding corruption in file contents.")

    # 3. Run MathML and Formula-fragment parity on bilingual pairs
    # Find all eng and vn block pairs
    eng_blocks = []
    vn_blocks = []
    
    # We look for all tags that have eng/vn classes
    for el in soup.find_all(True):
        classes = el.get("class", [])
        if isinstance(classes, str):
            classes = classes.split()
        elif classes is None:
            classes = []
            
        if "eng" in classes and "hidden" in classes:
            eng_blocks.append(el)
        elif "vn" in classes and "visible" in classes:
            vn_blocks.append(el)

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

    # Fallback to sequential index matching
    for eng_el in eng_blocks:
        if any(p[0] is eng_el for p in pairs):
            continue
        if unpaired_vn:
            paired = unpaired_vn.pop(0)
            pairs.append((eng_el, paired))

    # Perform parity checks on each paired element
    for eng_el, vn_el in pairs:
        eng_id_str = eng_el.get('id', '(no-id)')
        
        # MathML parity check
        math_ok, math_err = check_mathml_parity(eng_el, vn_el)
        if not math_ok:
            issues.append(f"Block '{eng_id_str}': {math_err}")
            
        # Formula fragment parity check
        frag_ok, frag_err = check_formula_fragment_parity(eng_el, vn_el)
        if not frag_ok:
            issues.append(f"Block '{eng_id_str}': {frag_err}")

    status = "FAIL" if issues else "PASS"
    return {
        "status": status,
        "issues": issues
    }
