import sys
from src.pipeline.translate.translate_runner import translate_chapter
from src.utils.status_helper import update_status

def run(args):
    """
    Execute translate subcommand: translate prepared bilingual HTML files.
    """
    book_slug = args.book
    chapter = args.chapter
    file_filter = getattr(args, "file", None)
    force = getattr(args, "force", False)
    resume = getattr(args, "resume", False)
    dry_run = getattr(args, "dry_run", False)
    batch_size = getattr(args, "batch_size", 50)
    model = getattr(args, "model", None)
    provider = getattr(args, "provider", "agent")
    restore_math_only = getattr(args, "restore_math", False)

    if restore_math_only:
        if dry_run:
            print(f"Dry run: Simulating math/formula restoration for book '{book_slug}' chapter '{chapter}'...")
            return 0
        print(f"Restoring and healing math/formulas for book '{book_slug}' chapter '{chapter}'...")
        from src.core.paths import get_prep_dir, get_translated_dir
        import os
        prep_dir = get_prep_dir(book_slug, chapter)
        translated_dir = get_translated_dir(book_slug, chapter)
        if not prep_dir.is_dir():
            print(f"Error: Prep directory not found at {prep_dir}")
            return 1
        if not translated_dir.is_dir():
            print(f"Error: Translated directory not found at {translated_dir}")
            return 1
        html_files = sorted([f for f in os.listdir(prep_dir) if f.endswith('.html')])
        if file_filter:
            html_files = [f for f in html_files if f == file_filter]
            
        from src.pipeline.translate.translate_runner import validate_agent_translation
        is_valid, err_msg, val_results = validate_agent_translation(prep_dir, translated_dir, html_files)
        
        processed = val_results.get("processed", [])
        failed = val_results.get("failed", [])
        print("\nMath Restoration Summary:")
        print(f"  - Healed/Validated: {len(processed)} file(s)")
        for p in processed:
            print(f"    * {p['file']}")
        print(f"  - Failed/In-Progress: {len(failed)} file(s)")
        for f in failed:
            print(f"    * {f['file']}: {f['error']}")
            
        if failed:
            return 1
        return 0

    # Guard: Ensure term extraction has been performed
    from src.core.paths import get_book_root, get_chapter_folder_name
    book_path = get_book_root(book_slug)
    chap_folder = get_chapter_folder_name(chapter)
    new_glossary_path = book_path / chap_folder / "03-analyzed" / f"{chap_folder}-new-glossary.csv"
    if not new_glossary_path.is_file() and provider == "gemini-api" and not dry_run:
        print(f"WARNING: Glossary proposal file not found at: {new_glossary_path}")
        print(f"  It is highly recommended to run term extraction and review them before translating.")
        print(f"  To extract terms, run:")
        print(f"    node agents/agent-analyze/scripts/term-extract.js {book_slug} {chapter}")
        if not force:
            print("  Translation aborted. Use --force to override this check.")
            return 1

    if dry_run:
        print(f"Dry run enabled. Simulating translation for book '{book_slug}' chapter '{chapter}' (provider: '{provider}')...")
    else:
        print(f"Executing translation pipeline for book '{book_slug}' chapter '{chapter}' (provider: '{provider}')...")
        if provider == "gemini-api":
            update_status(book_slug, chapter, phase="translate", status_str="translating")

    try:
        results = translate_chapter(
            book_slug, chapter,
            file_filter=file_filter,
            force=force,
            resume=resume,
            dry_run=dry_run,
            batch_size=batch_size,
            model=model,
            provider=provider
        )
    except FileNotFoundError as e:
        print(f"Error: {e}")
        if not dry_run:
            update_status(book_slug, chapter, phase="translate", status_str="failed", error_msg=str(e))
        return 1
    except Exception as e:
        print(f"Unexpected error during translation: {e}")
        if not dry_run:
            update_status(book_slug, chapter, phase="translate", status_str="failed", error_msg=str(e))
        return 1

    processed = results.get("processed", [])
    skipped = results.get("skipped", [])
    failed = results.get("failed", [])

    print("\nTranslation Summary:")
    print(f"  - Processed/Validated: {len(processed)} file(s)")
    for p in processed:
        print(f"    * {p['file']} ({p['blocks']} blocks, {p['fallbacks']} fallback trigger(s))")
        
    print(f"  - Skipped: {len(skipped)} file(s)")
    for s in skipped:
        print(f"    * {s['file']}: {s.get('reason', 'Skipped')}")
        
    print(f"  - Failed/In-Progress: {len(failed)} file(s)")
    for f in failed:
        print(f"    * {f['file']}: {f['error']}")

    if provider == "gemini-api":
        if failed:
            error_msg = f"Failed to translate {len(failed)} file(s)"
            if not dry_run:
                update_status(book_slug, chapter, phase="translate", status_str="failed", error_msg=error_msg,
                              extra_metadata={"files_processed": len(processed), "files_skipped": len(skipped), "files_failed": len(failed), "provider": provider})
            return 1
        if not dry_run:
            update_status(book_slug, chapter, phase="translate", status_str="completed",
                          extra_metadata={"files_processed": len(processed), "files_skipped": len(skipped), "provider": provider})
        return 0
        
    elif provider == "manual":
        if failed:
            print(f"Warning: Manual preparation failed to copy {len(failed)} file(s).")
            if not dry_run:
                update_status(book_slug, chapter, phase="translate", status_str="failed", error_msg="Manual copying failed",
                              extra_metadata={"provider": provider})
            return 1
        if not dry_run:
            update_status(book_slug, chapter, phase="translate", status_str="ready",
                          extra_metadata={"files_processed": len(processed), "files_skipped": len(skipped), "provider": provider})
        print("\nManual translation files prepared. Please translate the .vn.visible blocks in the 05-translated/ folder.")
        return 0
        
    elif provider == "agent":
        structural_failures = [f for f in failed if "untranslated" not in str(f.get("error")).lower()]
        
        if failed:
            if not dry_run:
                if structural_failures:
                    update_status(book_slug, chapter, phase="translate", status_str="failed", error_msg="Structural validation failures",
                                  extra_metadata={"provider": provider})
                else:
                    update_status(book_slug, chapter, phase="translate", status_str="translating",
                                  extra_metadata={"provider": provider, "files_processed": len(processed), "files_untranslated": len(failed)})
            if structural_failures:
                print(f"\nError: Validation found structural integrity issues in {len(structural_failures)} file(s).")
                return 1
            else:
                print("\nTranslation tasks prepared. Antigravity agent, please translate the .vn.visible blocks in the 05-translated/ folder.")
                return 0
                
        # All validation passed!
        if not dry_run:
            update_status(book_slug, chapter, phase="translate", status_str="completed",
                          extra_metadata={"files_processed": len(processed), "provider": provider})
        print("\nValidation passed! All files translated successfully.")
        return 0
    else:
        print(f"Error: Unknown provider '{provider}'")
        return 1
