import re
import copy
from bs4 import BeautifulSoup, NavigableString

def is_math_em(em_element):
    if em_element.find(['sub', 'sup']):
        return True
    
    text = em_element.get_text().strip()
    if not text:
        return False
        
    if len(text) == 1:
        return True
        
    # Greek letters
    greek_letters = ['μ', 'σ', 'α', 'β', 'γ', 'δ', 'λ', 'θ', 'π', 'χ', 'ρ', 'η', 'Σ']
    if any(g in text for g in greek_letters):
        return True
        
    if re.search(r'\bchi\b', text, re.IGNORECASE):
        return True
        
    low_text = text.lower()
    if low_text in ['h0', 'ha', 'df', 'p-value', 'p', 'sd', 'se', 'ss', 'ms', 'gpa']:
        return True
        
    if len(text) <= 4 and re.match(r'^[a-zA-Z0-9\-\+\*\/=\<\>≤≥≠±≈\s_]+$', text):
        if re.search(r'[0-9\-\+\*\/=\<\>≤≥≠±≈_]', text) or len(text) <= 2:
            return True
            
    return False

def protect_math_and_formulas(soup_or_element):
    is_str = isinstance(soup_or_element, str)
    if is_str:
        soup = BeautifulSoup(soup_or_element, 'html.parser')
    else:
        soup = copy.copy(soup_or_element)
        
    mapping = []
    placeholder_idx = 0
    
    def should_protect_tag(tag):
        if tag.name in ['math', 'code', 'pre', 'script', 'style', 'mjx-container']:
            return True
        if tag.name == 'span':
            classes = tag.get('class', [])
            if isinstance(classes, str):
                classes = classes.split()
            elif classes is None:
                classes = []
            if 'os-math-in-para' in classes:
                return True
        if tag.name == 'em':
            return is_math_em(tag)
        return False
        
    # Protect tags
    tags = soup.find_all(should_protect_tag)
    for tag in tags:
        if tag.parent is None:
            continue
        placeholder = f"[[PROTECTED_TAG_{placeholder_idx}]]"
        mapping.append((placeholder, str(tag)))
        placeholder_idx += 1
        tag.replace_with(placeholder)
        
    # Protect text patterns
    patterns = [
        # Hypothesis markers: H0, Ha, H_0, H_a
        r'\bH[0a]\b',
        r'\bH_[0a]\b',
        # Variables with subscripts/indices: x1, x_1, y2, y_2, p1, p_1, p_hat, p_prime
        r'\b[xypntzF]\d+\b',
        r'\b[xypntzF]_[0-9a-zA-Z]+\b',
        # Inequality/equality equations (longer/more specific first, supporting dot/comma decimals)
        r'\b[a-zA-ZμσαβχρηλθπΣ]\b\s*[\<\>\=≤≥≠±≈]\s*-?\d+(?:[\.,]\d+)?',
        # Greek letters and math operators (shorter/fallback matches)
        r'[μσαβχρηλθπΣ≤≥≠±≈]',
        # Statistical terms
        r'\bp-value\b',
        r'\bz-score\b',
        r'\bt-score\b',
        r'\bdf\b'
    ]
    combined_regex = re.compile('|'.join(f'(?:{p})' for p in patterns))
    
    text_nodes = list(soup.find_all(string=True))
    for node in text_nodes:
        if node.parent is None:
            continue
        if node.parent.name in ['script', 'style', 'code', 'pre', 'math', 'mjx-container']:
            continue
            
        content = str(node)
        matches = list(combined_regex.finditer(content))
        if not matches:
            continue
            
        new_content = ""
        last_idx = 0
        for match in matches:
            matched_text = match.group(0)
            placeholder = f"[[PROTECTED_TAG_{placeholder_idx}]]"
            mapping.append((placeholder, matched_text))
            placeholder_idx += 1
            
            new_content += content[last_idx:match.start()] + placeholder
            last_idx = match.end()
        new_content += content[last_idx:]
        
        node.replace_with(new_content)
        
    if is_str:
        return str(soup), mapping
    return soup, mapping

def restore_math_and_formulas(soup_or_element, mapping):
    is_str = isinstance(soup_or_element, str)
    if is_str:
        html_str = soup_or_element
        for placeholder, original in mapping:
            html_str = html_str.replace(placeholder, original)
        return html_str
    else:
        if hasattr(soup_or_element, 'decode_contents'):
            html_str = soup_or_element.decode_contents().strip()
        else:
            html_str = str(soup_or_element)
        for placeholder, original in mapping:
            html_str = html_str.replace(placeholder, original)
        
        new_soup = BeautifulSoup(html_str, 'html.parser')
        if hasattr(soup_or_element, 'clear'):
            soup_or_element.clear()
            soup_or_element.extend(new_soup.contents)
        return soup_or_element

def extract_protected_items(soup_or_element):
    is_str = isinstance(soup_or_element, str)
    if is_str:
        _, mapping = protect_math_and_formulas(soup_or_element)
    else:
        if hasattr(soup_or_element, 'decode_contents'):
            inner = soup_or_element.decode_contents().strip()
        else:
            inner = str(soup_or_element)
        _, mapping = protect_math_and_formulas(inner)
    return [orig for placeholder, orig in mapping]

def normalize_item(item):
    cleaned = re.sub(r'\s+', '', item)
    cleaned = cleaned.replace("'", '"')
    return cleaned

def compare_protected_items(source_element, translated_element):
    source_items = extract_protected_items(source_element)
    trans_items = extract_protected_items(translated_element)
    
    if len(source_items) != len(trans_items):
        return False, f"Count mismatch: source has {len(source_items)}, translation has {len(trans_items)}."
        
    for idx, (src, trans) in enumerate(zip(source_items, trans_items)):
        if normalize_item(src) != normalize_item(trans):
            return False, f"Content mismatch at index {idx}: Expected '{src}', got '{trans}'"
            
    return True, ""

def restore_math_from_source(source_element, translated_element):
    src_items = extract_protected_items(source_element)
    
    if hasattr(translated_element, 'decode_contents'):
        trans_inner = translated_element.decode_contents().strip()
    else:
        trans_inner = str(translated_element)
        
    trans_protected_inner, trans_mapping = protect_math_and_formulas(trans_inner)
    
    if len(trans_mapping) == len(src_items):
        aligned_mapping = []
        for (placeholder, _), src_item in zip(trans_mapping, src_items):
            aligned_mapping.append((placeholder, src_item))
            
        healed_inner = restore_math_and_formulas(trans_protected_inner, aligned_mapping)
        new_soup = BeautifulSoup(healed_inner, 'html.parser')
        
        if hasattr(translated_element, 'clear'):
            translated_element.clear()
            translated_element.extend(new_soup.contents)
            
    return translated_element
