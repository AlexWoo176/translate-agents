import os
import re
from pathlib import Path
from bs4 import BeautifulSoup
from src.core.paths import get_clean_dir, get_translated_dir, get_reviews_dir

BLOCK_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "caption", "figcaption", "th", "td"]
CONTAINER_TAGS = ["table", "figure"]
INLINE_TAGS = ["a", "span"]

def is_leaf_block(tag):
    """
    Check if this tag is a BLOCK_TAG and contains no other nested BLOCK_TAG elements.
    We ignore block tags that are nested inside container tags (like table or figure)
    which are children of this tag.
    """
    if tag.name not in BLOCK_TAGS:
        return False
    for child in tag.find_all(BLOCK_TAGS):
        in_container = False
        for parent in child.parents:
            if parent is tag:
                break
            if parent.name in CONTAINER_TAGS:
                in_container = True
                break
        if not in_container:
            return False
    return True

def analyze_file_tags(filepath):
    """
    Analyze tags structure, leaf blocks, eng/vn blocks, and inline tags.
    """
    if not filepath.is_file():
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {"error": f"Failed to read file: {e}"}

    if not content.strip():
        return {"error": "Empty file"}

    try:
        soup = BeautifulSoup(content, "html.parser")
    except Exception as e:
        return {"error": f"Parse error: {e}"}

    # Count leaf block tags
    leaf_blocks = {}
    for tag_name in BLOCK_TAGS:
        leaf_blocks[tag_name] = 0
    for tag in soup.find_all(BLOCK_TAGS):
        if is_leaf_block(tag):
            leaf_blocks[tag.name] = leaf_blocks.get(tag.name, 0) + 1

    # Count container tags
    containers = {}
    for tag_name in CONTAINER_TAGS:
        containers[tag_name] = len(soup.find_all(tag_name))

    # Identify and pair eng/vn blocks
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

    eng_hidden_counts = {}
    vn_visible_counts = {}
    for tag_name in BLOCK_TAGS:
        eng_hidden_counts[tag_name] = 0
        vn_visible_counts[tag_name] = 0

    for el in eng_blocks:
        if is_leaf_block(el):
            eng_hidden_counts[el.name] = eng_hidden_counts.get(el.name, 0) + 1
        else:
            for child in el.find_all(BLOCK_TAGS):
                if is_leaf_block(child):
                    eng_hidden_counts[child.name] = eng_hidden_counts.get(child.name, 0) + 1

    for el in vn_blocks:
        if is_leaf_block(el):
            vn_visible_counts[el.name] = vn_visible_counts.get(el.name, 0) + 1
        else:
            for child in el.find_all(BLOCK_TAGS):
                if is_leaf_block(child):
                    vn_visible_counts[child.name] = vn_visible_counts.get(child.name, 0) + 1

    return {
        "content_empty": False,
        "leaf_blocks": leaf_blocks,
        "containers": containers,
        "eng_blocks": eng_blocks,
        "vn_blocks": vn_blocks,
        "eng_hidden_counts": eng_hidden_counts,
        "vn_visible_counts": vn_visible_counts,
        "soup": soup,
        "size_bytes": os.path.getsize(filepath)
    }

