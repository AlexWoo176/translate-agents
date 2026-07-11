import os
import unittest
from pathlib import Path

# Set dummy env vars for setup before importing core components
os.environ["BOOKS_ROOT"] = "../books"
os.environ["WEB_OUTPUT_ROOT"] = "../web-site"

from src.core.config import get_config, WORKSPACE_ROOT
from src.core.paths import (
    get_books_root,
    get_web_output_root,
    get_book_root,
    get_chapter_root,
    get_phase_dir,
    get_raw_dir,
    get_clean_dir,
    get_analyzed_dir,
    get_prep_dir,
    get_translated_dir,
    get_reviews_dir,
    get_archive_root,
    get_archive_dir,
    get_book_html_dir,
)

class TestPaths(unittest.TestCase):
    def setUp(self):
        # Cache current environment
        self.orig_books_root = os.environ.get("BOOKS_ROOT")
        self.orig_web_root = os.environ.get("WEB_OUTPUT_ROOT")

    def tearDown(self):
        # Restore environment settings
        if self.orig_books_root is not None:
            os.environ["BOOKS_ROOT"] = self.orig_books_root
        elif "BOOKS_ROOT" in os.environ:
            del os.environ["BOOKS_ROOT"]

        if self.orig_web_root is not None:
            os.environ["WEB_OUTPUT_ROOT"] = self.orig_web_root
        elif "WEB_OUTPUT_ROOT" in os.environ:
            del os.environ["WEB_OUTPUT_ROOT"]

    def test_default_paths(self):
        # Clear env variables to test configuration fallbacks
        if "BOOKS_ROOT" in os.environ:
            del os.environ["BOOKS_ROOT"]
        if "WEB_OUTPUT_ROOT" in os.environ:
            del os.environ["WEB_OUTPUT_ROOT"]

        books_root = get_books_root()
        self.assertEqual(books_root, (WORKSPACE_ROOT / "../books").resolve())

        web_root = get_web_output_root()
        self.assertEqual(web_root, (WORKSPACE_ROOT / "../web-site").resolve())

        # Test book root resolving
        book_slug = "math"
        self.assertEqual(get_book_root(book_slug), books_root / book_slug)

        # Test chapter formatting
        self.assertEqual(get_chapter_root(book_slug, 3), books_root / book_slug / "chapter-3")
        self.assertEqual(get_chapter_root(book_slug, "chapter-4"), books_root / book_slug / "chapter-4")
        self.assertEqual(get_chapter_root(book_slug, "preface"), books_root / book_slug / "chapter-preface")

    def test_phase_dirs(self):
        book = "entrepreneurship"
        ch = 1

        chapter_path = get_chapter_root(book, ch)
        self.assertEqual(get_raw_dir(book, ch), chapter_path / "01-raw")
        self.assertEqual(get_clean_dir(book, ch), chapter_path / "02-clean")
        self.assertEqual(get_analyzed_dir(book, ch), chapter_path / "03-analyzed")
        self.assertEqual(get_prep_dir(book, ch), chapter_path / "04-prep")
        self.assertEqual(get_translated_dir(book, ch), chapter_path / "05-translated")
        self.assertEqual(get_reviews_dir(book, ch), chapter_path / "06-reviews")
        self.assertEqual(get_archive_root(book, ch), chapter_path / "07-archive")

        # Single arg (no params) returns standard folder name Path
        self.assertEqual(get_raw_dir(), Path("01-raw"))
        self.assertEqual(get_clean_dir(), Path("02-clean"))
        self.assertEqual(get_analyzed_dir(), Path("03-analyzed"))
        self.assertEqual(get_prep_dir(), Path("04-prep"))
        self.assertEqual(get_translated_dir(), Path("05-translated"))
        self.assertEqual(get_reviews_dir(), Path("06-reviews"))
        self.assertEqual(get_archive_root(), Path("07-archive"))

    def test_archive_dir(self):
        book = "physics"
        ch = "chapter-2"
        self.assertEqual(get_archive_dir(book, ch, "bilingual"), get_chapter_root(book, ch) / "07-archive" / "bilingual")
        self.assertEqual(get_archive_dir(book, ch, "vn-only", "docx"), get_chapter_root(book, ch) / "07-archive" / "vn-only" / "docx")

    def test_book_html_dir(self):
        book = "chemistry"
        self.assertEqual(get_book_html_dir(book), get_web_output_root() / book)

    def test_env_overrides(self):
        os.environ["BOOKS_ROOT"] = "custom-books"
        os.environ["WEB_OUTPUT_ROOT"] = "custom-site"

        self.assertEqual(get_books_root(), (WORKSPACE_ROOT / "custom-books").resolve())
        self.assertEqual(get_web_output_root(), (WORKSPACE_ROOT / "custom-site").resolve())

if __name__ == "__main__":
    unittest.main()
