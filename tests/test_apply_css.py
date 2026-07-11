import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import CLI modules
from src.cli.commands import apply_css

class TestApplyCss(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for book testing
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        # Remove temporary directory
        shutil.rmtree(self.test_dir)

    @patch("src.cli.commands.apply_css.get_book_root")
    def test_apply_css_creation(self, mock_get_book_root):
        book_slug = "sample-book"
        book_root = self.test_dir / book_slug
        mock_get_book_root.return_value = book_root

        # Pre-create book root folder (apply-css expects existing directory)
        book_root.mkdir(parents=True, exist_ok=True)

        args = MagicMock()
        args.book = book_slug
        args.force = False
        args.include_working = False
        args.include_raw = False
        args.chapter = None

        # Run apply-css
        exit_code = apply_css.run(args)
        self.assertEqual(exit_code, 0)

        # Assert stylesheet exists
        self.assertTrue((book_root / "css" / "style.css").is_file())

    @patch("src.cli.commands.apply_css.get_book_root")
    def test_apply_css_overwrite_protection(self, mock_get_book_root):
        book_slug = "sample-book"
        book_root = self.test_dir / book_slug
        mock_get_book_root.return_value = book_root

        # Pre-create files with custom content
        book_root.mkdir(parents=True, exist_ok=True)
        (book_root / "css").mkdir(parents=True, exist_ok=True)
        with open(book_root / "css" / "style.css", "w", encoding="utf-8") as f:
            f.write("custom-css")

        args = MagicMock()
        args.book = book_slug
        args.force = False
        args.include_working = False
        args.include_raw = False
        args.chapter = None

        # Run without force
        exit_code = apply_css.run(args)
        self.assertEqual(exit_code, 0)

        # File should NOT have been overwritten
        with open(book_root / "css" / "style.css", "r", encoding="utf-8") as f:
            content = f.read()
            self.assertEqual(content, "custom-css")

        # Run with force
        args.force = True
        exit_code = apply_css.run(args)
        self.assertEqual(exit_code, 0)

        # File should have been overwritten
        with open(book_root / "css" / "style.css", "r", encoding="utf-8") as f:
            content = f.read()
            self.assertNotEqual(content, "custom-css")

    @patch("src.cli.commands.apply_css.get_book_root")
    @patch("src.cli.commands.apply_css.get_chapter_root")
    @patch("src.cli.commands.apply_css.get_phase_dir")
    def test_apply_css_working_folders(self, mock_get_phase, mock_get_chap, mock_get_book):
        book_slug = "sample-book"
        chapter = "1"
        book_root = self.test_dir / book_slug
        chapter_root = book_root / f"chapter-{chapter}"
        
        mock_get_book.return_value = book_root
        mock_get_chap.return_value = chapter_root
        mock_get_phase.side_effect = lambda b, c, p: chapter_root / f"0{['raw', 'clean', 'analyzed', 'prep', 'translated'].index(p)}-{p}"

        # Create temporary working folder structure
        book_root.mkdir(parents=True, exist_ok=True)
        chapter_root.mkdir(parents=True, exist_ok=True)
        
        phases = ["raw", "clean", "prep", "translated"]
        phase_folders = {}
        for p in phases:
            p_dir = chapter_root / f"0{['raw', 'clean', 'analyzed', 'prep', 'translated'].index(p)}-{p}"
            p_dir.mkdir(parents=True, exist_ok=True)
            phase_folders[p] = p_dir
            
            # Write a sample HTML file
            with open(p_dir / "01-intro.html", "w", encoding="utf-8") as f:
                f.write("<html><head><title>Test</title></head><body><p>Hello</p></body></html>")

        # Run with --include-working (no --include-raw, force=False)
        args = MagicMock()
        args.book = book_slug
        args.chapter = chapter
        args.include_working = True
        args.include_raw = False
        args.force = False
        
        exit_code = apply_css.run(args)
        self.assertEqual(exit_code, 0)
        
        # Verify 02-clean, 04-prep, 05-translated got stylesheet link
        for p in ["clean", "prep", "translated"]:
            with open(phase_folders[p] / "01-intro.html", "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn('<link href="../../css/style.css" rel="stylesheet"/>', content)
                self.assertNotIn("book-reader.css", content)
                
        # Verify 01-raw remains unchanged
        with open(phase_folders["raw"] / "01-intro.html", "r", encoding="utf-8") as f:
            content = f.read()
            self.assertNotIn("style.css", content)

        # Run with --include-working AND --include-raw (force=True)
        args.include_raw = True
        args.force = True
        exit_code = apply_css.run(args)
        self.assertEqual(exit_code, 0)
        
        # Verify 01-raw now has stylesheet link
        with open(phase_folders["raw"] / "01-intro.html", "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn('<link href="../../css/style.css" rel="stylesheet"/>', content)

    @patch("src.cli.commands.apply_css.get_book_root")
    @patch("src.cli.commands.apply_css.get_chapter_root")
    @patch("src.cli.commands.apply_css.get_phase_dir")
    def test_apply_css_idempotent_no_duplicate_links(self, mock_get_phase, mock_get_chap, mock_get_book):
        """Running apply-css twice must not produce duplicate style.css links."""
        book_slug = "sample-book"
        chapter = "1"
        book_root = self.test_dir / book_slug
        chapter_root = book_root / f"chapter-{chapter}"

        mock_get_book.return_value = book_root
        mock_get_chap.return_value = chapter_root
        mock_get_phase.side_effect = lambda b, c, p: chapter_root / f"0{['raw', 'clean', 'analyzed', 'prep', 'translated'].index(p)}-{p}"

        book_root.mkdir(parents=True, exist_ok=True)
        chapter_root.mkdir(parents=True, exist_ok=True)

        clean_dir = chapter_root / "01-clean"
        clean_dir.mkdir(parents=True, exist_ok=True)
        with open(clean_dir / "01-intro.html", "w", encoding="utf-8") as f:
            f.write("<html><head><title>T</title></head><body><p>Hello</p></body></html>")

        args = type("args", (), {
            "book": book_slug, "chapter": chapter,
            "include_working": True, "include_raw": False, "force": False,
        })()

        # First run
        apply_css.run(args)
        # Second run
        apply_css.run(args)

        from bs4 import BeautifulSoup
        with open(clean_dir / "01-intro.html", "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        style_links = [
            lnk for lnk in soup.find_all("link", rel="stylesheet")
            if "style.css" in lnk.get("href", "")
        ]
        self.assertEqual(len(style_links), 1, "Running apply-css twice must not duplicate style.css links")

    @patch("src.cli.commands.apply_css.get_book_root")
    @patch("src.cli.commands.apply_css.get_chapter_root")
    @patch("src.cli.commands.apply_css.get_phase_dir")
    def test_raw_not_modified_without_include_raw(self, mock_get_phase, mock_get_chap, mock_get_book):
        """01-raw must NOT receive style.css when --include-raw is not set."""
        book_slug = "sample-book"
        chapter = "1"
        book_root = self.test_dir / book_slug
        chapter_root = book_root / f"chapter-{chapter}"

        mock_get_book.return_value = book_root
        mock_get_chap.return_value = chapter_root
        mock_get_phase.side_effect = lambda b, c, p: chapter_root / f"0{['raw', 'clean', 'analyzed', 'prep', 'translated'].index(p)}-{p}"

        book_root.mkdir(parents=True, exist_ok=True)
        chapter_root.mkdir(parents=True, exist_ok=True)

        raw_dir = chapter_root / "00-raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        original_content = "<html><head><title>Raw</title></head><body><p>Raw content</p></body></html>"
        with open(raw_dir / "01-intro.html", "w", encoding="utf-8") as f:
            f.write(original_content)

        clean_dir = chapter_root / "01-clean"
        clean_dir.mkdir(parents=True, exist_ok=True)
        with open(clean_dir / "01-intro.html", "w", encoding="utf-8") as f:
            f.write("<html><head><title>T</title></head><body></body></html>")

        args = type("args", (), {
            "book": book_slug, "chapter": chapter,
            "include_working": True, "include_raw": False, "force": False,
        })()

        apply_css.run(args)

        # 01-raw should not have been modified
        with open(raw_dir / "01-intro.html", "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("style.css", content,
                         "01-raw must not receive style.css without --include-raw")
        self.assertEqual(content, original_content, "01-raw file content must be unchanged")


if __name__ == "__main__":
    unittest.main()
