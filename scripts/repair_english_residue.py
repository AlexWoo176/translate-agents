import os
import re
import argparse
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from src.core.config import get_config
from src.core.paths import get_book_root, get_chapter_root

# Heuristics & stopwords identical to audit script
ENGLISH_STOPWORDS = {
    'the', 'and', 'of', 'to', 'in', 'is', 'that', 'it', 'for', 'on', 'with', 'as', 'this',
    'are', 'by', 'an', 'be', 'at', 'or', 'if', 'suppose', 'reject', 'fail', 'null', 'hypothesis',
    'probability', 'sample', 'mean', 'standard', 'deviation', 'confidence', 'interval', 'population',
    'distribution', 'test', 'value', 'data', 'we', 'from', 'which', 'random', 'variable', 'following',
    'under', 'between', 'each', 'results', 'conclude', 'evidence', 'interpret', 'suppose', 'determine',
    'calculate', 'find', 'using', 'given', 'show', 'table', 'where', 'then', 'there', 'has', 'have', 'been'
}

VN_DIACRITICS_RE = re.compile(
    r'[áàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ'
    r'ÁÀẢÃẠÂẤẦẨẪẬĂẮẰẲẴẶÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ]'
)

ALLOWED_TERMS = {
    'h0', 'ha', 'p-value', 'z-score', 'x̄', 'μ', 'σ', 'α', 'beta', 'df', 'chi-square',
    'openstax', 'creative commons', 'attribution', 'license', 'sd', 'n1', 'n2', 'ti-83', 'ti-84'
}

def get_norm_words(text):
    clean = re.sub(r'[^a-zA-Z\s]', '', text.lower())
    return clean.split()

def detect_english_residue(text):
    text_stripped = text.strip()
    if not text_stripped or len(text_stripped) < 4:
        return False
        
    words = get_norm_words(text_stripped)
    if not words:
        return False
        
    stopwords_found = [w for w in words if w in ENGLISH_STOPWORDS]
    stopword_ratio = len(stopwords_found) / len(words)
    
    vn_chars = VN_DIACRITICS_RE.findall(text_stripped)
    
    # Heuristics:
    if len(vn_chars) == 0 and len(words) >= 2:
        # Check if the words are mostly allowed tech terms
        non_allowed = [w for w in words if w not in ALLOWED_TERMS and not w.isdigit()]
        if len(non_allowed) >= 1:
            return True
            
    return False

def translate_block(eng_html, api_key, model="gemini-3.1-flash-lite"):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    system_instruction = (
        "You are a professional academic translator specializing in introductory statistics textbooks. "
        "Translate the given HTML/text snippet from English to Vietnamese. "
        "Strictly preserve all HTML tags, classes, and attributes. Translate only the human-readable text. "
        "Do not translate proper names of software/tools (like TI-83, TI-84). "
        "Use 'Bạn' for 'you' and 'Chúng ta' for 'we'. "
        "Return ONLY the translated HTML/text. Do not include markdown code block formatting (like ```html)."
    )
    
    contents = {
        "contents": [{"parts": [{"text": eng_html}]}],
        "generationConfig": {
            "temperature": 0.2
        },
        "systemInstruction": {"parts": [{"text": system_instruction}]}
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=contents, headers=headers, timeout=45)
            if response.status_code == 200:
                res_data = response.json()
                parts = res_data["candidates"][0]["content"]["parts"]
                text_parts = [p["text"] for p in parts if not p.get("thought")]
                if not text_parts:
                    text_parts = [parts[-1]["text"]]
                translated = "".join(text_parts).strip()
                if translated.startswith("```"):
                    translated = re.sub(r"^```[a-zA-Z]*\n", "", translated)
                    translated = re.sub(r"\n```$", "", translated)
                    translated = translated.strip()
                return translated
            else:
                print(f"  API Error ({response.status_code}): {response.text}")
        except Exception as e:
            print(f"  Request Exception (attempt {attempt+1}): {e}")
        import time
        time.sleep(2 ** attempt + 1)
    return None

