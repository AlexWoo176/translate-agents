import sys
from src.pipeline.fix.apply_review_fixes import apply_review_fixes
from src.utils.status_helper import update_status

def run(args):
    """
    Execute fix subcommand: safely apply reviewed translation fixes to HTML files,
    writing backups, marking markdown tables, and saving a diff report.
    """
    book_slug = args.book
    chapter = args.chapter
    review_file = getattr(args, "review_file", None)
    dry_run = getattr(args, "dry_run", False)

    print(f"\n============================================================")
    print(f"  APPLY REVIEW FIXES: BOOK '{book_slug}' CHAPTER '{chapter}'")
    if dry_run:
        print("  (DRY-RUN MODE ACTIVE - NO FILES WILL BE WRITTEN)")
    print(f"============================================================\n")

    status_code, result = apply_review_fixes(book_slug, chapter, review_file_path=review_file, dry_run=dry_run)

    if status_code != 0:
        print(f"Error: {result}")
        update_status(book_slug, chapter, phase="fix", status_str="failed", error_msg=str(result))
        return status_code

    applied = result["applied"]
    skipped = result["skipped"]
    report_file = result["diff_report"]

    print("Fix Execution Summary:")
    print(f"  - Fixes applied: {len(applied)}")
    print(f"  - Fixes skipped/failed: {len(skipped)}")
    print(f"\nDiff report written to: {report_file}")

    if skipped:
        print("\nSome fixes were skipped (unmatched or ambiguous text structures). Check the diff report for details.")

    update_status(book_slug, chapter, phase="fix", status_str="completed",
                  extra_metadata={"fixes_applied": len(applied), "fixes_skipped": len(skipped), "dry_run": dry_run})
    return 0
