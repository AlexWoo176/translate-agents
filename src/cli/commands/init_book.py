import os
import json
from src.core.paths import get_book_root

def run(args):
    """
    Execute init-book command: initialize directory layout and metadata files
    for a book workspace.
    """
    book_slug = args.book
    force = getattr(args, "force", False)
    
    book_path = get_book_root(book_slug)
    print(f"Initializing book workspace at: {book_path}")
    
    # 1. Ensure folders exist
    try:
        os.makedirs(book_path, exist_ok=True)
        (book_path / "css").mkdir(exist_ok=True)
        (book_path / "assets").mkdir(exist_ok=True)
        (book_path / "_book-level").mkdir(exist_ok=True)
    except Exception as e:
        print(f"Error creating directories: {e}")
        return 1

    # 1.5. Copy default style.css template
    try:
        from src.core.config import WORKSPACE_ROOT
        import shutil
        src_css = WORKSPACE_ROOT / "src" / "templates" / "book-css" / "style.css"
        dst_css = book_path / "css" / "style.css"
        if src_css.is_file():
            if dst_css.is_file() and not force:
                print("  - Skipping css/style.css (already exists). Use --force to overwrite.")
            else:
                shutil.copy2(src_css, dst_css)
                action_str = "Overwrote" if dst_css.is_file() and force else "Created"
                print(f"  - {action_str} css/style.css")
        else:
            print("Warning: Default style.css template not found at src/templates/book-css/style.css")
    except Exception as e:
        print(f"Error copying style.css: {e}")
        return 1

    # 2. Define files and their contents
    files_to_create = {
        "book.json": json.dumps({
            "slug": book_slug,
            "title_en": "",
            "title_vi": "",
            "source": "",
            "language_source": "en",
            "language_target": "vi",
            "status": "initialized",
            "chapters": []
        }, indent=2),
        
        "glossary.csv": "term,translation,context,status,notes\n",
        
        "status.json": json.dumps({
            "book": book_slug,
            "status": "initialized",
            "chapters": {}
        }, indent=2),
        
        "tasks.md": f"# Project Tasks: {book_slug}\n\n- [ ] Initialize workspace\n"
    }

    # 3. Create files with overwrite protection
    for filename, content in files_to_create.items():
        file_path = book_path / filename
        if file_path.is_file() and not force:
            print(f"  - Skipping {filename} (already exists). Use --force to overwrite.")
        else:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                action_str = "Overwrote" if file_path.is_file() and force else "Created"
                print(f"  - {action_str} {filename}")
            except Exception as e:
                print(f"Error writing file {filename}: {e}")
                return 1

    print("Book initialization complete.")
    return 0
