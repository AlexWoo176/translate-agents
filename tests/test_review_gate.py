import unittest
import tempfile
import shutil
import os
import json
import csv
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.qa.review_gate import run_review_gate

class TestReviewGate(unittest.TestCase):
    def setUp(self):
        # Create temp folders structure
        self.test_dir = Path(tempfile.mkdtemp())
        self.book_slug = "test-gate-book"
        self.chapter = "1"

        self.book_root = self.test_dir / self.book_slug
        self.chapter_root = self.book_root / f"chapter-{self.chapter}"
        self.clean_dir = self.chapter_root / "02-clean"
        self.translated_dir = self.chapter_root / "05-translated"
        self.reviews_dir = self.chapter_root / "06-reviews"

        self.clean_dir.mkdir(parents=True, exist_ok=True)
        self.translated_dir.mkdir(parents=True, exist_ok=True)
        self.reviews_dir.mkdir(parents=True, exist_ok=True)

        # Glossary CSV
        self.glossary_csv = self.book_root / "glossary.csv"
        self.book_root.mkdir(parents=True, exist_ok=True)
        with open(self.glossary_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["term", "translation", "context", "status", "notes"])
            writer.writerow(["entrepreneur", "nhà khởi nghiệp", "", "approved", ""])

        # Clean HTML file
        self.clean_file = self.clean_dir / "01-intro.html"
        with open(self.clean_file, "w", encoding="utf-8") as f:
            f.write("<html><head><meta charset=\"utf-8\"/></head><body><p id=\"p1\">An entrepreneur starts a business.</p></body></html>")

        # Initial chapter.json
        self.chapter_json = self.chapter_root / "chapter.json"
        with open(self.chapter_json, "w", encoding="utf-8") as f:
            json.dump({"chapter_number": 1, "qa": {}}, f)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch("src.qa.review_gate.get_book_root")
    @patch("src.qa.review_gate.get_chapter_root")
    @patch("src.qa.review_gate.get_clean_dir")
    @patch("src.qa.review_gate.get_translated_dir")
    @patch("src.qa.review_gate.get_reviews_dir")
    def test_gate_passed(self, mock_get_reviews, mock_get_trans, mock_get_clean, mock_get_chap, mock_get_book):
        mock_get_book.return_value = self.book_root
        mock_get_chap.return_value = self.chapter_root
        mock_get_clean.return_value = self.clean_dir
        mock_get_trans.return_value = self.translated_dir
        mock_get_reviews.return_value = self.reviews_dir

        # Valid translated content
        trans_file = self.translated_dir / "01-intro.html"
        trans_content = (
            "<html><head><meta charset=\"utf-8\"/></head><body>"
            "<p class=\"eng hidden\" id=\"p1\">An entrepreneur starts a business.</p>"
            "<p class=\"vn visible\" id=\"p1-vn\">Một nhà khởi nghiệp bắt đầu doanh nghiệp.</p>"
            "</body></html>"
        )
        with open(trans_file, "w", encoding="utf-8") as f:
            f.write(trans_content)

        exit_code, summary = run_review_gate(self.book_slug, self.chapter)
        
        self.assertEqual(exit_code, 0)
        self.assertEqual(summary["integrity"], "passed")
        self.assertEqual(summary["glossary"], "passed")
        self.assertEqual(summary["math_encoding"], "passed")
        self.assertEqual(summary["review_gate"], "passed")

        # Verify chapter.json updated
        with open(self.chapter_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["qa"]["integrity"], "passed")
            self.assertEqual(data["qa"]["glossary"], "passed")
            self.assertEqual(data["qa"]["math_encoding"], "passed")
            self.assertEqual(data["qa"]["review_gate"], "passed")

        # Verify report written
        report_file = self.reviews_dir / f"chapter-{self.chapter}-review-gate.md"
        self.assertTrue(report_file.is_file())
        with open(report_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Gate Status:** ✅ PASSED", content)

    @patch("src.qa.review_gate.get_book_root")
    @patch("src.qa.review_gate.get_chapter_root")
    @patch("src.qa.review_gate.get_clean_dir")
    @patch("src.qa.review_gate.get_translated_dir")
    @patch("src.qa.review_gate.get_reviews_dir")
    def test_gate_fails_on_integrity(self, mock_get_reviews, mock_get_trans, mock_get_clean, mock_get_chap, mock_get_book):
        mock_get_book.return_value = self.book_root
        mock_get_chap.return_value = self.chapter_root
        mock_get_clean.return_value = self.clean_dir
        mock_get_trans.return_value = self.translated_dir
        mock_get_reviews.return_value = self.reviews_dir

        # Mismatched blocks (missing p1-vn) -> Integrity fails
        trans_file = self.translated_dir / "01-intro.html"
        trans_content = (
            "<html><head><meta charset=\"utf-8\"/></head><body>"
            "<p class=\"eng hidden\" id=\"p1\">An entrepreneur starts a business.</p>"
            "</body></html>"
        )
        with open(trans_file, "w", encoding="utf-8") as f:
            f.write(trans_content)

        exit_code, summary = run_review_gate(self.book_slug, self.chapter)

        self.assertEqual(exit_code, 1)
        self.assertEqual(summary["integrity"], "failed")
        self.assertEqual(summary["review_gate"], "failed")

        # Verify chapter.json updated
        with open(self.chapter_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["qa"]["integrity"], "failed")
            self.assertEqual(data["qa"]["review_gate"], "failed")

        # Verify report contains issues details
        report_file = self.reviews_dir / f"chapter-{self.chapter}-review-gate.md"
        self.assertTrue(report_file.is_file())
        with open(report_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Gate Status:** ❌ FAILED", content)
            self.assertIn("Structural Integrity Failures Details", content)

    @patch("src.qa.review_gate.get_book_root")
    @patch("src.qa.review_gate.get_chapter_root")
    @patch("src.qa.review_gate.get_clean_dir")
    @patch("src.qa.review_gate.get_translated_dir")
    @patch("src.qa.review_gate.get_reviews_dir")
    def test_gate_fails_on_glossary(self, mock_get_reviews, mock_get_trans, mock_get_clean, mock_get_chap, mock_get_book):
        mock_get_book.return_value = self.book_root
        mock_get_chap.return_value = self.chapter_root
        mock_get_clean.return_value = self.clean_dir
        mock_get_trans.return_value = self.translated_dir
        mock_get_reviews.return_value = self.reviews_dir

        # Valid block structures but missing glossary term translation ("nhà khởi nghiệp")
        trans_file = self.translated_dir / "01-intro.html"
        trans_content = (
            "<html><head><meta charset=\"utf-8\"/></head><body>"
            "<p class=\"eng hidden\" id=\"p1\">An entrepreneur starts a business.</p>"
            "<p class=\"vn visible\" id=\"p1-vn\">Một ai đó bắt đầu doanh nghiệp.</p>"
            "</body></html>"
        )
        with open(trans_file, "w", encoding="utf-8") as f:
            f.write(trans_content)

        exit_code, summary = run_review_gate(self.book_slug, self.chapter)

        self.assertEqual(exit_code, 1)
        self.assertEqual(summary["integrity"], "passed")
        self.assertEqual(summary["glossary"], "failed")
        self.assertEqual(summary["review_gate"], "failed")

        # Verify chapter.json updated
        with open(self.chapter_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["qa"]["glossary"], "failed")
            self.assertEqual(data["qa"]["review_gate"], "failed")

        # Verify report contains violations details
        report_file = self.reviews_dir / f"chapter-{self.chapter}-review-gate.md"
        self.assertTrue(report_file.is_file())
        with open(report_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Gate Status:** ❌ FAILED", content)
            self.assertIn("Glossary Consistency Violations Details", content)


if __name__ == "__main__":
    unittest.main()
