import unittest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import CLI modules
from src.cli.commands import init_chapter

class TestInitChapter(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for chapter testing
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        # Remove temporary directory
        shutil.rmtree(self.test_dir)

    @patch("src.cli.commands.init_chapter.get_chapter_root")
    @patch("src.cli.commands.init_chapter.get_book_root")
    def test_init_chapter_creation(self, mock_get_book_root, mock_get_chapter_root):
        book_slug = "sample-book"
        book_root = self.test_dir / book_slug
        chapter_root = book_root / "chapter-5"

        mock_get_book_root.return_value = book_root
        mock_get_chapter_root.return_value = chapter_root

        # Pre-initialize status.json at book level
        book_root.mkdir(parents=True, exist_ok=True)
        with open(book_root / "status.json", "w", encoding="utf-8") as f:
            json.dump({"book": book_slug, "status": "initialized", "chapters": {}}, f)

        args = MagicMock()
        args.book = book_slug
        args.chapter = "5"
        args.force = False

        # Run init-chapter
        exit_code = init_chapter.run(args)
        self.assertEqual(exit_code, 0)

        # Assert subfolders exist
        self.assertTrue((chapter_root / "01-raw").is_dir())
        self.assertTrue((chapter_root / "02-clean").is_dir())
        self.assertTrue((chapter_root / "05-translated").is_dir())
        self.assertTrue((chapter_root / "07-archive/bilingual/html").is_dir())
        self.assertTrue((chapter_root / "07-archive/vn-only/pdf").is_dir())

        # Assert chapter.json exists and values are correct
        self.assertTrue((chapter_root / "chapter.json").is_file())
        with open(chapter_root / "chapter.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["book"], book_slug)
            self.assertEqual(data["chapter"], 5)
            self.assertEqual(data["status"], "initialized")

        # Verify parent status.json was updated with chapter key
        with open(book_root / "status.json", "r", encoding="utf-8") as f:
            status_data = json.load(f)
            self.assertIn("chapter-5", status_data["chapters"])
            self.assertEqual(status_data["chapters"]["chapter-5"]["status"], "initialized")

    @patch("src.cli.commands.init_chapter.get_chapter_root")
    @patch("src.cli.commands.init_chapter.get_book_root")
    def test_init_chapter_overwrite_protection(self, mock_get_book_root, mock_get_chapter_root):
        book_slug = "sample-book"
        book_root = self.test_dir / book_slug
        chapter_root = book_root / "chapter-1"

        mock_get_book_root.return_value = book_root
        mock_get_chapter_root.return_value = chapter_root

        # Pre-create files
        chapter_root.mkdir(parents=True, exist_ok=True)
        with open(chapter_root / "chapter.json", "w", encoding="utf-8") as f:
            f.write("custom-content")

        args = MagicMock()
        args.book = book_slug
        args.chapter = "1"
        args.force = False

        # Run without force
        exit_code = init_chapter.run(args)
        self.assertEqual(exit_code, 0)

        # Content should NOT be overwritten
        with open(chapter_root / "chapter.json", "r", encoding="utf-8") as f:
            content = f.read()
            self.assertEqual(content, "custom-content")

        # Run with force
        args.force = True
        exit_code = init_chapter.run(args)
        self.assertEqual(exit_code, 0)

        # Content should be overwritten with chapter json schema
        with open(chapter_root / "chapter.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["chapter"], 1)

if __name__ == "__main__":
    unittest.main()
