import os
from pathlib import Path
from src.core.config import get_config, WORKSPACE_ROOT

# Mapping of phase names to sub-directory folders
PHASE_MAPPING = {
    "raw": "01-raw",
    "clean": "02-clean",
    "analyzed": "03-analyzed",
    "prep": "04-prep",
    "translated": "05-translated",
    "reviews": "06-reviews",
    "archive": "07-archive"
}

def resolve_path(configured_path: str) -> Path:
    """
    Resolve absolute path, or relative path based on WORKSPACE_ROOT.
    """
    p = Path(configured_path)
    if p.is_absolute():
        return p.resolve()
    return (WORKSPACE_ROOT / p).resolve()

def get_books_root() -> Path:
    """
    Get resolved BOOKS_ROOT directory.
    """
    books_root_val = get_config("BOOKS_ROOT", "../books")
    return resolve_path(books_root_val)

def get_web_output_root() -> Path:
    """
    Get resolved WEB_OUTPUT_ROOT directory.
    """
    web_root_val = get_config("WEB_OUTPUT_ROOT", "../web-site")
    return resolve_path(web_root_val)

def get_book_root(book_slug: str) -> Path:
    """
    Get root path of a book.
    """
    return get_books_root() / book_slug

def get_chapter_root(book_slug: str, chapter) -> Path:
    """
    Get root path of a specific chapter under a book.
    """
    chapter_str = str(chapter)
    if chapter_str.startswith("chapter-"):
        folder_name = chapter_str
    elif chapter_str == "_book-level":
        folder_name = chapter_str
    else:
        folder_name = f"chapter-{chapter_str}"
    return get_book_root(book_slug) / folder_name

def get_phase_dir(book_slug: str, chapter, phase: str) -> Path:
    """
    Get root path of a specific phase in a chapter.
    """
    phase_lower = str(phase).lower()
    folder_name = PHASE_MAPPING.get(phase_lower, str(phase))
    return get_chapter_root(book_slug, chapter) / folder_name

def get_raw_dir(book_slug: str = None, chapter = None) -> Path:
    """
    Get raw directory path, or folder name fallback.
    """
    if book_slug is None or chapter is None:
        return Path("01-raw")
    return get_phase_dir(book_slug, chapter, "raw")

def get_clean_dir(book_slug: str = None, chapter = None) -> Path:
    """
    Get clean directory path, or folder name fallback.
    """
    if book_slug is None or chapter is None:
        return Path("02-clean")
    return get_phase_dir(book_slug, chapter, "clean")

def get_analyzed_dir(book_slug: str = None, chapter = None) -> Path:
    """
    Get analyzed directory path, or folder name fallback.
    """
    if book_slug is None or chapter is None:
        return Path("03-analyzed")
    return get_phase_dir(book_slug, chapter, "analyzed")

def get_prep_dir(book_slug: str = None, chapter = None) -> Path:
    """
    Get prep directory path, or folder name fallback.
    """
    if book_slug is None or chapter is None:
        return Path("04-prep")
    return get_phase_dir(book_slug, chapter, "prep")

def get_translated_dir(book_slug: str = None, chapter = None) -> Path:
    """
    Get translated directory path, or folder name fallback.
    """
    if book_slug is None or chapter is None:
        return Path("05-translated")
    return get_phase_dir(book_slug, chapter, "translated")

def get_reviews_dir(book_slug: str = None, chapter = None) -> Path:
    """
    Get reviews directory path, or folder name fallback.
    """
    if book_slug is None or chapter is None:
        return Path("06-reviews")
    return get_phase_dir(book_slug, chapter, "reviews")

def get_archive_root(book_slug: str = None, chapter = None) -> Path:
    """
    Get archive root directory path, or folder name fallback.
    """
    if book_slug is None or chapter is None:
        return Path("07-archive")
    return get_phase_dir(book_slug, chapter, "archive")

def get_archive_dir(book_slug: str, chapter, mode: str, fmt: str = None) -> Path:
    """
    Get finalized archive path for a specific mode and format.
    """
    path = get_archive_root(book_slug, chapter) / mode
    if fmt:
        path = path / fmt
    return path

def get_book_html_dir(book_slug: str) -> Path:
    """
    Get final static HTML output directory for the web-site.
    """
    return get_web_output_root() / book_slug