def check_file_integrity(clean_path, trans_path):
    """
    Compare clean vs translated HTML file for integrity issues.
    """
    clean_stats = analyze_file_tags(clean_path)
    if not clean_stats:
        return {"status": "FAIL", "issues": [f"Source clean file {clean_path} not found"]}
        
    trans_stats = analyze_file_tags(trans_path)
    if not trans_stats:
        return {"status": "FAIL", "issues": [f"Translated file {trans_path} not found"]}

    if "error" in trans_stats:
        return {"status": "FAIL", "issues": [f"Translated file error: {trans_stats['error']}"]}

    issues = []

    # Verify presence of eng/vn blocks if clean has text blocks
    total_clean_blocks = sum(clean_stats["leaf_blocks"].values())
    total_trans_eng = len(trans_stats["eng_blocks"])
    total_trans_vn = len(trans_stats["vn_blocks"])

    if total_clean_blocks > 0:
        if total_trans_eng == 0:
            issues.append("Translated file does not contain any .eng.hidden blocks")
        if total_trans_vn == 0:
            issues.append("Translated file does not contain any .vn.visible blocks")

    # 1. Check leaf block tag counts matching between clean and translated
    for tag in BLOCK_TAGS:
        clean_cnt = clean_stats["leaf_blocks"].get(tag, 0)
        eng_cnt = trans_stats["eng_hidden_counts"].get(tag, 0)
        vn_cnt = trans_stats["vn_visible_counts"].get(tag, 0)

        if clean_cnt > 0 and eng_cnt != clean_cnt:
            issues.append(
                f"Mismatched <{tag}> counts: clean has {clean_cnt}, translated .eng.hidden has {eng_cnt}"
            )
        if eng_cnt != vn_cnt:
            issues.append(
                f"Mismatched <{tag}> counts inside translation pairs: .eng.hidden has {eng_cnt}, .vn.visible has {vn_cnt}"
            )

    # 2. Check container tags matching
    for tag in CONTAINER_TAGS:
        clean_cnt = clean_stats["containers"].get(tag, 0)
        trans_cnt = trans_stats["containers"].get(tag, 0)
        if clean_cnt != trans_cnt:
            issues.append(
                f"Mismatched container <{tag}> counts: clean has {clean_cnt}, translated has {trans_cnt}"
            )

    # 3. Check inline tags inside matching block pairings
    # Pair eng_blocks and vn_blocks by ID (or sequence index fallback)
    vn_by_id = {}
    for el in trans_stats["vn_blocks"]:
        el_id = el.get("id")
        if el_id:
            vn_by_id[el_id] = el

    pairs = []
    unpaired_vn = list(trans_stats["vn_blocks"])

    for eng_el in trans_stats["eng_blocks"]:
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

    # Fallback to sequential index matching
    for eng_el in trans_stats["eng_blocks"]:
        if any(p[0] is eng_el for p in pairs):
            continue
        if unpaired_vn:
            paired = unpaired_vn.pop(0)
            pairs.append((eng_el, paired))

    # Analyze inline tag matching in pairs
    for eng_el, vn_el in pairs:
        eng_id_str = eng_el.get('id', '(no-id)')
        for tag in INLINE_TAGS:
            eng_inline_cnt = len(eng_el.find_all(tag))
            vn_inline_cnt = len(vn_el.find_all(tag))
            if eng_inline_cnt != vn_inline_cnt:
                issues.append(
                    f"Mismatched inline <{tag}> inside block ID '{eng_id_str}': "
                    f"English has {eng_inline_cnt}, Vietnamese has {vn_inline_cnt}"
                )

    # 4. Check for untranslated (English leak) blocks
    soup = trans_stats["soup"]
    for tag_name in BLOCK_TAGS:
        for tag in soup.find_all(tag_name):
            classes = tag.get('class', []) or []
            if isinstance(classes, str):
                classes = classes.split()
            
            if 'eng' not in classes and 'vn' not in classes:
                # Check if any parent has eng or vn class
                has_bilingual_parent = False
                for parent in tag.parents:
                    if parent is None or parent.name == '[document]':
                        break
                    p_classes = parent.get('class', []) or []
                    if isinstance(p_classes, str):
                        p_classes = p_classes.split()
                    if 'eng' in p_classes or 'vn' in p_classes:
                        has_bilingual_parent = True
                        break
                
                if not has_bilingual_parent:
                    # Ignore if the tag contains no meaningful text content
                    text = tag.get_text(strip=True)
                    if text:
                        snippet = text[:60]
                        tag_id = tag.get('id', '(no-id)')
                        issues.append(
                            f"English Leak: Untranslated block <{tag_name}> id='{tag_id}' found: \"{snippet}...\""
                        )

    status = "FAIL" if issues else "PASS"
    
    return {
        "status": status,
        "issues": issues,
        "clean_size": clean_stats["size_bytes"],
        "trans_size": trans_stats["size_bytes"]
    }
