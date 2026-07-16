"""
resource_verifier.py — Book resource verification orchestrator.

Implements the logic for `verify-resources` CLI command. Scans all HTML files
in a book's pipeline stages and validates CSS/image resource compliance against
the resource contract defined in docs/resource-contract.md.

Usage (from CLI):
    python -m src.cli.main verify-resources --book <slug>
    python -m src.cli.main verify-resources --book <slug> --chapter 1
    python -m src.cli.main verify-resources --book <slug> --stage archive

Returns:
    (exit_code: int, report: dict)
    exit_code 0 if all checks pass, 1 if any errors found
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from src.core.paths import (
    get_book_root,
    get_web_output_root,
    get_phase_dir,
    get_archive_dir,
)
from src.utils.html_resources import (
    validate_stylesheet_links,
    validate_image_links,
    validate_no_forbidden_css,
    validate_no_duplicate_stylesheets,
    validate_image_src_pattern,
)

# Stages that can be individually targeted
VALID_STAGES = ("raw", "working", "archive", "preview", "web")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _html_files(directory: Path) -> list[Path]:
    """Return all .html files in a directory (non-recursive)."""
    if not directory.is_dir():
        return []
    return [directory / f for f in os.listdir(directory) if f.endswith(".html")]


def _accumulate(errors: dict, file_path: Path, new_errors: list[str]) -> None:
    """Accumulate validation errors into the shared errors dict."""
    if new_errors:
        key = str(file_path)
        errors.setdefault(key, []).extend(new_errors)


def _run_validators(html_file: Path, stage: str, assets_dir: Optional[Path],
                    errors: dict, warnings: dict, phase: Optional[str] = None) -> None:
    """
    Run all applicable validators for a single HTML file and accumulate results.
    """
    # CSS presence/correctness (skip or warn for raw, clean, prep)
    res = validate_stylesheet_links(html_file, stage)
    if stage == "raw" or phase in ("clean", "prep"):
        if not res["ok"]:
            key = str(html_file)
            warnings.setdefault(key, []).extend(res["errors"])
    else:
        _accumulate(errors, html_file, res["errors"])

    # Forbidden CSS check
    res = validate_no_forbidden_css(html_file, stage)
    _accumulate(errors, html_file, res["errors"])

    # Duplicate stylesheets
    res = validate_no_duplicate_stylesheets(html_file)
    _accumulate(errors, html_file, res["errors"])

    # Image src pattern
    res = validate_image_src_pattern(html_file, stage)
    _accumulate(errors, html_file, res["errors"])

    # Image file resolution (only when assets_dir is known)
    if assets_dir is not None and stage != "raw":
        res = validate_image_links(html_file, assets_dir)
        _accumulate(errors, html_file, res["errors"])


# ---------------------------------------------------------------------------
# Per-stage scanners
# ---------------------------------------------------------------------------

def _verify_raw(book_slug: str, chapter: str, errors: dict, warnings: dict) -> None:
    """Verify 01-raw — report-only, no requirements."""
    raw_dir = get_phase_dir(book_slug, chapter, "raw")
    for html_file in _html_files(raw_dir):
        _run_validators(html_file, "raw", None, errors, warnings)


def _verify_working(book_slug: str, chapter: str, errors: dict, warnings: dict, scope: str = "release") -> None:
    """Verify 02-clean, 04-prep, 05-translated working folders."""
    book_root = get_book_root(book_slug)
    chapter_str = f"chapter-{chapter}" if not str(chapter).startswith("chapter-") and str(chapter) != "_book-level" else str(chapter)
    assets_dir = book_root / chapter_str / "assets"

    if scope == "release":
        phases = ("translated",)
    else:
        phases = ("clean", "prep", "translated")

    for phase in phases:
        phase_dir = get_phase_dir(book_slug, chapter, phase)
        for html_file in _html_files(phase_dir):
            _run_validators(html_file, "working", assets_dir, errors, warnings, phase=phase)


def _verify_archive(book_slug: str, chapter: str, errors: dict, warnings: dict) -> None:
    """Verify 07-archive/bilingual/html and 07-archive/vn-only/html."""
    book_root = get_book_root(book_slug)
    chapter_str = f"chapter-{chapter}" if not str(chapter).startswith("chapter-") and str(chapter) != "_book-level" else str(chapter)
    assets_dir = book_root / chapter_str / "assets"

    for mode in ("bilingual", "vn-only"):
        archive_html_dir = get_archive_dir(book_slug, chapter, mode, "html")
        for html_file in _html_files(archive_html_dir):
            _run_validators(html_file, "archive", assets_dir, errors, warnings)


def _verify_preview(book_slug: str, chapter: Optional[str], errors: dict, warnings: dict) -> None:
    """Verify .html preview build output."""
    book_root = get_book_root(book_slug)
    preview_root = book_root / ".html"

    if not preview_root.is_dir():
        errors.setdefault("__preview__", []).append(
            f"Preview output directory not found: {preview_root}"
        )
        return

    # CSS and book-reader files must exist
    if not (preview_root / "css" / "style.css").is_file():
        errors.setdefault("__preview__", []).append(
            f"Missing css/style.css in preview: {preview_root / 'css' / 'style.css'}"
        )
    if not (preview_root / "book-reader" / "book-reader.css").is_file():
        errors.setdefault("__preview__", []).append(
            f"Missing book-reader/book-reader.css in preview: {preview_root / 'book-reader'}"
        )

    chapters_to_check = []
    if chapter:
        chap_str = f"chapter-{chapter}" if not str(chapter).startswith("chapter-") and str(chapter) != "_book-level" else str(chapter)
        chapters_to_check = [chap_str]
    else:
        chapters_to_check = [
            d for d in os.listdir(preview_root)
            if d.startswith("chapter-") and (preview_root / d).is_dir()
        ]

    for chap_str in chapters_to_check:
        chap_dir = preview_root / chap_str
        assets_dir = chap_dir / "assets"
        if not assets_dir.is_dir():
            warnings.setdefault("__preview__", []).append(
                f"No assets dir for chapter preview: {assets_dir}"
            )
        for html_file in _html_files(chap_dir):
            _run_validators(html_file, "preview", assets_dir, errors, warnings)


def _verify_web(book_slug: str, chapter: Optional[str], errors: dict, warnings: dict) -> None:
    """Verify web-site output."""
    web_root = get_web_output_root() / book_slug

    if not web_root.is_dir():
        errors.setdefault("__web__", []).append(
            f"Web-site output directory not found: {web_root}"
        )
        return

    # CSS and book-reader files must exist
    if not (web_root / "css" / "style.css").is_file():
        errors.setdefault("__web__", []).append(
            f"Missing css/style.css in web-site: {web_root / 'css' / 'style.css'}"
        )
    if not (web_root / "book-reader" / "book-reader.css").is_file():
        errors.setdefault("__web__", []).append(
            f"Missing book-reader/book-reader.css in web-site: {web_root / 'book-reader'}"
        )

    chapters_to_check = []
    if chapter:
        chap_str = f"chapter-{chapter}" if not str(chapter).startswith("chapter-") and str(chapter) != "_book-level" else str(chapter)
        chapters_to_check = [chap_str]
    else:
        chapters_to_check = [
            d for d in os.listdir(web_root)
            if d.startswith("chapter-") and (web_root / d).is_dir()
        ]

    for chap_str in chapters_to_check:
        chap_dir = web_root / chap_str
        assets_dir = chap_dir / "assets"
        if not assets_dir.is_dir():
            warnings.setdefault("__web__", []).append(
                f"No assets dir for chapter web output: {assets_dir}"
            )
        for html_file in _html_files(chap_dir):
            _run_validators(html_file, "web", assets_dir, errors, warnings)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_book_resources(
    book_slug: str,
    chapter: Optional[str] = None,
    stage: Optional[str] = None,
    scope: str = "release",
) -> tuple[int, dict]:
    """
    Verify all HTML resources for a book against the resource contract.

    Args:
        book_slug: Book identifier (e.g. 'introductory-statistics-2e')
        chapter: Optional chapter number or identifier. If given, restricts
                 verification to that chapter only.
        stage: Optional stage filter. One of: raw, working, archive, preview, web.
               If None, all stages are checked.
        scope: Verification scope. If 'release', scans only release stages (excluding
               raw, clean, prep). If 'all', scans intermediate stages too.

    Returns:
        (exit_code, report)
        exit_code: 0 if all checks pass, 1 if any errors found
        report: {
            "errors": {file_path: [error_str]},
            "warnings": {file_path: [warning_str]},
            "total_errors": int,
            "total_warnings": int,
            "stages_checked": [str],
        }
    """
    errors: dict[str, list[str]] = {}
    warnings: dict[str, list[str]] = {}
    stages_checked = []

    book_root = get_book_root(book_slug)

    # Determine which chapters to scan
    if chapter:
        chapters = [str(chapter)]
    else:
        chapters = []
        if book_root.is_dir():
            for d in os.listdir(book_root):
                if d.startswith("chapter-") and (book_root / d).is_dir():
                    num = d.split("-")[1]
                    chapters.append(num)
            chapters.sort(key=lambda x: int(x) if x.isdigit() else 999)

    # Determine which stages to run
    run_all = stage is None
    if scope == "release":
        run_raw = (stage == "raw")
        run_working = run_all or stage == "working"
        run_archive = run_all or stage == "archive"
        run_preview = run_all or stage == "preview"
        run_web = run_all or stage == "web"
    else:
        run_raw = run_all or stage == "raw"
        run_working = run_all or stage == "working"
        run_archive = run_all or stage == "archive"
        run_preview = run_all or stage == "preview"
        run_web = run_all or stage == "web"

    # Run chapter-level stage checks
    for chap in chapters:
        if run_raw:
            _verify_raw(book_slug, chap, errors, warnings)
        if run_working:
            _verify_working(book_slug, chap, errors, warnings, scope=scope)
        if run_archive:
            _verify_archive(book_slug, chap, errors, warnings)

    if run_raw:
        stages_checked.append("raw")
    if run_working:
        stages_checked.append("working")
    if run_archive:
        stages_checked.append("archive")

    # Preview and web are book-level (not per-chapter split by scanner)
    if run_preview:
        _verify_preview(book_slug, chapter, errors, warnings)
        stages_checked.append("preview")
    if run_web:
        _verify_web(book_slug, chapter, errors, warnings)
        stages_checked.append("web")

    total_errors = sum(len(v) for v in errors.values())
    total_warnings = sum(len(v) for v in warnings.values())

    report = {
        "errors": errors,
        "warnings": warnings,
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "stages_checked": stages_checked,
        "book_slug": book_slug,
        "chapter": chapter,
        "stage_filter": stage,
        "scope": scope,
    }

    exit_code = 0 if total_errors == 0 else 1
    return exit_code, report
