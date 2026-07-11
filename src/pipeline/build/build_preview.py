import os
import re
import shutil
from pathlib import Path
from src.core.paths import get_book_root, get_web_output_root, get_archive_dir
from src.reader.build_reader import copy_reader_assets, write_pages_js, generate_root_index
from src.utils.html_resources import normalize_preview_image_paths

def sort_html_files(file_name):
    """
    Extract chapter and section numbers to sort HTML documents sequentially.
    """
    match = re.match(r'^(\d+)(?:-(\d+))?-', file_name)
    if match:
        chap_num = int(match.group(1))
        sec_num = int(match.group(2)) if match.group(2) else -1
        
        if sec_num == -1:
            if 'introduction' in file_name:
                return (chap_num, 0)
            elif 'key-terms' in file_name:
                return (chap_num, 100)
            elif 'summary' in file_name:
                return (chap_num, 101)
            elif 'review-questions' in file_name:
                return (chap_num, 102)
            elif 'discussion-questions' in file_name:
                return (chap_num, 103)
            elif 'case-questions' in file_name:
                return (chap_num, 104)
            elif 'suggested-resources' in file_name:
                return (chap_num, 105)
            else:
                return (chap_num, 99)
        else:
            return (chap_num, sec_num)
    return (999, 999)

def build_preview(book_slug: str, mode: str = "bilingual", copy_to_web: bool = False):
    """
    Orchestrate preview compile operations.
    """
    book_root = get_book_root(book_slug)
    if not book_root.is_dir():
        return 1, f"Book directory '{book_root}' does not exist."

    output_dir = book_root / ".html"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy css if exists, otherwise fallback to copying standard template
    css_src = book_root / "css"
    css_dst = output_dir / "css"
    if css_src.is_dir():
        shutil.copytree(css_src, css_dst)
    
    # Ensure style.css is present in build css folder
    dst_style_css = css_dst / "style.css"
    if not dst_style_css.is_file():
        from src.core.config import WORKSPACE_ROOT
        src_template_css = WORKSPACE_ROOT / "src" / "templates" / "book-css" / "style.css"
        if src_template_css.is_file():
            css_dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_template_css, dst_style_css)

    # 2. Copy book-reader JS/CSS
    copy_reader_assets(output_dir)

    all_pages = []

    # 3. Process book-level preface files if available
    book_level_src = get_archive_dir(book_slug, "_book-level", mode, "html")
    book_level_dst = output_dir / "_book-level"
    
    if book_level_src.is_dir():
        book_level_dst.mkdir(parents=True, exist_ok=True)
        html_files = sorted([f for f in os.listdir(book_level_src) if f.endswith(".html")])
        for fname in html_files:
            src_file = book_level_src / fname
            dst_file = book_level_dst / fname
            
            with open(src_file, "r", encoding="utf-8") as f:
                content = f.read()

            all_pages.append(f"/_book-level/{fname}")
            content = inject_reader_scripts(content)
            
            with open(dst_file, "w", encoding="utf-8") as f:
                f.write(content)

        # Copy book-level assets
        bl_assets_src = book_root / "_book-level" / "assets"
        bl_assets_dst = book_level_dst / "assets"
        if bl_assets_src.is_dir():
            shutil.copytree(bl_assets_src, bl_assets_dst)

    # 4. Find and sort chapter folders
    chapter_folders = []
    for d in os.listdir(book_root):
        if d.startswith("chapter-") and (book_root / d).is_dir():
            chapter_folders.append(d)
            
    # Numeric sorting
    chapter_folders.sort(key=lambda x: int(x.split('-')[1]) if x.split('-')[1].isdigit() else 999)

    from src.qa.math_encoding_qa import run_math_encoding_qa
    qa_warnings = 0

    for chap in chapter_folders:
        chap_num = chap.split("-")[1]
        chap_src = get_archive_dir(book_slug, chap_num, mode, "html")
        chap_dst = output_dir / chap

        if not chap_src.is_dir():
            print(f"Warning: Chapter '{chap}' is not archived yet. Skipping from preview build.")
            continue

        chap_dst.mkdir(parents=True, exist_ok=True)
        
        # Sort and copy HTML files
        html_files = sorted([f for f in os.listdir(chap_src) if f.endswith(".html")], key=sort_html_files)
        for fname in html_files:
            src_file = chap_src / fname
            dst_file = chap_dst / fname

            # Run math/encoding QA checks on archived files
            qa_res = run_math_encoding_qa(src_file)
            if qa_res["status"] != "PASS":
                qa_warnings += len(qa_res["issues"])
                print(f"Warning: Math/Encoding QA check failed for archived file '{chap}/{fname}':")
                for issue in qa_res["issues"]:
                    print(f"  - {issue}")

            with open(src_file, "r", encoding="utf-8") as f:
                content = f.read()

            all_pages.append(f"/{chap}/{fname}")
            content = inject_reader_scripts(content)

            with open(dst_file, "w", encoding="utf-8") as f:
                f.write(content)


        # Copy chapter assets if exist
        assets_src = book_root / chap / "assets"
        assets_dst = chap_dst / "assets"
        if assets_src.is_dir():
            shutil.copytree(assets_src, assets_dst)

    # 5. Copy global glossary.csv if exists
    glossary_src = book_root / "glossary.csv"
    glossary_dst = output_dir / "glossary.csv"
    if glossary_src.is_file():
        shutil.copy2(glossary_src, glossary_dst)

    # 6. Generate page manifest and redirect index
    if all_pages:
        write_pages_js(output_dir, all_pages)
        first_page = all_pages[0]
    else:
        first_page = "/chapter-1/1-introduction.html"

    generate_root_index(output_dir, first_page, book_slug)

    if qa_warnings > 0:
        print(f"\nWarning: Math/encoding QA check detected {qa_warnings} issues in compiled preview content.")

    # 7. Copy to web output if copy-to-web is set

    if copy_to_web:
        web_output_dir = get_web_output_root() / book_slug
        if web_output_dir.exists():
            shutil.rmtree(web_output_dir)
        shutil.copytree(output_dir, web_output_dir)

    return 0, {
        "output_dir": output_dir,
        "total_pages": len(all_pages),
        "first_page": first_page
    }

