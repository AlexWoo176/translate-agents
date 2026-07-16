import os
import json
from src.core.paths import get_chapter_root, get_book_root, get_chapter_folder_name

def run(args):
    """
    Execute init-chapter command: initialize directory structure for a chapter
    and generate its metadata, plus updating parent status.json.
    """
    book_slug = args.book
    force = getattr(args, "force", False)
    
    # Try parsing chapter identifier as integer, fallback to string
    try:
        chapter_val = int(args.chapter)
    except ValueError:
        chapter_val = args.chapter

    chapter_root = get_chapter_root(book_slug, args.chapter)

    print(f"Initializing chapter workspace at: {chapter_root}")

    # 1. Define list of nested subfolders to create
    subfolders = [
        "01-raw",
        "02-clean",
        "03-analyzed",
        "04-prep",
        "05-translated",
        "06-reviews",
        "07-archive",
        "07-archive/bilingual",
        "07-archive/bilingual/html",
        "07-archive/bilingual/md",
        "07-archive/bilingual/pdf",
        "07-archive/vn-only",
        "07-archive/vn-only/html",
        "07-archive/vn-only/md",
        "07-archive/vn-only/pdf"
    ]

    # 2. Create subfolders
    for sub in subfolders:
        dir_path = chapter_root / sub
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            print(f"Error creating directory {sub}: {e}")
            return 1

    # 3. Create chapter.json metadata file
    chapter_json = chapter_root / "chapter.json"
    
    chapter_data = {
        "book": book_slug,
        "chapter": chapter_val,
        "title_en": "",
        "title_vi": "",
        "status": "initialized",
        "qa": {
            "integrity": "pending",
            "glossary": "pending",
            "html_structure": "pending",
            "untranslated": "pending",
            "review_gate": "pending"
        },
        "archive": {
            "bilingual": {
                "html": False,
                "md": False,
                "pdf": False
            },
            "vn-only": {
                "html": False,
                "md": False,
                "pdf": False
            }
        }
    }

    if chapter_json.is_file() and not force:
        print("  - Skipping chapter.json (already exists). Use --force to overwrite.")
    else:
        try:
            with open(chapter_json, "w", encoding="utf-8") as f:
                json.dump(chapter_data, f, indent=2)
            action_str = "Overwrote" if chapter_json.is_file() and force else "Created"
            print(f"  - {action_str} chapter.json")
        except Exception as e:
            print(f"Error writing chapter.json: {e}")
            return 1

    # 4. Update status.json of parent book
    chapter_key = get_chapter_folder_name(args.chapter)

    status_file = get_book_root(book_slug) / "status.json"
    if status_file.is_file():
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                status_data = json.load(f)
            if "chapters" not in status_data:
                status_data["chapters"] = {}
            status_data["chapters"][chapter_key] = {
                "status": "initialized"
            }
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, indent=2)
            print(f"  - Updated status.json to include {chapter_key}")
            from src.utils.status_helper import sync_tasks_markdown
            sync_tasks_markdown(book_slug)
        except Exception as e:
            print(f"Warning: Could not update status.json: {e}")

    print("Chapter initialization complete.")
    return 0
