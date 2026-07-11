import unittest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.qa.integrity_check import check_file_integrity
from src.cli.commands import review

class TestIntegrityCheck(unittest.TestCase):
    def setUp(self):
        # Create temp dir structure
        self.test_dir = Path(tempfile.mkdtemp())
        self.book_slug = "test-review-book"
        self.chapter = "1"

        self.book_root = self.test_dir / self.book_slug
        self.chapter_root = self.book_root / f"chapter-{self.chapter}"
        self.clean_dir = self.chapter_root / "02-clean"
        self.translated_dir = self.chapter_root / "05-translated"
        self.reviews_dir = self.chapter_root / "06-reviews"

        self.clean_dir.mkdir(parents=True, exist_ok=True)
        self.translated_dir.mkdir(parents=True, exist_ok=True)
        self.reviews_dir.mkdir(parents=True, exist_ok=True)

        # Standard inputs
        self.clean_content = (
            "<html>\n"
            "<body>\n"
            "  <h1 id=\"t1\">Title</h1>\n"
            "  <p id=\"p1\">Paragraph content <span>bold clean</span></p>\n"
            "</body>\n"
            "</html>"
        )
        self.trans_content_pass = (
            "<html>\n"
            "<body>\n"
            "  <h1 class=\"eng hidden\" id=\"t1\">Title</h1>\n"
            "  <h1 class=\"vn visible\" id=\"t1-vn\">Tiêu đề</h1>\n"
            "  <p class=\"eng hidden\" id=\"p1\">Paragraph content <span>bold clean</span></p>\n"
            "  <p class=\"vn visible\" id=\"p1-vn\">Nội dung đoạn văn <span>bold clean</span></p>\n"
            "</body>\n"
            "</html>"
        )

        self.clean_file = self.clean_dir / "01-intro.html"
        with open(self.clean_file, "w", encoding="utf-8") as f:
            f.write(self.clean_content)

        # Create mock chapter.json to satisfy dependency check
        import json
        self.chapter_json = self.chapter_root / "chapter.json"
        with open(self.chapter_json, "w", encoding="utf-8") as f:
            json.dump({
                "book": self.book_slug,
                "chapter": 1,
                "phases": {"translate": {"status": "completed"}}
            }, f)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_integrity_pass(self):
        trans_file = self.translated_dir / "01-intro.html"
        with open(trans_file, "w", encoding="utf-8") as f:
            f.write(self.trans_content_pass)

        res = check_file_integrity(self.clean_file, trans_file)
        self.assertEqual(res["status"], "PASS")
        self.assertEqual(len(res["issues"]), 0)

    def test_integrity_missing_translated_file(self):
        trans_file = self.translated_dir / "01-intro.html" # Doesn't exist

        res = check_file_integrity(self.clean_file, trans_file)
        self.assertEqual(res["status"], "FAIL")
        self.assertTrue(any("not found" in issue for issue in res["issues"]))

    def test_integrity_empty_translated_file(self):
        trans_file = self.translated_dir / "01-intro.html"
        with open(trans_file, "w", encoding="utf-8") as f:
            f.write("   ") # empty

        res = check_file_integrity(self.clean_file, trans_file)
        self.assertEqual(res["status"], "FAIL")
        self.assertTrue(any("Empty file" in issue or "Translated file error" in issue for issue in res["issues"]))

    def test_integrity_missing_vn_visible(self):
        # Missing vn visible paragraph
        trans_content = (
            "<html>\n"
            "<body>\n"
            "  <h1 class=\"eng hidden\" id=\"t1\">Title</h1>\n"
            "  <h1 class=\"vn visible\" id=\"t1-vn\">Tiêu đề</h1>\n"
            "  <p class=\"eng hidden\" id=\"p1\">Paragraph content</p>\n" # missing p1-vn
            "</body>\n"
            "</html>"
        )
        trans_file = self.translated_dir / "01-intro.html"
        with open(trans_file, "w", encoding="utf-8") as f:
            f.write(trans_content)

        res = check_file_integrity(self.clean_file, trans_file)
        self.assertEqual(res["status"], "FAIL")
        self.assertTrue(any("counts inside translation pairs" in issue or "counts: .eng.hidden" in issue for issue in res["issues"]))

    def test_integrity_missing_eng_hidden(self):
        # Missing eng hidden h1
        trans_content = (
            "<html>\n"
            "<body>\n"
            "  <h1 class=\"vn visible\" id=\"t1-vn\">Tiêu đề</h1>\n" # missing t1
            "  <p class=\"eng hidden\" id=\"p1\">Paragraph content</p>\n"
            "  <p class=\"vn visible\" id=\"p1-vn\">Nội dung đoạn văn</p>\n"
            "</body>\n"
            "</html>"
        )
        trans_file = self.translated_dir / "01-intro.html"
        with open(trans_file, "w", encoding="utf-8") as f:
            f.write(trans_content)

        res = check_file_integrity(self.clean_file, trans_file)
        self.assertEqual(res["status"], "FAIL")
        self.assertTrue(any("clean has 1, translated .eng.hidden has 0" in issue for issue in res["issues"]))

    def test_integrity_mismatched_inline_tag_counts(self):
        # Cloned paragraph is missing the <span> tag inside
        trans_content = (
            "<html>\n"
            "<body>\n"
            "  <h1 class=\"eng hidden\" id=\"t1\">Title</h1>\n"
            "  <h1 class=\"vn visible\" id=\"t1-vn\">Tiêu đề</h1>\n"
            "  <p class=\"eng hidden\" id=\"p1\">Paragraph content <span>bold clean</span></p>\n"
            "  <p class=\"vn visible\" id=\"p1-vn\">Nội dung đoạn văn bold clean</p>\n" # missing <span>
            "</body>\n"
            "</html>"
        )
        trans_file = self.translated_dir / "01-intro.html"
        with open(trans_file, "w", encoding="utf-8") as f:
            f.write(trans_content)

        res = check_file_integrity(self.clean_file, trans_file)
        self.assertEqual(res["status"], "FAIL")
        self.assertTrue(any("Mismatched inline <span" in issue for issue in res["issues"]))

    @patch("src.cli.commands.review.get_chapter_root")
    @patch("src.cli.commands.review.get_book_root")
    @patch("src.cli.commands.review.get_clean_dir")
    @patch("src.cli.commands.review.get_translated_dir")
    @patch("src.cli.commands.review.get_reviews_dir")
    def test_review_writes_report(self, mock_get_reviews_dir, mock_get_translated_dir, mock_get_clean_dir, mock_get_book_root, mock_get_chapter_root):
        mock_get_chapter_root.return_value = self.chapter_root
        mock_get_book_root.return_value = self.book_root
        mock_get_clean_dir.return_value = self.clean_dir
        mock_get_translated_dir.return_value = self.translated_dir
        mock_get_reviews_dir.return_value = self.reviews_dir

        # Write matching file
        trans_file = self.translated_dir / "01-intro.html"
        with open(trans_file, "w", encoding="utf-8") as f:
            f.write(self.trans_content_pass)

        args = MagicMock()
        args.book = self.book_slug
        args.chapter = self.chapter
        args.check = "integrity"

        # Execute command
        exit_code = review.run(args)
        self.assertEqual(exit_code, 0)

        # Assert report file exists
        report_file = self.reviews_dir / f"chapter-{self.chapter}-integrity-report.md"
        self.assertTrue(report_file.is_file())
        with open(report_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Structural Integrity Verification Report", content)
            self.assertIn("01-intro.html", content)
            self.assertIn("✅ PASS", content)

if __name__ == "__main__":
    unittest.main()
