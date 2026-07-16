"""
verify_resources.py — CLI command runner for `verify-resources`.

Usage:
    python -m src.cli.main verify-resources --book <slug>
    python -m src.cli.main verify-resources --book <slug> --chapter 1
    python -m src.cli.main verify-resources --book <slug> --stage archive
    python -m src.cli.main verify-resources --book <slug> --stage working
    python -m src.cli.main verify-resources --book <slug> --stage preview
    python -m src.cli.main verify-resources --book <slug> --stage web
    python -m src.cli.main verify-resources --book <slug> --all
"""

from src.qa.resource_verifier import verify_book_resources


def run(args):
    """
    Execute verify-resources subcommand.
    Scans all HTML outputs and validates CSS/image resource compliance.
    Exits non-zero if any errors are found.
    """
    book_slug = args.book
    chapter = getattr(args, "chapter", None)
    stage = getattr(args, "stage", None)
    run_all = getattr(args, "all", False)
    scope = getattr(args, "scope", "release")

    # --all overrides any --stage filter
    if run_all:
        stage = None

    print(f"\n{'='*60}")
    print(f"  VERIFY RESOURCES: BOOK '{book_slug}'")
    print(f"  Scope:        {scope}")
    if chapter:
        print(f"  Chapter:      {chapter}")
    if stage:
        print(f"  Stage filter: {stage}")
    print(f"{'='*60}\n")

    exit_code, report = verify_book_resources(book_slug, chapter=chapter, stage=stage, scope=scope)

    stages_str = ", ".join(report["stages_checked"]) if report["stages_checked"] else "none"
    print(f"Stages checked: {stages_str}")
    print(f"Errors found:   {report['total_errors']}")
    print(f"Warnings found: {report['total_warnings']}")

    # Print warnings
    if report["warnings"]:
        print("\n⚠  WARNINGS:")
        for file_path, warns in sorted(report["warnings"].items()):
            for w in warns:
                print(f"   WARN  {w}")

    # Print errors
    if report["errors"]:
        print("\n✗  ERRORS:")
        for file_path, errs in sorted(report["errors"].items()):
            for e in errs:
                print(f"   ERROR {e}")
        print(f"\n{'='*60}")
        print(f"  RESULT: FAILED — {report['total_errors']} error(s) found")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'='*60}")
        print(f"  RESULT: PASSED — all resource checks OK")
        print(f"{'='*60}\n")

    return exit_code
