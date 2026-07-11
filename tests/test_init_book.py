import unittest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import CLI modules
from src.cli.commands import init_book

class TestInitBook(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for book testing
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        # Remove temporary directory
        shutil.rmtree(self.test_dir)

    @patch("src.cli.commands.init_book.get_book_root")
    def test_init_book_creation(self, mock_get_book_root):
        book_slug = "sample-book"
        book_root = self.test_dir / book_slug
        mock_get_book_root.return_value = book_root

        args = MagicMock()
        args.book = book_slug
        args.force = False

        # Run init-book
        exit_code = init_book.run(args)
        self.assertEqual(exit_code, 0)

        # Assert folders exist
        self.assertTrue((book_root / "css").is_dir())
        self.assertTrue((book_root / "assets").is_dir())
        self.assertTrue((book_root / "_book-level").is_dir())

        # Assert files exist
        self.assertTrue((book_root / "css" / "style.css").is_file())
        self.assertTrue((book_root / "book.json").is_file())
        self.assertTrue((book_root / "glossary.csv").is_file())
        self.assertTrue((book_root / "status.json").is_file())
        self.assertTrue((book_root / "tasks.md").is_file())

        # Verify book.json contents
        with open(book_root / "book.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["slug"], book_slug)
            self.assertEqual(data["status"], "initialized")

        # Verify glossary header
        with open(book_root / "glossary.csv", "r", encoding="utf-8") as f:
            header = f.readline().strip()
            self.assertEqual(header, "term,translation,context,status,notes")

    @patch("src.cli.commands.init_book.get_book_root")
    def test_init_book_overwrite_protection(self, mock_get_book_root):
        book_slug = "sample-book"
        book_root = self.test_dir / book_slug
        mock_get_book_root.return_value = book_root

        # Pre-create files with custom content
        book_root.mkdir(parents=True, exist_ok=True)
        (book_root / "css").mkdir(parents=True, exist_ok=True)
        with open(book_root / "book.json", "w", encoding="utf-8") as f:
            f.write("custom-content")
        with open(book_root / "css" / "style.css", "w", encoding="utf-8") as f:
            f.write("custom-css")

        args = MagicMock()
        args.book = book_slug
        args.force = False

        # Run without force
        exit_code = init_book.run(args)
        self.assertEqual(exit_code, 0)

        # File should NOT have been overwritten
        with open(book_root / "book.json", "r", encoding="utf-8") as f:
            content = f.read()
            self.assertEqual(content, "custom-content")
        with open(book_root / "css" / "style.css", "r", encoding="utf-8") as f:
            content = f.read()
            self.assertEqual(content, "custom-css")

        # Run with force
        args.force = True
        exit_code = init_book.run(args)
        self.assertEqual(exit_code, 0)

        # File should have been overwritten with json structure and CSS template
        with open(book_root / "book.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["slug"], book_slug)
        with open(book_root / "css" / "style.css", "r", encoding="utf-8") as f:
            content = f.read()
            self.assertNotEqual(content, "custom-css")

if __name__ == "__main__":
    unittest.main()
