import argparse
import sys
from src.cli.commands import status, validate, init_book, init_chapter, scrape, prep, translate, review, fix, archive, build, apply_css
from src.cli.commands import verify_resources, qa_math, repair_encoding

def main():
    """
    Unified CLI entrypoint mapping command arguments to command runners.
    """
    parser = argparse.ArgumentParser(
        description="Libero Stateless Translation Engine CLI",
        prog="python -m src.cli.main"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # status command
    status_parser = subparsers.add_parser("status", help="Get status of a book")
    status_parser.add_argument("--book", required=True, help="Book slug")

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate book-level structure")
    validate_parser.add_argument("--book", required=True, help="Book slug")

    # init-book command
    init_book_parser = subparsers.add_parser("init-book", help="Initialize a new book workspace")
    init_book_parser.add_argument("--book", required=True, help="Book slug")
    init_book_parser.add_argument("--force", action="store_true", help="Overwrite existing workspace files if set")

    # init-chapter command
    init_chapter_parser = subparsers.add_parser("init-chapter", help="Initialize a new chapter in a book")
    init_chapter_parser.add_argument("--book", required=True, help="Book slug")
    init_chapter_parser.add_argument("--chapter", required=True, help="Chapter identifier")
    init_chapter_parser.add_argument("--force", action="store_true", help="Overwrite existing chapter files if set")

    # scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape book chapters recursively from OpenStax source")
    scrape_parser.add_argument("--book", required=True, help="Book slug")
    scrape_parser.add_argument("--chapter", required=True, help="Chapter identifier")
    scrape_parser.add_argument("--start-url", help="Start URL to scrape from. If not specified, crawler will guess page 1")
    scrape_parser.add_argument("--force", action="store_true", help="Overwrite existing raw HTML files if set")

    # prep command
    prep_parser = subparsers.add_parser("prep", help="Prepare bilingual HTML templates")
    prep_parser.add_argument("--book", required=True, help="Book slug")
    prep_parser.add_argument("--chapter", required=True, help="Chapter identifier")
    prep_parser.add_argument("--force", action="store_true", help="Overwrite existing prepped files if set")

    # translate command
    translate_parser = subparsers.add_parser("translate", help="Translate prepared bilingual HTML files")
    translate_parser.add_argument("--book", required=True, help="Book slug")
    translate_parser.add_argument("--chapter", required=True, help="Chapter identifier")
    translate_parser.add_argument("--file", help="Specific file to translate instead of all")
    translate_parser.add_argument("--force", action="store_true", help="Overwrite existing translated files")
    translate_parser.add_argument("--resume", action="store_true", help="Resume translation, skipping already translated files")
    translate_parser.add_argument("--dry-run", action="store_true", help="Run without writing files or changing status")
    translate_parser.add_argument("--batch-size", type=int, default=50, help="API batch size")
    translate_parser.add_argument("--model", help="Override the translation LLM model")
    translate_parser.add_argument("--provider", default="agent", choices=["agent", "gemini-api", "manual"], help="Translation provider")
    translate_parser.add_argument("--restore-math", action="store_true", help="Only restore/heal math/formulas from source to translated files, without translating")

    # review command
    review_parser = subparsers.add_parser("review", help="Run quality review checks on translated files")
    review_parser.add_argument("--book", required=True, help="Book slug")
    review_parser.add_argument("--chapter", required=True, help="Chapter identifier")
    review_parser.add_argument("--check", default="integrity", choices=["integrity", "glossary"], help="Type of review check to run")
    review_parser.add_argument("--all", action="store_true", help="Run all reviews and update QA gate status")
    review_parser.add_argument("--gate", action="store_true", help="Run review gate checking and update metadata status")

    # qa-math command
    qa_math_parser = subparsers.add_parser("qa-math", help="Run math and encoding QA verification")
    qa_math_parser.add_argument("--book", required=True, help="Book slug")
    qa_math_parser.add_argument("--chapter", help="Chapter identifier")
    qa_math_parser.add_argument("--file", help="Specific file to check")

    # repair-encoding command
    repair_parser = subparsers.add_parser("repair-encoding", help="Repair known mojibake in existing files")
    repair_parser.add_argument("--book", required=True, help="Book slug")
    repair_parser.add_argument("--chapter", required=True, help="Chapter identifier")
    repair_parser.add_argument("--file", help="Specific file to repair")
    repair_parser.add_argument("--stage", help="Specific stage/folder to repair")
    repair_parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode without modifying files")

    # fix command
    fix_parser = subparsers.add_parser("fix", help="Apply reviewed corrections to translated HTML files")
    fix_parser.add_argument("--book", required=True, help="Book slug")
    fix_parser.add_argument("--chapter", required=True, help="Chapter identifier")
    fix_parser.add_argument("--review-file", help="Specific review file to process instead of all")
    fix_parser.add_argument("--dry-run", action="store_true", help="Preview fixes without modifying files")

    # archive command
    archive_parser = subparsers.add_parser("archive", help="Compile and export translated pages to archive")
    archive_parser.add_argument("--book", required=True, help="Book slug")
    archive_parser.add_argument("--chapter", required=True, help="Chapter identifier")
    archive_parser.add_argument("--force", action="store_true", help="Override QA review gate checks")

    build_parser = subparsers.add_parser("build", help="Build interactive HTML preview from archives")
    build_parser.add_argument("--book", required=True, help="Book slug")
    build_parser.add_argument("--mode", default="bilingual", choices=["bilingual", "vn-only"], help="Archiving mode to build from")
    build_parser.add_argument("--copy-to-web", action="store_true", help="Copy finalized build to web site directory")
    build_parser.add_argument("--verify", action="store_true", help="Run verify-resources after build")

    # apply-css command
    apply_css_parser = subparsers.add_parser("apply-css", help="Apply core CSS stylesheet template to a book")
    apply_css_parser.add_argument("--book", required=True, help="Book slug")
    apply_css_parser.add_argument("--chapter", help="Chapter identifier (optional, used with --include-working)")
    apply_css_parser.add_argument("--include-working", action="store_true", help="Apply style.css to chapter working folders")
    apply_css_parser.add_argument("--include-raw", action="store_true", help="Apply style.css to raw folder as well (used with --include-working)")
    apply_css_parser.add_argument("--force", action="store_true", help="Overwrite existing style.css if set")

    # verify-resources command
    verify_parser = subparsers.add_parser("verify-resources", help="Verify CSS and image resources across pipeline stages")
    verify_parser.add_argument("--book", required=True, help="Book slug")
    verify_parser.add_argument("--chapter", help="Restrict verification to a specific chapter")
    verify_parser.add_argument("--stage", choices=["raw", "working", "archive", "preview", "web"], help="Restrict verification to a specific stage")
    verify_parser.add_argument("--all", action="store_true", help="Run all stage checks (default if no --stage given)")

    args = parser.parse_args()

    if args.command == "status":
        sys.exit(status.run(args))
    elif args.command == "validate":
        sys.exit(validate.run(args))
    elif args.command == "init-book":
        sys.exit(init_book.run(args))
    elif args.command == "init-chapter":
        sys.exit(init_chapter.run(args))
    elif args.command == "scrape":
        sys.exit(scrape.run(args))
    elif args.command == "prep":
        sys.exit(prep.run(args))
    elif args.command == "translate":
        sys.exit(translate.run(args))
    elif args.command == "review":
        sys.exit(review.run(args))
    elif args.command == "qa-math":
        sys.exit(qa_math.run(args))
    elif args.command == "repair-encoding":
        sys.exit(repair_encoding.run(args))
    elif args.command == "fix":
        sys.exit(fix.run(args))
    elif args.command == "archive":
        sys.exit(archive.run(args))
    elif args.command == "build":
        sys.exit(build.run(args))
    elif args.command == "apply-css":
        sys.exit(apply_css.run(args))
    elif args.command == "verify-resources":
        sys.exit(verify_resources.run(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
