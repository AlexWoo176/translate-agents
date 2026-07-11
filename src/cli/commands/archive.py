import sys
from src.pipeline.archive.archive_chapter import archive_chapter
from src.utils.status_helper import update_status

def run(args):
    """
    Execute archive subcommand: compile translated pages into bilingual and vn-only folders,
    running HTML, Markdown, and PDF conversions. Enforces QA gate checks.
    """
    book_slug = args.book
    chapter = args.chapter
    force = getattr(args, "force", False)

    print(f"\n============================================================")
    print(f"  ARCHIVING CHAPTER: BOOK '{book_slug}' CHAPTER '{chapter}'")
    if force:
        print("  (FORCE OVERRIDE QA GATE STATE ENABLED)")
    print(f"============================================================\n")

    status_code, result = archive_chapter(book_slug, chapter, force=force)

    if status_code != 0:
        print(f"Error: {result}")
        update_status(book_slug, chapter, phase="archive", status_str="failed", error_msg=str(result))
        return status_code

    print("Archive Execution Summary:")
    print("  Bilingual outputs:")
    print(f"    - HTML: {'PASSED' if result['bilingual']['html'] else 'FAILED'}")
    print(f"    - Markdown: {'PASSED' if result['bilingual']['md'] else 'FAILED'}")
    print(f"    - PDF: {'PASSED' if result['bilingual']['pdf'] else 'SKIPPED/FAILED (Missing system engine)'}")
    
    print("  Vietnamese-only outputs:")
    print(f"    - HTML: {'PASSED' if result['vn-only']['html'] else 'FAILED'}")
    print(f"    - Markdown: {'PASSED' if result['vn-only']['md'] else 'FAILED'}")
    print(f"    - PDF: {'PASSED' if result['vn-only']['pdf'] else 'SKIPPED/FAILED (Missing system engine)'}")

    if result.get("review_gate_forced"):
        print("\nNote: QA review gate check was overridden using --force.")

    update_status(book_slug, chapter, phase="archive", status_str="completed",
                  extra_metadata={"formats": result})
    return 0
