import os
import copy
from pathlib import Path
from bs4 import BeautifulSoup
from src.core.paths import get_clean_dir, get_prep_dir

TAGS_TO_DUPLICATE = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'caption', 'figcaption', 'th', 'td', 'dt', 'dd']

def add_classes(tag, class_list):
    """
    Safely append classes to a BeautifulSoup tag.
    """
    classes = tag.get('class', [])
    if isinstance(classes, str):
        classes = [c for c in classes.split() if c]
    elif classes is None:
        classes = []
    
    for c in class_list:
        if c not in classes:
            classes.append(c)
    tag['class'] = classes

def remove_classes(tag, class_list):
    """
    Safely remove classes from a BeautifulSoup tag.
    """
    classes = tag.get('class', [])
    if isinstance(classes, str):
        classes = [c for c in classes.split() if c]
    elif classes is None:
        classes = []
    
    tag['class'] = [c for c in classes if c not in class_list]

def prep_file(in_path, out_path):
    """
    Read an HTML file from 02-clean, duplicate translation block tags,
    mark English block as hidden, mark duplicated block as Vietnamese visible,
    append -vn to IDs, and write output to 04-prep.
    """
    with open(in_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # Enforce meta charset utf-8
    from src.utils.html_encoding import ensure_meta_charset_utf8
    ensure_meta_charset_utf8(soup)

    # Ensure stylesheet link
    from src.exporters.html_exporter import ensure_stylesheet_link
    ensure_stylesheet_link(soup, "../../css/style.css")

    # Add style to head if head exists and style doesn't already exist
    head = soup.find('head')
    if head:
        style_exists = False
        for s in head.find_all('style'):
            if s.string and ".eng.hidden" in s.string:
                style_exists = True
                break
        if not style_exists:
            style = soup.new_tag('style')
            style.string = "\n.eng.hidden { display: none; }\n.vn.visible { color: #000; }\n"
            head.append(style)

    # Collect all elements to duplicate
    targets = []
    for tag_name in TAGS_TO_DUPLICATE:
        targets.extend(soup.find_all(tag_name))
    
    # Also find div elements with class "os-caption-container" (table captions)
    for tag in soup.find_all('div', class_='os-caption-container'):
        if tag not in targets:
            targets.append(tag)

    for tag in targets:
        # Check if this tag contains any nested child tag that is also in targets
        contains_child_block = False
        for child in tag.find_all(recursive=True):
            if child in targets:
                contains_child_block = True
                break
        
        if contains_child_block:
            continue  # Skip outer tags, letting leaf tags be duplicated
        
        # Skip if already prepped as eng hidden
        classes = tag.get('class', [])
        if isinstance(classes, str):
            classes = classes.split()
        elif classes is None:
            classes = []
        if 'eng' in classes and 'hidden' in classes:
            continue

        # Duplicate the tag
        new_tag = copy.copy(tag)

        # Modify original tag to be English hidden
        add_classes(tag, ['eng', 'hidden'])

        # Modify duplicate tag to be Vietnamese visible
        remove_classes(new_tag, ['eng', 'hidden'])
        add_classes(new_tag, ['vn', 'visible'])

        # Suffix ID with -vn if present
        if new_tag.get('id'):
            new_tag['id'] = new_tag['id'] + '-vn'

        # Insert new tag immediately after original tag
        tag.insert_after(new_tag)

    # Save outputs
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))

def prep_chapter(book_slug, chapter, force=False):
    """
    Process all clean HTML files in the chapter, outputting to prep folder.
    """
    clean_dir = get_clean_dir(book_slug, chapter)
    prep_dir = get_prep_dir(book_slug, chapter)

    if not clean_dir.is_dir():
        raise FileNotFoundError(f"Source clean directory not found: {clean_dir}")

    html_files = sorted([f for f in os.listdir(clean_dir) if f.endswith('.html')])
    
    processed = []
    skipped = []
    failed = []

    if html_files:
        os.makedirs(prep_dir, exist_ok=True)

    for filename in html_files:
        in_file = clean_dir / filename
        out_file = prep_dir / filename

        if out_file.is_file() and not force:
            skipped.append(filename)
            continue

        try:
            prep_file(in_file, out_file)
            processed.append(filename)
        except Exception as e:
            failed.append({"file": filename, "error": str(e)})

    return {
        "processed": processed,
        "skipped": skipped,
        "failed": failed
    }
