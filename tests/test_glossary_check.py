import unittest
import tempfile
import shutil
import os
import csv
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.qa.glossary_check import load_glossary, check_file_glossary
from src.cli.commands import review

class TestGlossaryCheck(unittest.TestCase):
    def setUp(self):
        # Create temp dir layout
        self.test_dir = Path(tempfile.mkdtemp())
        self.book_slug = "test-glossary-book"
        self.chapter = "1"

        self.book_root = self.test_dir / self.book_slug
        self.chapter_root = self.book_root / f"chapter-{self.chapter}"
        self.clean_dir = self.chapter_root / "02-clean"
        self.translated_dir = self.chapter_root / "05-translated"
        self.reviews_dir = self.chapter_root / "06-reviews"

        self.clean_dir.mkdir(parents=True, exist_ok=True)
        self.translated_dir.mkdir(parents=True, exist_ok=True)
        self.reviews_dir.mkdir(parents=True, exist_ok=True)

        # Standard CSV content
        self.glossary_csv = self.book_root / "glossary.csv"
        self.book_root.mkdir(parents=True, exist_ok=True)
        
        self.glossary_data = [
            {"term": "entrepreneur", "translation": "nhà khởi nghiệp", "context": "", "status": "approved", "notes": ""},
            {"term": "business", "translation": "doanh nghiệp", "context": "", "status": "approved", "notes": ""},
            {"term": "draft term", "translation": "nháp", "context": "", "status": "proposed", "notes": ""},
            {"term": "empty trans", "translation": "", "context": "", "status": "approved", "notes": ""}
        ]

        with open(self.glossary_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["term", "translation", "context", "status", "notes"])
            writer.writeheader()
            for row in self.glossary_data:
                writer.writerow(row)

        # Create sample files
        self.clean_file = self.clean_dir / "01-intro.html"
        with open(self.clean_file, "w", encoding="utf-8") as f:
            f.write("<html><body><p id=\"p1\">An entrepreneur starts a business.</p></body></html>")

        # Create mock chapter.json to satisfy dependency check
        self.chapter_json = self.chapter_root / "chapter.json"
        with open(self.chapter_json, "w", encoding="utf-8") as f:
            json.dump({
                "book": self.book_slug,
                "chapter": 1,
                "phases": {"translate": {"status": "completed"}}
            }, f)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_load_glossary(self):
        glossary = load_glossary(self.glossary_csv)
        # Should only load the 3 approved terms (entrepreneur, business, empty trans)
        # and ignore draft term (status=proposed)
        self.assertEqual(len(glossary), 3)
        terms = [item["term"] for item in glossary]
        self.assertIn("entrepreneur", terms)
        self.assertIn("business", terms)
        self.assertNotIn("draft term", terms)

    def test_glossary_pass(self):
        glossary = load_glossary(self.glossary_csv)
        trans_file = self.translated_dir / "01-intro.html"
        
        # English: "An entrepreneur starts a business."
        # Vietnamese: "Một nhà khởi nghiệp bắt đầu một doanh nghiệp." (Contains both translations)
        trans_content = (
            "<html><body>"
            "<p class=\"eng hidden\" id=\"p1\">An entrepreneur starts a business.</p>"
            "<p class=\"vn visible\" id=\"p1-vn\">Một nhà khởi nghiệp bắt đầu một doanh nghiệp.</p>"
            "</body></html>"
        )
        with open(trans_file, "w", encoding="utf-8") as f:
            f.write(trans_content)

        res = check_file_glossary(trans_file, glossary)
        self.assertEqual(res["status"], "PASS")
        self.assertEqual(len(res["violations"]), 0)

    def test_glossary_missing_translation(self):
        glossary = load_glossary(self.glossary_csv)
        trans_file = self.translated_dir / "01-intro.html"
        
        # Missing "nhà khởi nghiệp" translation for term "entrepreneur"
        trans_content = (
            "<html><body>"
            "<p class=\"eng hidden\" id=\"p1\">An entrepreneur starts a business.</p>"
            "<p class=\"vn visible\" id=\"p1-vn\">Một ai đó bắt đầu một doanh nghiệp.</p>"
            "</body></html>"
        )
        with open(trans_file, "w", encoding="utf-8") as f:
            f.write(trans_content)

        res = check_file_glossary(trans_file, glossary)
        self.assertEqual(res["status"], "FAIL")
        self.assertEqual(len(res["violations"]), 1)
        self.assertIn("missing in Vietnamese block", res["violations"][0]["reason"])

    def test_glossary_empty_translation(self):
        glossary = load_glossary(self.glossary_csv)
        trans_file = self.translated_dir / "01-intro.html"
        
        # Test empty translation block matching. English has "empty trans",
        # which exists in glossary with approved but empty translation.
        trans_content = (
            "<html><body>"
            "<p class=\"eng hidden\" id=\"p1\">An empty trans element here.</p>"
            "<p class=\"vn visible\" id=\"p1-vn\">Một phần tử rỗng ở đây.</p>"
            "</body></html>"
        )
        with open(trans_file, "w", encoding="utf-8") as f:
            f.write(trans_content)

        res = check_file_glossary(trans_file, glossary)
        self.assertEqual(res["status"], "FAIL")
        self.assertEqual(len(res["violations"]), 1)
        self.assertIn("approved translation is empty", res["violations"][0]["reason"])

    @patch("src.cli.commands.review.get_chapter_root")
    @patch("src.cli.commands.review.get_book_root")
    @patch("src.cli.commands.review.get_clean_dir")
    @patch("src.cli.commands.review.get_translated_dir")
    @patch("src.cli.commands.review.get_reviews_dir")
    def test_review_writes_glossary_reports(self, mock_get_reviews_dir, mock_get_translated_dir, mock_get_clean_dir, mock_get_book_root, mock_get_chapter_root):
        mock_get_chapter_root.return_value = self.chapter_root
        mock_get_book_root.return_value = self.book_root
        mock_get_clean_dir.return_value = self.clean_dir
        mock_get_translated_dir.return_value = self.translated_dir
        mock_get_reviews_dir.return_value = self.reviews_dir

        # Write mismatched translated file to trigger per-file report
        trans_file = self.translated_dir / "01-intro.html"
        trans_content = (
            "<html><body>"
            "<p class=\"eng hidden\" id=\"p1\">An entrepreneur starts a business.</p>"
            "<p class=\"vn visible\" id=\"p1-vn\">Một ai đó bắt đầu một doanh nghiệp.</p>"
            "</body></html>"
        )
        with open(trans_file, "w", encoding="utf-8") as f:
            f.write(trans_content)

        args = MagicMock()
        args.book = self.book_slug
        args.chapter = self.chapter
        args.check = "glossary"

        # Execute
        exit_code = review.run(args)
        self.assertEqual(exit_code, 1) # Mismatch should fail checking, exit_code=1

        # Assert report files exist
        summary_path = self.reviews_dir / f"chapter-{self.chapter}-glossary-summary.md"
        file_report_path = self.reviews_dir / "01-intro-glossary-review.md"

        self.assertTrue(summary_path.is_file())
        self.assertTrue(file_report_path.is_file())

        with open(summary_path, "r", encoding="utf-8") as f:
            self.assertIn("Glossary Review Summary", f.read())

        with open(file_report_path, "r", encoding="utf-8") as f:
            self.assertIn("Glossary Consistency Review", f.read())

if __name__ == "__main__":
    unittest.main()