def inject_reader_scripts(html_content: str) -> str:
    """
    Remove any pre-existing reader script blocks, normalize CSS refs, and inject reader imports.
    """
    # 1. Normalize css paths (chain from content, not html_content)
    content = html_content.replace('../../../css/style.css', '../css/style.css')
    content = content.replace('../../css/style.css', '../css/style.css')
    content = content.replace('../css/style.css', '../css/style.css')

    # 2. Normalize image asset paths using shared helper from html_resources
    content = normalize_preview_image_paths(content)

    # 3. De-duplicate/remove old reader script blocks
    content = re.sub(r'<script src="[^"]*book-pages\.js"></script>\n?', '', content)
    content = re.sub(r'<link rel="stylesheet" href="[^"]*book-reader\.css">\n?', '', content)
    content = re.sub(r'<script src="[^"]*book-reader\.js"></script>\n?', '', content)
    content = re.sub(r'<link href="[^"]*book-reader\.css" rel="stylesheet"/>\n?', '', content)

    # 4. Inject new scripts inside head tag
    pages_js = '<script src="../book-reader/book-pages.js"></script>\n'
    css_link = '<link rel="stylesheet" href="../book-reader/book-reader.css">\n'
    js_link = '<script src="../book-reader/book-reader.js"></script>\n'
    style_link = '<link rel="stylesheet" href="../css/style.css">\n' if 'css/style.css' not in content else ''
    
    if '</head>' in content:
        content = content.replace('</head>', f'{style_link}{pages_js}{css_link}{js_link}</head>')
        
    # 5. Inject book-reader class to body tag
    body_match = re.search(r'<body([^>]*)>', content, re.IGNORECASE)
    if body_match:
        attrs = body_match.group(1)
        if 'class="' in attrs:
            class_match = re.search(r'class="([^"]*)"', attrs)
            if class_match and 'book-reader' not in class_match.group(1).split():
                new_attrs = re.sub(r'class="([^"]*)"', r'class="\1 book-reader"', attrs)
                content = content[:body_match.start()] + f'<body{new_attrs}>' + content[body_match.end():]
        elif "class='" in attrs:
            class_match = re.search(r"class='([^']*)'", attrs)
            if class_match and 'book-reader' not in class_match.group(1).split():
                new_attrs = re.sub(r"class='([^']*)'", r"class='\1 book-reader'", attrs)
                content = content[:body_match.start()] + f'<body{new_attrs}>' + content[body_match.end():]
        else:
            new_attrs = attrs + ' class="book-reader"'
            content = content[:body_match.start()] + f'<body{new_attrs}>' + content[body_match.end():]

    return content