def main():
    parser = argparse.ArgumentParser(description="Repair English residue in translated files.")
    parser.add_argument("--book", default="introductory-statistics-2e", help="Book slug name")
    parser.add_argument("--chapter", default="1", help="Chapter identifier")
    parser.add_argument("--model", default="gemini-3.1-flash-lite", help="API Model name to use")
    args = parser.parse_args()

    book_slug = args.book
    chapter_num = args.chapter

    ch_slug = f"chapter-{chapter_num}"
    ch_root = get_book_root(book_slug) / ch_slug
    trans_dir = ch_root / "05-translated"

    if not trans_dir.is_dir():
        print(f"Error: Translated directory {trans_dir} does not exist.")
        return 1

    api_key = get_config("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is missing.")
        return 1

    print(f"Scanning translated files in {trans_dir} for Chapter {chapter_num}...")
    repaired_count = 0

    for f in trans_dir.glob("*.html"):
        soup = BeautifulSoup(f.read_text(encoding="utf-8"), "html.parser")
        file_modified = False

        # --- Part 1: Standard .vn.visible blocks ---
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

        for el_vn in vn_elements:
            vn_text = el_vn.get_text().strip()
            if not vn_text:
                continue

            vn_id = el_vn.get("id", "")
            eng_id = vn_id.replace("-vn", "") if vn_id.endswith("-vn") else vn_id
            el_eng = soup.find(id=eng_id)
            eng_text = el_eng.get_text().strip() if el_eng else ""

            # Check if Vietnamese text is English residue
            if detect_english_residue(vn_text):
                print(f"[{f.name}] Detected English residue in block '{vn_id}':")
                print(f"  Text: {ascii(vn_text)}")
                
                # Check if it contains math tags
                if el_vn.find(['math', 'semantics', 'annotation', 'mi', 'mo', 'mn', 'mrow', 'msup', 'msub']):
                    print("  -> Skipped (contains math tags)")
                    continue

                # Check if it needs translation (ignore purely math/numbers)
                words = get_norm_words(vn_text)
                non_allowed = [w for w in words if w not in ALLOWED_TERMS and not w.isdigit()]
                if len(non_allowed) < 2:
                    print("  -> Skipped (mostly math or symbols)")
                    continue

                if el_eng:
                    source_html = el_eng.decode_contents().strip()
                else:
                    source_html = el_vn.decode_contents().strip()

                print(f"  -> Translating snippet: {ascii(source_html[:80])}...")
                translated = translate_block(source_html, api_key, model=args.model)
                if translated:
                    print(f"  -> Translation received: {ascii(translated[:80])}")
                    el_vn.clear()
                    temp_soup = BeautifulSoup(translated, "html.parser")
                    for child in temp_soup.contents:
                        el_vn.append(child)
                    file_modified = True
                    repaired_count += 1
                else:
                    print("  -> Translation failed.")

        # --- Part 2: Table/Figure caption / titles (os-caption-container) ---
        caption_divs = soup.find_all(['div', 'figcaption'], class_='os-caption-container')
        for div_vn in caption_divs:
            classes = div_vn.get('class', [])
            if 'vn' in classes and 'visible' in classes:
                # Find matching English sibling caption
                div_eng = div_vn.find_previous_sibling(div_vn.name, class_='os-caption-container')
                if div_eng and 'eng' in div_eng.get('class', []) and 'hidden' in div_eng.get('class', []):
                    # Check os-title or os-caption span inside
                    span_vn = div_vn.find('span', class_=['os-title', 'os-caption'])
                    span_eng = div_eng.find('span', class_=['os-title', 'os-caption'])
                    if span_vn and span_eng:
                        vn_title = span_vn.get_text().strip()
                        eng_title = span_eng.get_text().strip()
                        if detect_english_residue(vn_title) and vn_title == eng_title:
                            print(f"[{f.name}] Detected untranslated table/figure title:")
                            print(f"  Title: {ascii(vn_title)}")
                            print(f"  -> Translating table/figure title...")
                            translated = translate_block(eng_title, api_key, model=args.model)
                            if translated:
                                print(f"  -> Translation received: {ascii(translated)}")
                                span_vn.string = translated
                                file_modified = True
                                repaired_count += 1
                            else:
                                print("  -> Translation failed.")
                    
                    # Also localize label span (e.g., Table -> Bảng, Figure -> Hình)
                    label_vn = div_vn.find('span', class_='os-title-label')
                    if label_vn:
                        lbl_text = label_vn.get_text()
                        if "Table" in lbl_text:
                            label_vn.string = lbl_text.replace("Table", "Bảng")
                            file_modified = True
                        elif "Figure" in lbl_text:
                            label_vn.string = lbl_text.replace("Figure", "Hình")
                            file_modified = True

        if file_modified:
            from src.utils.html_encoding import ensure_meta_charset_utf8
            ensure_meta_charset_utf8(soup)
            f.write_text(str(soup), encoding="utf-8")
            print(f"[{f.name}] Saved repaired changes.")

    print(f"Repairs completed! Translated and replaced {repaired_count} block(s).")
    return 0

if __name__ == "__main__":
    main()
