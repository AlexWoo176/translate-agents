import json
from pathlib import Path
from src.core.paths import get_book_root, get_chapter_root

def run(args):
    """
    Execute status subcommand: resolve the target book path and read status.json.
    Print a highly readable progress dashboard of all chapters.
    """
    book_slug = args.book
    book_root = get_book_root(book_slug)

    status_file = book_root / "status.json"
    if not status_file.is_file():
        print(f"Error: status.json does not exist for book '{book_slug}'.")
        print(f"Initialize the book workspace first using: python -m src.cli.main init-book --book {book_slug}")
        return 1

    try:
        with open(status_file, "r", encoding="utf-8") as f:
            status_data = json.load(f)
    except Exception as e:
        print(f"Error reading status.json: {e}")
        return 1

    print("\n============================================================")
    print(f"  BOOK STATUS DASHBOARD: {book_slug.upper()}")
    print("============================================================\n")
    print(f"Book Workspace: {book_root}")
    print(f"Overall Status: {status_data.get('status', 'initialized').upper()}")
    print()

    chapters = status_data.get("chapters", {})
    if not chapters:
        print("No chapters registered in status.json yet.")
        print(f"Initialize a chapter using: python -m src.cli.main init-chapter --book {book_slug} --chapter <number>")
    else:
        print("Chapters Progress:")
        print("------------------------------------------------------------")
        for chap_key, chap_summary in sorted(chapters.items()):
            print(f"* {chap_key}:")
            print(f"  - Summary Status: {chap_summary.get('status', 'initialized').upper()}")
            print(f"  - Last Updated:  {chap_summary.get('last_updated', 'N/A')}")
            
            # Retrieve detailed chapter.json from chapter directory
            chap_num = chap_key.replace("chapter-", "")
            chap_root = get_chapter_root(book_slug, chap_num)
            chapter_json = chap_root / "chapter.json"
            
            if chapter_json.is_file():
                try:
                    with open(chapter_json, "r", encoding="utf-8") as cf:
                        chap_detail = json.load(cf)
                    
                    phases = chap_detail.get("phases", {})
                    if phases:
                        print("  - Phase Details:")
                        for phase, details in sorted(phases.items()):
                            status_val = details.get("status", "unknown").upper()
                            timestamp = details.get("timestamp", "N/A")
                            print(f"    * {phase:10} : {status_val} ({timestamp})")
                            if "error" in details:
                                print(f"      [ERROR]   : {details['error']}")
                            
                    qa = chap_detail.get("qa", {})
                    if qa:
                        print("  - QA Gates:")
                        print(f"    * integrity : {qa.get('integrity', 'pending').upper()}")
                        print(f"    * glossary  : {qa.get('glossary', 'pending').upper()}")
                        print(f"    * gate      : {qa.get('review_gate', 'pending').upper()}")
                        if qa.get("review_gate_forced"):
                            print("      [BYPASS]  : QA review checks overridden with --force")
                            
                    archive = chap_detail.get("archive", {})
                    if archive:
                        print("  - Archived formats:")
                        for mode in ["bilingual", "vn-only"]:
                            formats = archive.get(mode, {})
                            if formats:
                                html_status = "ok" if formats.get("html") else "no"
                                md_status = "ok" if formats.get("md") else "no"
                                pdf_status = "ok" if formats.get("pdf") else "no"
                                print(f"    * {mode:10} : html={html_status}, md={md_status}, pdf={pdf_status}")
                except Exception as e:
                    print(f"  - Could not load phase details: {e}")
            else:
                print("  - No chapter.json details found.")
            print()

    build_info = status_data.get("build")
    if build_info:
        print("Build Preview Status:")
        print("------------------------------------------------------------")
        print(f"- Status:      {build_info.get('status', 'unknown').upper()}")
        print(f"- Compiled At: {build_info.get('timestamp', 'N/A')}")
        if "error" in build_info:
            print(f"- [ERROR]:     {build_info['error']}")
        else:
            print(f"- Mode:        {build_info.get('mode', 'bilingual')}")
            print(f"- Pages:       {build_info.get('total_pages', 0)}")
            print(f"- Redirect:    {build_info.get('first_page', 'N/A')}")
        print()

    return 0
