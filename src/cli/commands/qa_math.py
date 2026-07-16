import os
import sys
from pathlib import Path
from src.core.paths import get_book_root, get_translated_dir, get_chapter_folder_name
from src.qa.math_encoding_qa import run_math_encoding_qa

def run(args):
    """
    Execute qa-math command: run math and encoding QA verification.
    """
    book_slug = args.book
    chapter = getattr(args, "chapter", None)
    file_name = getattr(args, "file", None)

    book_root = get_book_root(book_slug)
    if not book_root.is_dir():
        print(f"Error: Book directory '{book_root}' does not exist.")
        return 1

    # Find chapters to check
    if chapter:
        chapters = [get_chapter_folder_name(chapter)]
    else:
        chapters = []
        for d in os.listdir(book_root):
            if d.startswith("chapter-") and (book_root / d).is_dir():
                chapters.append(d)
        # Numeric sort
        chapters.sort(key=lambda x: int(x.split('-')[1]) if x.split('-')[1].isdigit() else 999)

    overall_pass = True
    total_files_checked = 0
    total_failures = 0

    print(f"\n============================================================")
    print(f"  RUNNING MATH/ENCODING QA: BOOK '{book_slug}'")
    print(f"============================================================\n")

    for chap in chapters:
        trans_dir = get_translated_dir(book_slug, chap)
        
        if not trans_dir.is_dir():
            print(f"Skipping chapter {chap} (translated folder not found)")
            continue

        if file_name:
            files_to_check = [file_name]
        else:
            files_to_check = sorted([f for f in os.listdir(trans_dir) if f.endswith(".html")])

        for fname in files_to_check:
            filepath = trans_dir / fname
            if not filepath.is_file():
                if file_name:
                    print(f"Error: File '{filepath}' not found.")
                    return 1
                continue

            total_files_checked += 1
            print(f"Checking {chap}/{fname}...")
            res = run_math_encoding_qa(filepath)
            
            if res["status"] == "PASS":
                print(f"  [PASS]")
            else:
                print(f"  [FAIL]")
                for issue in res["issues"]:
                    print(f"    * {issue}")
                overall_pass = False
                total_failures += 1

    print("\nSummary:")
    print(f"  - Total files checked: {total_files_checked}")
    print(f"  - Failed files: {total_failures}")

    if overall_pass:
        print("\nQA Outcome: PASS")
        return 0
    else:
        print("\nQA Outcome: FAIL")
        return 1
