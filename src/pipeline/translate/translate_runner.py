import os
import re
import json
import time
import shutil
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from src.utils.html_encoding import ensure_meta_charset_utf8
from src.core.paths import get_book_root, get_chapter_root, get_prep_dir, get_translated_dir, get_reviews_dir
from src.core.config import get_config
from src.qa.glossary_check import load_glossary
from src.utils.status_helper import update_status
from src.pipeline.translate.math_protection import (
    protect_math_and_formulas,
    restore_math_and_formulas,
    compare_protected_items,
    restore_math_from_source
)

def has_translatable_text(element):
    """
    Check if a BeautifulSoup element has alphabetical text to translate.
    """
    text = element.get_text()
    return bool(re.search(r'[a-zA-Z]', text))

def protect_structures(html_str):
    """
    Find tag structures like math, code, pre, script, and style,
    replace them with unique placeholders in-memory, and return
    the modified HTML string and placeholders mapping.
    """
    return protect_math_and_formulas(html_str)

def restore_structures(html_str, protected):
    """
    Restore saved tag structures in place of placeholders.
    """
    return restore_math_and_formulas(html_str, protected)

def validate_translation_integrity(original_inner_html, translated_inner_html):
    """
    Ensure no HTML structures or sensitive attributes were modified or removed.
    """
    try:
        orig_soup = BeautifulSoup(original_inner_html, 'html.parser')
        trans_soup = BeautifulSoup(translated_inner_html, 'html.parser')
        
        # Unwrap formatting tags like sup, sub, strong, em, b, i as they may not be preserved in Vietnamese
        for tag in orig_soup.find_all(['sup', 'sub', 'strong', 'em', 'b', 'i']):
            tag.unwrap()
        for tag in trans_soup.find_all(['sup', 'sub', 'strong', 'em', 'b', 'i']):
            tag.unwrap()
    except Exception as e:
        return False, f"Parser error: {e}"

    orig_tags = [t.name for t in orig_soup.find_all()]
    trans_tags = [t.name for t in trans_soup.find_all()]

    if orig_tags != trans_tags:
        return False, f"Tag structure mismatch. Expected: {orig_tags}, Got: {trans_tags}"

    for t_orig, t_trans in zip(orig_soup.find_all(), trans_soup.find_all()):
        if t_orig.attrs.keys() != t_trans.attrs.keys():
            return False, f"Attribute keys mismatch on <{t_orig.name}>. Expected: {list(t_orig.attrs.keys())}, Got: {list(t_trans.attrs.keys())}"
            
        for attr, val in t_orig.attrs.items():
            if attr in ['id', 'class', 'href', 'src'] or (attr.startswith('data-') and attr != 'data-alt'):
                if t_trans.attrs[attr] != val:
                    return False, f"Attribute '{attr}' value changed on <{t_orig.name}>. Expected '{val}', Got '{t_trans.attrs[attr]}'"

    return True, ""

def get_vn_blocks(soup):
    vn_elements = []
    block_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'caption', 'figcaption', 'th', 'td', 'dt', 'dd']
    for tag_name in block_tags:
        for tag in soup.find_all(tag_name):
            classes = tag.get('class', [])
            if isinstance(classes, str):
                classes = classes.split()
            elif classes is None:
                classes = []
            if 'vn' in classes and 'visible' in classes:
                vn_elements.append(tag)
    return vn_elements

def get_eng_blocks(soup):
    eng_elements = []
    block_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'caption', 'figcaption', 'th', 'td', 'dt', 'dd']
    for tag_name in block_tags:
        for tag in soup.find_all(tag_name):
            classes = tag.get('class', [])
            if isinstance(classes, str):
                classes = classes.split()
            elif classes is None:
                classes = []
            if 'eng' in classes and 'hidden' in classes:
                eng_elements.append(tag)
    return eng_elements

