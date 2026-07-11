import unittest
import tempfile
import shutil
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.utils.status_helper import update_status, normalize_chapter_key
from src.cli.commands import status, prep, fix, archive, build

class TestStatusUpdates(unittest.TestCase):
    def setUp(self):
        # Create temp folder structure
        self.test_dir = Path(tempfile.mkdtemp())
        self.book_slug = "test-status-book"
        self.chapter = "1"

        self.book_root = self.test_dir / self.book_slug
        self.chapter_root = self.book_root / f"chapter-{self.chapter}"
        self.clean_dir = self.chapter_root / "02-clean"
        self.prep_dir = self.chapter_root / "04-prep"
        self.translated_dir = self.chapter_root / "05-translated"
        self.reviews_dir = self.chapter_root / "06-reviews"
        self.archive_dir = self.chapter_root / "07-archive"

        self.book_root.mkdir(parents=True, exist_ok=True)
        self.chapter_root.mkdir(parents=True, exist_ok=True)
        self.clean_dir.mkdir(parents=True, exist_ok=True)
        self.prep_dir.mkdir(parents=True, exist_ok=True)
        self.translated_dir.mkdir(parents=True, exist_ok=True)
        self.reviews_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # Initialize mock status.json and chapter.json
        self.status_json = self.book_root / "status.json"
        with open(self.status_json, "w", encoding="utf-8") as f:
            json.dump({
                "book": self.book_slug,
                "status": "initialized",
                "chapters": {}
            }, f)

        self.chapter_json = self.chapter_root / "chapter.json"
        with open(self.chapter_json, "w", encoding="utf-8") as f:
            json.dump({
                "book": self.book_slug,
                "chapter": 1,
                "status": "initialized",
                "qa": {"review_gate": "pending"}
            }, f)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch("src.utils.status_helper.get_book_root")
    @patch("src.utils.status_helper.get_chapter_root")
    def test_update_status_helper(self, mock_get_chapter_root, mock_get_book_root):
        mock_get_book_root.return_value = self.book_root
        mock_get_chapter_root.return_value = self.chapter_root

        # 1. Update prep phase success
        res = update_status(self.book_slug, self.chapter, phase="prep", status_str="completed", 
                            extra_metadata={"files_processed": 3})
        self.assertTrue(res)

        # Assert status.json updated
        with open(self.status_json, "r", encoding="utf-8") as f:
            status_data = json.load(f)
            self.assertEqual(status_data["chapters"]["chapter-1"]["status"], "prep_completed")
            self.assertIn("last_updated", status_data["chapters"]["chapter-1"])

        # Assert chapter.json updated
        with open(self.chapter_json, "r", encoding="utf-8") as f:
            chapter_data = json.load(f)
            self.assertEqual(chapter_data["status"], "prep_completed")
            self.assertEqual(chapter_data["phases"]["prep"]["status"], "completed")
            self.assertEqual(chapter_data["phases"]["prep"]["files_processed"], 3)
            self.assertIn("timestamp", chapter_data["phases"]["prep"])

        # 2. Update build phase
        res = update_status(self.book_slug, phase="build", status_str="completed", 
                            extra_metadata={"total_pages": 12})
        self.assertTrue(res)

        with open(self.status_json, "r", encoding="utf-8") as f:
            status_data = json.load(f)
            self.assertEqual(status_data["status"], "build_completed")
            self.assertEqual(status_data["build"]["status"], "completed")
            self.assertEqual(status_data["build"]["total_pages"], 12)

    @patch("src.cli.commands.prep.prep_chapter")
    @patch("src.utils.status_helper.get_book_root")
    @patch("src.utils.status_helper.get_chapter_root")
    def test_prep_command_updates_status(self, mock_get_chapter_root, mock_get_book_root, mock_prep_chapter):
        mock_get_book_root.return_value = self.book_root
        mock_get_chapter_root.return_value = self.chapter_root
        mock_prep_chapter.return_value = {"processed": ["file1.html"], "skipped": [], "failed": []}

        # Mock args
        args = MagicMock()
        args.book = self.book_slug
        args.chapter = self.chapter
        args.force = False

        exit_code = prep.run(args)
        self.assertEqual(exit_code, 0)

        # Check status recorded
        with open(self.chapter_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["phases"]["prep"]["status"], "completed")
            self.assertEqual(data["phases"]["prep"]["files_processed"], 1)

    @patch("src.cli.commands.status.get_book_root")
    @patch("src.cli.commands.status.get_chapter_root")
    @patch("sys.stdout")
    def test_status_dashboard_display(self, mock_stdout, mock_get_chapter_root, mock_get_book_root):
        mock_get_book_root.return_value = self.book_root
        mock_get_chapter_root.return_value = self.chapter_root

        # Populate statuses
        update_status(self.book_slug, self.chapter, phase="prep", status_str="completed")
        update_status(self.book_slug, phase="build", status_str="completed", extra_metadata={"total_pages": 5})

        # Run status command dashboard
        args = MagicMock()
        args.book = self.book_slug
        exit_code = status.run(args)
        self.assertEqual(exit_code, 0)

if __name__ == "__main__":
    unittest.main()
