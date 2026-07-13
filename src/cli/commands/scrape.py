import sys
from src.pipeline.scrape.scrape_runner import scrape_chapter
from src.utils.status_helper import update_status

def run(args):
    """
    Execute scrape subcommand: download raw OpenStax HTML pages recursively for a chapter.
    """
    book_slug = args.book
    chapter = args.chapter
    start_url = getattr(args, "start_url", None)
    force = getattr(args, "force", False)

    print(f"Scraping book '{book_slug}' chapter '{chapter}'...")
    
    try:
        results = scrape_chapter(book_slug, chapter, start_url=start_url, force=force)
    except Exception as e:
        print(f"Unexpected error during scrape: {e}")
        update_status(book_slug, chapter, phase="scrape", status_str="failed", error_msg=str(e))
        return 1

    processed = results.get("processed", [])
    skipped = results.get("skipped", [])
    failed = results.get("failed", [])

    print("\nScraping Summary:")
    print(f"  - Downloaded: {len(processed)} page(s)")
    for f in processed:
        print(f"    * {f}")
        
    print(f"  - Skipped (Cached): {len(skipped)} page(s)")
    for f in skipped:
        print(f"    * {f}")
        
    print(f"  - Failed: {len(failed)} page(s)")
    for f_err in failed:
        print(f"    * {f_err['url']}: {f_err['error']}")

    if failed:
        error_msg = f"Failed to scrape {len(failed)} page(s)"
        update_status(book_slug, chapter, phase="scrape", status_str="failed", error_msg=error_msg,
                      extra_metadata={"pages_downloaded": len(processed), "pages_skipped": len(skipped), "pages_failed": len(failed)})
        return 1

    update_status(book_slug, chapter, phase="scrape", status_str="completed",
                  extra_metadata={"pages_downloaded": len(processed), "pages_skipped": len(skipped)})
    return 0