def validate_agent_translation(prep_dir, translated_dir, html_files):
    """
    Check if the translated files in translated_dir have actually been translated.
    Returns (is_valid, error_msg, processed_info)
    """
    processed = []
    failed = []
    
    for filename in html_files:
        prep_path = prep_dir / filename
        trans_path = translated_dir / filename
        
        if not trans_path.is_file():
            failed.append({"file": filename, "error": "Translated file is missing."})
            continue
            
        try:
            with open(prep_path, "r", encoding="utf-8") as f:
                prep_soup = BeautifulSoup(f.read(), "html.parser")
            with open(trans_path, "r", encoding="utf-8") as f:
                trans_soup = BeautifulSoup(f.read(), "html.parser")
        except Exception as e:
            failed.append({"file": filename, "error": f"Failed to parse file: {e}"})
            continue
            
        prep_vn = get_vn_blocks(prep_soup)
        trans_vn = get_vn_blocks(trans_soup)
        trans_eng = get_eng_blocks(trans_soup)
        
        if len(prep_vn) != len(trans_vn):
            failed.append({"file": filename, "error": f"Block count mismatch. Expected {len(prep_vn)} blocks, got {len(trans_vn)}."})
            continue
            
        # Pair eng blocks by ID to compare text
        trans_eng_by_id = {}
        for el in trans_eng:
            el_id = el.get("id")
            if el_id:
                trans_eng_by_id[el_id] = el
                
        total_translatable = 0
        untranslated_count = 0
        integrity_issues = []
        file_modified = False
        
        for idx, el_vn in enumerate(trans_vn):
            if not has_translatable_text(el_vn):
                continue
            total_translatable += 1
            
            vn_id = el_vn.get("id", "")
            eng_id = vn_id.replace("-vn", "") if vn_id.endswith("-vn") else vn_id
            
            el_eng = trans_eng_by_id.get(eng_id)
            if el_eng:
                if el_vn.get_text().strip() == el_eng.get_text().strip():
                    untranslated_count += 1
                    
            orig_vn_el = prep_vn[idx]
            
            # Auto-heal math/formulas from source block
            before_heal = str(el_vn)
            restore_math_from_source(orig_vn_el, el_vn)
            if str(el_vn) != before_heal:
                file_modified = True
                
            # Math validation/comparison check
            valid_math, math_err = compare_protected_items(orig_vn_el, el_vn)
            if not valid_math:
                integrity_issues.append(f"Block '{vn_id}': Math validation failed: {math_err}")
                continue
                
            # Run integrity checks comparing to original prepped block
            valid, err_msg = validate_translation_integrity(orig_vn_el.decode_contents().strip(), el_vn.decode_contents().strip())
            if not valid:
                integrity_issues.append(f"Block '{vn_id}': {err_msg}")
                
        if integrity_issues:
            failed.append({"file": filename, "error": "; ".join(integrity_issues)})
        elif total_translatable > 0 and untranslated_count == total_translatable:
            failed.append({"file": filename, "error": "File is completely untranslated."})
        elif untranslated_count > 0:
            failed.append({"file": filename, "error": f"File is partially untranslated ({untranslated_count} blocks match English)."})
        else:
            if file_modified:
                try:
                    ensure_meta_charset_utf8(trans_soup)
                    with open(trans_path, "w", encoding="utf-8") as f:
                        f.write(str(trans_soup))
                except Exception as e:
                    failed.append({"file": filename, "error": f"Failed to save healed file: {e}"})
                    continue
            processed.append({"file": filename, "blocks": total_translatable, "fallbacks": 0})
            
    if failed:
        return False, "Some files failed validation", {"processed": processed, "skipped": [], "failed": failed}
    return True, "", {"processed": processed, "skipped": [], "failed": []}

