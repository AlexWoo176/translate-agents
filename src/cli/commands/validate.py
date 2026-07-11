import os
from src.core.paths import get_book_root

def run(args):
    """
    Execute validate subcommand: verify structure of book-level files and folders.
    """
    book_slug = args.book
    book_path = get_book_root(book_slug)
    print(f"Validating book workspace at: {book_path}")

    if not book_path.is_dir():
        print(f"Error: Book directory {book_path} does not exist.")
        return 1

    expected_files = {
        "book.json": "file",
        "glossary.csv": "file",
        "tasks.md": "file",
        "status.json": "file",
        "css": "dir",
        "assets": "dir",
        "_book-level": "dir"
    }

    all_valid = True
    for item, item_type in expected_files.items():
        path = book_path / item
        if item_type == "file":
            exists = path.is_file()
        else:
            exists = path.is_dir()

        status_str = "OK" if exists else "MISSING"
        print(f"  - {item} ({item_type}): {status_str}")
        if not exists:
            all_valid = False

    if all_valid:
        print("Validation outcome: PASS")
        return 0
    else:
        print("Validation outcome: FAIL (some elements are missing)")
        return 1
