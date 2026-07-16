import os
import sys
import shutil
import glob
import re

def sort_html_files(file_name):
    # Extract chapter and section numbers
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

def build_preview(book_dir="../entrepreneurship"):
    book_dir = os.path.abspath(book_dir)
    output_dir = os.path.join(book_dir, ".html")

    print(f"Building preview:")
    print(f"  book_dir   : {book_dir}")
    print(f"  output_dir : {output_dir}")

    # ── T5: Validate book_dir trước khi làm gì ────────────────────────────
    if not os.path.isdir(book_dir):
        print(f"\n❌ Không tìm thấy thư mục sách: {book_dir}")
        print("   Kiểm tra lại đường dẫn và chạy lại với path chính xác.")
        print("   Ví dụ: python3 build-preview.py ../entrepreneurship")
        sys.exit(1)

    if os.path.exists(output_dir):
        try:
            shutil.rmtree(output_dir)
            os.makedirs(output_dir)
        except PermissionError:
            print("Warning: PermissionError when cleaning .html directory. Attempting to overwrite files directly...")
    else:
        os.makedirs(output_dir)


    # 1. Copy css
    css_src = os.path.join(book_dir, "css")
    css_dst = os.path.join(output_dir, "css")
    if os.path.exists(css_src):
        shutil.copytree(css_src, css_dst, dirs_exist_ok=True)

    # 2. Copy book-reader from agent-archive/book-reader
    br_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "book-reader")
    br_dst = os.path.join(output_dir, "book-reader")
    if os.path.exists(br_src):
        shutil.copytree(br_src, br_dst, dirs_exist_ok=True)

    # Find and sort chapters
    chapter_dirs = [d for d in os.listdir(book_dir) if d.startswith("chapter-") and os.path.isdir(os.path.join(book_dir, d))]
    chapter_dirs.sort(key=lambda x: int(x.split('-')[1]) if x.split('-')[1].isdigit() else 999)

    all_pages = []

    # Process book-level front matter
    book_level_dir = "_book-level"
    book_level_src = os.path.join(book_dir, book_level_dir)
    book_level_dst = os.path.join(output_dir, book_level_dir)
    
    if os.path.exists(book_level_src):
        os.makedirs(book_level_dst, exist_ok=True)
        trans_src = os.path.join(book_level_src, "05-translated")
        trans_dst = book_level_dst
        if os.path.exists(trans_src):
            os.makedirs(trans_dst, exist_ok=True)
            for file_name in ['preface.html', 'index.html']:
                src_file = os.path.join(trans_src, file_name)
                dst_file = os.path.join(trans_dst, file_name)
                if os.path.exists(src_file):
                    with open(src_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    all_pages.append(f"/{book_level_dir}/{file_name}")
                    pages_js = '<script src="../book-reader/book-pages.js"></script>\n'
                    css_link = '<link rel="stylesheet" href="../book-reader/book-reader.css">\n'
                    js_link = '<script src="../book-reader/book-reader.js"></script>\n'
                    content = content.replace('../../../css/style.css', '../css/style.css').replace('../../css/style.css', '../css/style.css').replace('../css/style.css', '../css/style.css')
                    content = content.replace('../assets/', 'assets/')
                    # Remove old injected relative scripts if they exist
                    content = content.replace('<script src="../../book-reader/book-pages.js"></script>\n', '')
                    content = content.replace('<link rel="stylesheet" href="../../book-reader/book-reader.css">\n', '')
                    content = content.replace('<script src="../../book-reader/book-reader.js"></script>\n', '')
                    content = content.replace('<link href="../../book-reader/book-reader.css" rel="stylesheet"/>\n', '')
                    content = content.replace('<script src="../book-reader/book-pages.js"></script>\n', '')
                    content = content.replace('<link rel="stylesheet" href="../book-reader/book-reader.css">\n', '')
                    content = content.replace('<script src="../book-reader/book-reader.js"></script>\n', '')
                    content = content.replace('<link href="../book-reader/book-reader.css" rel="stylesheet"/>\n', '')
                    if '</head>' in content and 'book-pages.js' not in content:
                        content = content.replace('</head>', f'{pages_js}{css_link}{js_link}</head>')
                    with open(dst_file, 'w', encoding='utf-8') as f:
                        f.write(content)
        
        # Copy book-level assets if any
        assets_src = os.path.join(book_level_src, "assets")
        assets_dst = os.path.join(book_level_dst, "assets")
        if os.path.exists(assets_src):
            shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)

    for chap in chapter_dirs:
        chap_src = os.path.join(book_dir, chap)
        chap_dst = os.path.join(output_dir, chap)
        os.makedirs(chap_dst, exist_ok=True)

        trans_src = os.path.join(chap_src, "05-translated")
        trans_dst = chap_dst
        
        if os.path.exists(trans_src):
            os.makedirs(trans_dst, exist_ok=True)
            
            # Sort files in this chapter
            html_files = [f for f in os.listdir(trans_src) if f.endswith('.html')]
            html_files.sort(key=sort_html_files)
            
            for file_name in html_files:
                src_file = os.path.join(trans_src, file_name)
                dst_file = os.path.join(trans_dst, file_name)
                with open(src_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Add to all pages list with absolute path from the root
                all_pages.append(f"/{chap}/{file_name}")
                
                # Inject scripts
                pages_js = '<script src="../book-reader/book-pages.js"></script>\n'
                css_link = '<link rel="stylesheet" href="../book-reader/book-reader.css">\n'
                js_link = '<script src="../book-reader/book-reader.js"></script>\n'
                content = content.replace('../../../css/style.css', '../css/style.css').replace('../../css/style.css', '../css/style.css').replace('../css/style.css', '../css/style.css')
                content = content.replace('../assets/', 'assets/')
                # Remove old injected relative scripts if they exist
                content = content.replace('<script src="../../book-reader/book-pages.js"></script>\n', '')
                content = content.replace('<link rel="stylesheet" href="../../book-reader/book-reader.css">\n', '')
                content = content.replace('<script src="../../book-reader/book-reader.js"></script>\n', '')
                content = content.replace('<link href="../../book-reader/book-reader.css" rel="stylesheet"/>\n', '')
                content = content.replace('<script src="../book-reader/book-pages.js"></script>\n', '')
                content = content.replace('<link rel="stylesheet" href="../book-reader/book-reader.css">\n', '')
                content = content.replace('<script src="../book-reader/book-reader.js"></script>\n', '')
                content = content.replace('<link href="../book-reader/book-reader.css" rel="stylesheet"/>\n', '')
                
                if '</head>' in content and 'book-pages.js' not in content:
                    content = content.replace('</head>', f'{pages_js}{css_link}{js_link}</head>')
                    
                with open(dst_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            print(f"Copied and injected into {chap}/")

        # assets
        assets_src = os.path.join(chap_src, "assets")
        assets_dst = os.path.join(chap_dst, "assets")
        if os.path.exists(assets_src):
            shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)

    # Process book-level back matter
    book_level_trans_src = os.path.join(book_level_src, "05-translated")
    book_level_trans_dst = book_level_dst
    if os.path.exists(book_level_src) and os.path.exists(book_level_trans_src):
        for file_name in ['a-suggested-resources.html']:
            src_file = os.path.join(book_level_trans_src, file_name)
            dst_file = os.path.join(book_level_trans_dst, file_name)
            if os.path.exists(src_file):
                with open(src_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                all_pages.append(f"/{book_level_dir}/{file_name}")
                pages_js = '<script src="../book-reader/book-pages.js"></script>\n'
                css_link = '<link rel="stylesheet" href="../book-reader/book-reader.css">\n'
                js_link = '<script src="../book-reader/book-reader.js"></script>\n'
                content = content.replace('../../../css/style.css', '../css/style.css').replace('../../css/style.css', '../css/style.css').replace('../css/style.css', '../css/style.css')
                content = content.replace('../assets/', 'assets/')
                # Remove old injected relative scripts if they exist
                content = content.replace('<script src="../../book-reader/book-pages.js"></script>\n', '')
                content = content.replace('<link rel="stylesheet" href="../../book-reader/book-reader.css">\n', '')
                content = content.replace('<script src="../../book-reader/book-pages.js"></script>\n', '')
                content = content.replace('<link href="../../book-reader/book-reader.css" rel="stylesheet"/>\n', '')
                content = content.replace('<script src="../book-reader/book-pages.js"></script>\n', '')
                content = content.replace('<link rel="stylesheet" href="../book-reader/book-reader.css">\n', '')
                content = content.replace('<script src="../book-reader/book-reader.js"></script>\n', '')
                content = content.replace('<link href="../book-reader/book-reader.css" rel="stylesheet"/>\n', '')
                if '</head>' in content and 'book-pages.js' not in content:
                    content = content.replace('</head>', f'{pages_js}{css_link}{js_link}</head>')
                with open(dst_file, 'w', encoding='utf-8') as f:
                    f.write(content)

    # 3. Copy global glossary
    glossary_src = os.path.join(book_dir, "glossary.csv")
    glossary_dst = os.path.join(output_dir, "glossary.csv")
    if os.path.exists(glossary_src):
        shutil.copy2(glossary_src, glossary_dst)
        print("Copied global glossary.csv")

    # Create book-pages.js
    pages_js_path = os.path.join(br_dst, "book-pages.js")
    with open(pages_js_path, "w", encoding="utf-8") as f:
        f.write(f"window.BOOK_PAGES = {all_pages};")
    print(f"Generated {len(all_pages)} pages into book-pages.js")

    # 4. Create an index.html at root that redirects to the first page
    index_html = os.path.join(output_dir, "index.html")
    first_page = all_pages[0] if all_pages else "/chapter-1/1-introduction.html"
    with open(index_html, "w", encoding="utf-8") as f:
        f.write(f'''<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url={first_page}" />
    <title>OpenStax Entrepreneurship Preview</title>
</head>
<body>
    <p>Redirecting to <a href="{first_page}">Start Reading</a></p>
</body>
</html>''')

    print(f"\\nBuild completed successfully! You can now host the '{output_dir}' directory.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        build_preview(sys.argv[1])
    else:
        build_preview("../entrepreneurship")