def call_gemini_api(prompt, system_instruction, model, api_key):
    """
    Execute HTTP REST POST request to Gemini API.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    contents = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2
        }
    }
    if system_instruction:
        contents["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        
    max_retries = 3
    last_err = None
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=contents, headers=headers, timeout=90)
            if response.status_code == 200:
                res_data = response.json()
                parts = res_data["candidates"][0]["content"]["parts"]
                text_parts = [p["text"] for p in parts if not p.get("thought")]
                if not text_parts:
                    text_parts = [parts[-1]["text"]]
                return "".join(text_parts).strip()
            elif response.status_code == 429:
                last_err = f"Status 429: {response.text}"
                time.sleep(2 ** attempt * 2 + 1)
            else:
                raise Exception(f"Gemini API returned status code {response.status_code}: {response.text}")
        except requests.exceptions.RequestException as e:
            last_err = str(e)
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt * 2 + 1)
            
    raise Exception(f"Max retries exceeded for Gemini API call. Last error: {last_err}")

def call_gemini_api_for_items(items, glossary, analysis_notes, book_slug, chapter, system_instruction, model, api_key):
    """
    Wrapper to format prompts and check basic JSON response constraints.
    """
    glossary_str = "\n".join([f"- {g['term']} -> {g['translation']}" for g in glossary])
    
    send_items = []
    for item in items:
        send_items.append({
            "id": item["id"],
            "source_html": item["protected_html"]
        })
    items_json = json.dumps(send_items, ensure_ascii=False, indent=2)
    
    prompt = f"Book: {book_slug}\nChapter: {chapter}\n\n"
    if analysis_notes:
        prompt += f"Translation Guidelines/Analysis:\n{analysis_notes}\n\n"
    prompt += f"Glossary:\n{glossary_str}\n\n"
    prompt += f"Segments to translate:\n{items_json}\n\n"
    prompt += "Return the translated segments in a JSON array matching the exact structure: [ {\"id\": \"...\", \"translated_html\": \"...\"} ]"
    
    response_text = call_gemini_api(prompt, system_instruction, model, api_key)
    
    clean_json = response_text.strip()
    if clean_json.startswith("```json"):
        clean_json = clean_json[7:]
    if clean_json.endswith("```"):
        clean_json = clean_json[:-3]
    clean_json = clean_json.strip()
    
    results = json.loads(clean_json)
    
    if not isinstance(results, list):
        raise ValueError("API response is not a JSON list")
        
    ret_dict = {}
    for r in results:
        if not isinstance(r, dict) or "id" not in r or "translated_html" not in r:
            raise ValueError("API response item is missing required fields ('id' or 'translated_html')")
        ret_dict[r["id"]] = r["translated_html"]
        
    requested_ids = {item["id"] for item in items}
    returned_ids = set(ret_dict.keys())
    
    if requested_ids != returned_ids:
        raise ValueError(f"ID mismatch. Sent: {requested_ids}, Got: {returned_ids}")
        
    for r_id, trans_html in ret_dict.items():
        if trans_html is None or not str(trans_html).strip():
            raise ValueError(f"Empty translated_html returned for item '{r_id}'")
            
    return ret_dict

def _translate_chapter_impl(book_slug, chapter, file_filter=None, force=False, resume=False, dry_run=False, batch_size=50, model=None, provider="agent"):
    """
    Translate prepared bilingual HTML files from 04-prep to 05-translated.
    Supports provider: agent, gemini-api, manual.
    """
    prep_dir = get_prep_dir(book_slug, chapter)
    translated_dir = get_translated_dir(book_slug, chapter)
    reviews_dir = get_reviews_dir(book_slug, chapter)
    
    if not prep_dir.is_dir():
        raise FileNotFoundError(f"Source prep directory not found: {prep_dir}")

    html_files = sorted([f for f in os.listdir(prep_dir) if f.endswith('.html')])
    if file_filter:
        html_files = [f for f in html_files if f == file_filter]
        if not html_files:
            raise FileNotFoundError(f"Filter specified file '{file_filter}' not found in prep directory.")

    if provider == "gemini-api":
        # Verify GEMINI_API_KEY
        api_key = get_config("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable or config value is missing.")
            
        if not model:
            model = get_config("DEFAULT_MODEL", "gemini-3.5-flash")
        backup_model = get_config("BACKUP_MODEL", "gemini-3.1-flash-lite")

        glossary_path = get_book_root(book_slug) / "glossary.csv"
        glossary = load_glossary(glossary_path)
        
        processed = []
        skipped = []
        failed = []
        
        system_instruction = (
            "You are a professional academic translator specializing in educational textbooks. "
            "Your task is to translate the natural language text inside HTML segments from English to Vietnamese. "
            "Strictly adhere to the following rules:\n"
            "1. DO NOT translate, modify, or corrupt any HTML tags, classes, attributes, ids, or structure. Return them exactly as they are.\n"
            "2. Keep all inline tags (like <span>, <a>, <em>, <strong>, <sup>, <sub>, MathML tags like <math>, <mfrac>, <msub> etc.) and math placeholders like [[MATH_000001]] in their correct relative positions. Translate only the surrounding text and the text inside them. You must strictly preserve the exact tag structure and placeholders; do not add, omit, or modify any HTML tags or math placeholders.\n"
            "3. Use the provided glossary mapping. Translate matching terms exactly as specified.\n"
            "4. Tone: Use 'Bạn' for 'you' and 'Chúng ta' for 'we'. Ensure the Vietnamese flow is natural, grammatically correct, and matches academic standards.\n"
            "5. Respond ONLY with a JSON array of objects, where each object has 'id' and 'translated_html'. Do not include any explanation or markdown formatting other than valid JSON."
        )

        for filename in html_files:
            in_file = prep_dir / filename
            out_file = translated_dir / filename
            
            # Check overwrite rules
            if out_file.is_file():
                if resume:
                    skipped.append({"file": filename, "reason": "Already exists, resume mode skips."})
                    continue
                elif not force:
                    failed_msg = "Output file already exists. Use --force to overwrite, or --resume to skip."
                    failed.append({"file": filename, "error": failed_msg})
                    continue
                    
            # Load analysis notes
            analysis_dir = get_chapter_root(book_slug, chapter) / "03-analyzed"
            analysis_file = analysis_dir / f"{filename.replace('.html', '')}-translate-analysis.md"
            analysis_notes = ""
            if analysis_file.is_file():
                try:
                    with open(analysis_file, "r", encoding="utf-8") as af:
                        analysis_notes = af.read()
                except Exception as ae:
                    print(f"Warning: Failed to read analysis file {analysis_file}: {ae}")

            print(f"Translating {filename}...")
            try:
                with open(in_file, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f.read(), 'html.parser')
                    
                # Locate all .vn.visible elements
                vn_elements = get_vn_blocks(soup)
                            
                # Map elements into translate items
                items = []
                item_idx = 0
                for el in vn_elements:
                    if has_translatable_text(el):
                        original_inner = el.decode_contents().strip()
                        protected_inner, protected_tags = protect_structures(original_inner)
                        items.append({
                            "id": f"item-{item_idx}",
                            "element": el,
                            "original_html": original_inner,
                            "protected_html": protected_inner,
                            "protected_tags": protected_tags,
                            "translated_html": None
                        })
                        item_idx += 1
                        
                if not items:
                    # No translatable text found, write file as is
                    if not dry_run:
                        os.makedirs(os.path.dirname(out_file), exist_ok=True)
                        ensure_meta_charset_utf8(soup)
                        with open(out_file, 'w', encoding='utf-8') as f:
                            f.write(str(soup))
                    processed.append({"file": filename, "blocks": 0, "fallbacks": 0})
                    continue
                    
                # Batch elements
                fallback_count = 0
                for b_idx in range(0, len(items), batch_size):
                    batch = items[b_idx:b_idx+batch_size]
                    
                    try:
                        # Attempt batch translation
                        ret_dict = call_gemini_api_for_items(batch, glossary, analysis_notes, book_slug, chapter, system_instruction, model, api_key)
                        for item in batch:
                            translated_protected = ret_dict[item["id"]]
                            translated_restored = restore_structures(translated_protected, item["protected_tags"])
                            
                            # Validate HTML integrity
                            valid, err_msg = validate_translation_integrity(item["original_html"], translated_restored)
                            if not valid:
                                raise ValueError(f"HTML integrity check failed: {err_msg}")
                                
                            item["translated_html"] = translated_restored
                        time.sleep(3)
                    except Exception as batch_err:
                        print(f"Batch {b_idx//batch_size} failed: {batch_err}. Falling back to element-by-element translation...")
                        fallback_count += 1
                        
                        # Individual fallback
                        for item in batch:
                            try:
                                # Attempt translation with primary model
                                ret_dict = call_gemini_api_for_items([item], glossary, analysis_notes, book_slug, chapter, system_instruction, model, api_key)
                                translated_protected = ret_dict[item["id"]]
                                translated_restored = restore_structures(translated_protected, item["protected_tags"])
                                
                                valid, err_msg = validate_translation_integrity(item["original_html"], translated_restored)
                                if not valid:
                                    raise ValueError(f"HTML integrity check failed on fallback: {err_msg}")
                                    
                                item["translated_html"] = translated_restored
                                time.sleep(3)
                            except Exception as single_err:
                                # Primary model failed on this item, try the backup model
                                print(f"Primary model failed on item {item['id']} due to: {single_err}. Trying backup model {backup_model}...")
                                try:
                                    ret_dict = call_gemini_api_for_items([item], glossary, analysis_notes, book_slug, chapter, system_instruction, backup_model, api_key)
                                    translated_protected = ret_dict[item["id"]]
                                    translated_restored = restore_structures(translated_protected, item["protected_tags"])
                                    
                                    valid, err_msg = validate_translation_integrity(item["original_html"], translated_restored)
                                    if not valid:
                                        raise ValueError(f"HTML integrity check failed on backup model fallback: {err_msg}")
                                        
                                    item["translated_html"] = translated_restored
                                    time.sleep(3)
                                except Exception as backup_err:
                                    raise Exception(f"Unrecoverable translation failure on item {item['id']} (both primary and backup models failed): {backup_err}") from backup_err

                # Apply translations to BeautifulSoup clone elements in memory
                for item in items:
                    el = item["element"]
                    el.clear()
                    snippet = BeautifulSoup(item["translated_html"], "html.parser")
                    el.extend(snippet.contents)

                # Atomic write
                if not dry_run:
                    os.makedirs(os.path.dirname(out_file), exist_ok=True)
                    ensure_meta_charset_utf8(soup)
                    with open(out_file, 'w', encoding='utf-8') as f:
                        f.write(str(soup))
                        
                processed.append({"file": filename, "blocks": len(items), "fallbacks": fallback_count})
            except Exception as e:
                failed.append({"file": filename, "error": str(e)})

        # Generate Report
        if not dry_run:
            os.makedirs(reviews_dir, exist_ok=True)
            report_file = reviews_dir / f"chapter-{chapter}-translation-run.md"
            write_run_report(report_file, book_slug, chapter, processed, skipped, failed, model, batch_size, resume, provider)
            
        return {
            "processed": processed,
            "skipped": skipped,
            "failed": failed
        }
        
    elif provider == "manual":
        processed = []
        skipped = []
        failed = []
        
        os.makedirs(translated_dir, exist_ok=True)
        for filename in html_files:
            in_file = prep_dir / filename
            out_file = translated_dir / filename
            
            if out_file.is_file():
                if resume:
                    skipped.append({"file": filename, "reason": "Already exists, resume mode skips."})
                    continue
                elif not force:
                    failed.append({"file": filename, "error": "Output file already exists. Use --force to overwrite, or --resume to skip."})
                    continue
            
            try:
                if not dry_run:
                    shutil.copy2(in_file, out_file)
                processed.append({"file": filename, "blocks": 0, "fallbacks": 0})
            except Exception as e:
                failed.append({"file": filename, "error": str(e)})
                
        if not dry_run:
            os.makedirs(reviews_dir, exist_ok=True)
            report_file = reviews_dir / f"chapter-{chapter}-translation-run.md"
            write_run_report(report_file, book_slug, chapter, processed, skipped, failed, "Manual Copying", batch_size, resume, provider)
            
        return {
            "processed": processed,
            "skipped": skipped,
            "failed": failed
        }
        
    elif provider == "agent":
        if force:
            processed = []
            skipped = []
            failed = []
            os.makedirs(translated_dir, exist_ok=True)
            for filename in html_files:
                in_file = prep_dir / filename
                out_file = translated_dir / filename
                try:
                    if not dry_run:
                        shutil.copy2(in_file, out_file)
                    processed.append({"file": filename, "blocks": 0, "fallbacks": 0})
                except Exception as e:
                    failed.append({"file": filename, "error": str(e)})
                    
            if not dry_run:
                os.makedirs(reviews_dir, exist_ok=True)
                report_file = reviews_dir / f"chapter-{chapter}-translation-run.md"
                write_run_report(report_file, book_slug, chapter, [], skipped, [{"file": f["file"], "error": "Forced template reset; translation required."} for f in processed] + failed, "Agent Translation", batch_size, resume, provider)
            return {
                "processed": [],
                "skipped": skipped,
                "failed": [{"file": f["file"], "error": "Forced template reset; translation required."} for f in processed] + failed
            }
            
        # Run validation
        is_valid, err_msg, val_results = validate_agent_translation(prep_dir, translated_dir, html_files)
        
        if is_valid:
            if not dry_run:
                os.makedirs(reviews_dir, exist_ok=True)
                report_file = reviews_dir / f"chapter-{chapter}-translation-run.md"
                write_run_report(report_file, book_slug, chapter, val_results["processed"], [], [], "Agent Validation Passed", batch_size, resume, provider)
            return val_results
            
        # Untranslated / partially translated -> Copy missing templates
        copy_errors = []
        os.makedirs(translated_dir, exist_ok=True)
        for filename in html_files:
            in_file = prep_dir / filename
            out_file = translated_dir / filename
            if not out_file.is_file():
                try:
                    if not dry_run:
                        shutil.copy2(in_file, out_file)
                except Exception as e:
                    copy_errors.append({"file": filename, "error": str(e)})
                    
        failed_list = val_results["failed"] + copy_errors
        
        if not dry_run:
            os.makedirs(reviews_dir, exist_ok=True)
            report_file = reviews_dir / f"chapter-{chapter}-translation-run.md"
            write_run_report(report_file, book_slug, chapter, val_results["processed"], val_results["skipped"], failed_list, "Agent In-Progress", batch_size, resume, provider)
            
        return {
            "processed": val_results["processed"],
            "skipped": val_results["skipped"],
            "failed": failed_list
        }
        
    else:
        raise ValueError(f"Unknown translation provider: {provider}")

def translate_chapter(book_slug, chapter, file_filter=None, force=False, resume=False, dry_run=False, batch_size=50, model=None, provider="agent"):
    res = _translate_chapter_impl(book_slug, chapter, file_filter, force, resume, dry_run, batch_size, model, provider)
    print(f"DEBUG Wrapper: _translate_chapter_impl returned {res}")
    
    if not dry_run and isinstance(res, dict):
        translated_dir = get_translated_dir(book_slug, chapter)
        prep_dir = get_prep_dir(book_slug, chapter)
        print(f"DEBUG Wrapper: translated_dir={translated_dir}, prep_dir={prep_dir}")
        try:
            html_files = sorted([f for f in os.listdir(prep_dir) if f.endswith('.html')])
            if file_filter:
                html_files = [f for f in html_files if f == file_filter]
                
            processed_filenames = {item["file"] for item in res.get("processed", []) if isinstance(item, dict) and "file" in item}
                
            from src.exporters.html_exporter import ensure_stylesheet_link
            for filename in html_files:
                out_file = translated_dir / filename
                print(f"DEBUG Wrapper: filename={filename}, processed={filename in processed_filenames}, out_file={out_file}, exists={out_file.is_file()}")
                if filename not in processed_filenames:
                    continue
                if out_file.is_file():
                    try:
                        with open(out_file, "r", encoding="utf-8") as f:
                            soup = BeautifulSoup(f.read(), "html.parser")
                        ensure_stylesheet_link(soup, "../../css/style.css")
                        ensure_meta_charset_utf8(soup)
                        with open(out_file, "w", encoding="utf-8") as f:
                            f.write(str(soup))
                    except Exception as e:
                        print(f"Warning: Failed to ensure style on {out_file}: {e}")
        except Exception as e:
            print(f"Warning: Post-translation style check failed: {e}")
            
    return res

def write_run_report(report_path, book_slug, chapter, processed, skipped, failed, model, batch_size, resume, provider):
    """
    Write detailed translation run report.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    
    # Consolidate status
    if provider == "agent" and failed:
        status_str = "TRANSLATING"
    elif provider == "manual" and not failed:
        status_str = "TRANSLATION_READY"
    elif failed:
        status_str = "TRANSLATION_BLOCKED"
    else:
        status_str = "TRANSLATED"
        
    lines = [
        f"# Translation Run Report (Provider: {provider}): Chapter {chapter}",
        "",
        f"- **Book:** {book_slug}",
        f"- **Run Time:** {timestamp}",
        f"- **Provider:** {provider}",
        f"- **Engine/Model:** {model}",
        f"- **Batch Size:** {batch_size}",
        f"- **Resume Mode:** {resume}",
        f"- **Resulting Status:** {status_str}",
        "",
        "## Summary Details",
        "",
        "| File Name | Status | Blocks | Details / Errors |",
        "|---|---|---|---|",
    ]
    
    for p in processed:
        lines.append(f"| `{p['file']}` | SUCCESS | {p.get('blocks', 0)} | - |")
        
    for s in skipped:
        lines.append(f"| `{s['file']}` | SKIPPED | 0 | {s.get('reason', 'Skipped')} |")
        
    for f in failed:
        lines.append(f"| `{f['file']}` | FAILED / IN_PROGRESS | 0 | {f['error']} |")
        
    lines.append("")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
