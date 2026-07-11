import os
import sys
import shutil
import glob
from bs4 import BeautifulSoup

import argparse

def find_project_root():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.isdir(os.path.join(d, "data")):
            return d
        d = os.path.dirname(d)
    return None

def archive_chapter(chapter_num, book="entrepreneurship"):
    project_root = find_project_root()
    if not project_root:
        print("Cannot find project root with 'data' directory.")
        return
        
    book_dir = os.path.join(project_root, "data", book)
    chap_dir = os.path.join(book_dir, f"chapter-{chapter_num}")
    trans_dir = os.path.join(chap_dir, "05-translated")
    
    archive_dir = os.path.join(chap_dir, "07-archive")
    bilingual_dir = os.path.join(archive_dir, "bilingual")
    vn_only_dir = os.path.join(archive_dir, "vn-only")
    
    os.makedirs(bilingual_dir, exist_ok=True)
    os.makedirs(vn_only_dir, exist_ok=True)
    
    html_files = glob.glob(os.path.join(trans_dir, "*.html"))
    if not html_files:
        print(f"No translated files found in {trans_dir}")
        return
        
    for file_path in html_files:
        filename = os.path.basename(file_path)
        
        # 1. Copy to bilingual
        shutil.copy2(file_path, os.path.join(bilingual_dir, filename))
        
        # 2. Process vn-only
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove eng hidden elements
        for eng_elem in soup.find_all(class_='eng hidden'):
            eng_elem.decompose()
            
        # Clean up vn visible class
        for vn_elem in soup.find_all(class_='vn visible'):
            # remove the classes but keep others if they exist
            classes = vn_elem.get('class', [])
            classes = [c for c in classes if c not in ['vn', 'visible']]
            if classes:
                vn_elem['class'] = classes
            else:
                del vn_elem['class']
                
        # Also remove the style block injected for debug
        for style in soup.find_all('style'):
            if '.eng.hidden' in style.text or '.vn.visible' in style.text:
                style.decompose()
                
        # Save vn-only
        with open(os.path.join(vn_only_dir, filename), 'w', encoding='utf-8') as f:
            f.write(str(soup))
            
    print(f"Archived chapter {chapter_num} successfully to 07-archive/bilingual and 07-archive/vn-only.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Archive a translated chapter")
    parser.add_argument("chapter", help="Chapter number or name (e.g., preface)")
    parser.add_argument("--book", default="entrepreneurship", help="Book name")
    args = parser.parse_args()
    
    archive_chapter(args.chapter, args.book)
