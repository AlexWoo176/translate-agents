import sys
from src.pipeline.prep.prep_bilingual_html import prep_chapter
from src.utils.status_helper import update_status

def run(args):
    """
    Execute prep subcommand: transform clean HTML files into bilingual prep HTML structures.
    """
    book_slug = args.book
    chapter = args.chapter
    force = getattr(args, "force", False)

    print(f"Preparing bilingual HTML templates for book '{book_slug}' chapter '{chapter}'...")
    
    try:
        results = prep_chapter(book_slug, chapter, force=force)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        update_status(book_slug, chapter, phase="prep", status_str="failed", error_msg=str(e))
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        update_status(book_slug, chapter, phase="prep", status_str="failed", error_msg=str(e))
        return 1

    processed = results.get("processed", [])
    skipped = results.get("skipped", [])
    failed = results.get("failed", [])

    print("\nPreparation Summary:")
    print(f"  - Processed: {len(processed)} file(s)")
    for f in processed:
        print(f"    * {f}")
        
    print(f"  - Skipped: {len(skipped)} file(s)")
    for f in skipped:
        print(f"    * {f} (already exists, use --force to overwrite)")
        
    print(f"  - Failed: {len(failed)} file(s)")
    for f_err in failed:
        print(f"    * {f_err['file']}: {f_err['error']}")

    if failed:
        error_msg = f"Failed to prepare {len(failed)} file(s)"
        update_status(book_slug, chapter, phase="prep", status_str="failed", error_msg=error_msg,
                      extra_metadata={"files_processed": len(processed), "files_skipped": len(skipped), "files_failed": len(failed)})
        return 1

    update_status(book_slug, chapter, phase="prep", status_str="completed",
                  extra_metadata={"files_processed": len(processed), "files_skipped": len(skipped)})
    return 0
