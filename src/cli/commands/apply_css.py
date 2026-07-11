import os
import shutil
from pathlib import Path
from bs4 import BeautifulSoup
from src.core.paths import get_book_root, get_chapter_root, get_phase_dir
from src.core.config import WORKSPACE_ROOT
from src.exporters.html_exporter import ensure_stylesheet_link

def run(args):
    """
    Execute apply-css command: copy core CSS template into book and/or inject it into working folders.
    """
    book_slug = args.book
    force = getattr(args, "force", False)
    include_working = getattr(args, "include_working", False)
    include_raw = getattr(args, "include_raw", False)
    chapter = getattr(args, "chapter", None)
    
    book_path = get_book_root(book_slug)
    if not book_path.is_dir():
        print(f"Error: Book workspace directory '{book_path}' does not exist. Run init-book first.")
        return 1
        
    css_dir = book_path / "css"
    try:
        css_dir.mkdir(exist_ok=True)
    except Exception as e:
        print(f"Error creating css directory: {e}")
        return 1
        
    src_css = WORKSPACE_ROOT / "src" / "templates" / "book-css" / "style.css"
    dst_css = css_dir / "style.css"
    
    if not src_css.is_file():
        print("Error: Default style.css template not found at src/templates/book-css/style.css")
        return 1
        
    book_css_status = "skipped"
    if dst_css.is_file() and not force:
        print(f"Skipping css/style.css for book '{book_slug}' (already exists). Use --force to overwrite.")
    else:
        try:
            shutil.copy2(src_css, dst_css)
            book_css_status = "overwrote" if dst_css.is_file() and force else "copied"
            print(f"Successfully {book_css_status} style.css template to {dst_css}")
        except Exception as e:
            print(f"Error copying style.css to book workspace: {e}")
            return 1

    # Chapter working folders CSS injection
    files_updated = 0
    files_skipped = 0
    folders_processed = []
    
    if include_working:
        if not chapter:
            print("Error: --chapter must be specified when using --include-working.")
            return 1
            
        chapter_root = get_chapter_root(book_slug, chapter)
        if not chapter_root.is_dir():
            print(f"Error: Chapter directory '{chapter_root}' does not exist.")
            return 1
            
        # Target working folders
        phases = ["clean", "prep", "translated"]
        if include_raw:
            phases.insert(0, "raw")
            
        for phase in phases:
            phase_dir = get_phase_dir(book_slug, chapter, phase)
            if not phase_dir.is_dir():
                continue
                
            folders_processed.append(phase_dir.name)
            html_files = [f for f in os.listdir(phase_dir) if f.endswith(".html")]
            
            for fname in html_files:
                file_path = phase_dir / fname
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    soup = BeautifulSoup(content, "html.parser")
                    
                    # Check if it already contains the link
                    style_link = None
                    for link in soup.find_all("link", rel="stylesheet"):
                        h = link.get("href", "")
                        if "style.css" in h:
                            style_link = link
                            break
                            
                    # If already correct link and not force, skip
                    if style_link and style_link.get("href", "") == "../../css/style.css" and not force:
                        files_skipped += 1
                        continue
                        
                    # Apply stylesheet normalization/injection
                    ensure_stylesheet_link(soup, "../../css/style.css")
                    from src.utils.html_encoding import ensure_meta_charset_utf8
                    ensure_meta_charset_utf8(soup)
                    
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(str(soup))
                        
                    files_updated += 1
                except Exception as e:
                    print(f"Warning: Failed to process {file_path}: {e}")
                    
        # Print summarization output
        print("\n============================================================")
        print("  CSS INJECTION SUMMARY:")
        print("============================================================")
        print(f"  Book: {book_slug}")
        print(f"  Chapter: {chapter}")
        print(f"  Book style.css state: {book_css_status}")
        print(f"  Working folders processed: {', '.join(folders_processed) if folders_processed else 'None'}")
        print(f"  Raw folder included: {'Yes' if include_raw else 'No'}")
        print(f"  HTML files updated: {files_updated}")
        print(f"  HTML files skipped: {files_skipped}")
        print("============================================================\n")

    return 0
