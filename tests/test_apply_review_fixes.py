import unittest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from src.pipeline.fix.apply_review_fixes import apply_review_fixes

class TestApplyReviewFixes(unittest.TestCase):
    def setUp(self):
        # Create temporary directories structure
        self.test_dir = Path(tempfile.mkdtemp())
        self.book_slug = "test-fix-book"
        self.chapter = "1"

        self.book_root = self.test_dir / self.book_slug
        self.chapter_root = self.book_root / f"chapter-{self.chapter}"
        self.translated_dir = self.chapter_root / "05-translated"
        self.reviews_dir = self.chapter_root / "06-reviews"

        self.translated_dir.mkdir(parents=True, exist_ok=True)
        self.reviews_dir.mkdir(parents=True, exist_ok=True)

        # Standard clean review markdown table
        self.review_md_content = (
            "# Báo cáo Nghiệm thu: 01-intro.html (Round 1)\n\n"
            "| ID | Thẻ Gốc | Bản dịch hiện tại | Phản biện | Đề xuất sửa | Trạng thái |\n"
            "|---|---|---|---|---|---|\n"
            "| 1 | p#fs-1234 | old translation | review commentary | new replacement | Mới |\n"
            "| 2 | p#fs-5678 | another old text | review comments | new suggestion | Mới |\n"
            "| 3 | p#ambig | duplicate text | review comments | suggestion | Mới |\n"
        )
        self.review_file = self.reviews_dir / "01-intro-semantic-review-round-1.md"
        with open(self.review_file, "w", encoding="utf-8") as f:
            f.write(self.review_md_content)

        # Standard HTML file structure
        self.html_content = (
            "<html>\n"
            "<body>\n"
            "  <p class=\"eng hidden\" id=\"fs-1234\">English original old translation text.</p>\n"
            "  <p class=\"vn visible\" id=\"fs-1234-vn\">old translation</p>\n"
            "  <p class=\"eng hidden\" id=\"fs-5678\">English another old text.</p>\n"
            "  <p class=\"vn visible\" id=\"fs-5678-vn\">another old text</p>\n"
            "  <p class=\"vn visible\" id=\"fs-dup-1-vn\">duplicate text</p>\n"
            "  <p class=\"vn visible\" id=\"fs-dup-2-vn\">duplicate text</p>\n"
            "</body>\n"
            "</html>"
        )
        self.html_file = self.translated_dir / "01-intro.html"
        with open(self.html_file, "w", encoding="utf-8") as f:
            f.write(self.html_content)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch("src.pipeline.fix.apply_review_fixes.get_reviews_dir")
    @patch("src.pipeline.fix.apply_review_fixes.get_translated_dir")
    def test_apply_fixes_workflow(self, mock_get_trans, mock_get_reviews):
        mock_get_reviews.return_value = self.reviews_dir
        mock_get_trans.return_value = self.translated_dir

        # Run fixes without dry run
        exit_code, result = apply_review_fixes(self.book_slug, self.chapter, dry_run=False)
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(result["applied"]), 2) # ID match for p#fs-1234 and p#fs-5678
        self.assertEqual(len(result["skipped"]), 1) # Ambiguous duplicate text skip

        # Verify HTML modified for .vn.visible and NOT for .eng.hidden
        with open(self.html_file, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # English hidden paragraph is unchanged
        eng_p = soup.find("p", id="fs-1234")
        self.assertIn("old translation text", eng_p.text)
        
        # Vietnamese visible paragraph is updated
        vn_p = soup.find("p", id="fs-1234-vn")
        self.assertEqual(vn_p.text, "new replacement")

        # Verify backup file created
        backup_file = self.translated_dir / "01-intro.html.bak"
        self.assertTrue(backup_file.is_file())
        with open(backup_file, "r", encoding="utf-8") as f:
            self.assertIn('<p class="vn visible" id="fs-1234-vn">old translation</p>', f.read())

        # Verify markdown review file updated with status 'Đã sửa' for applied rows
        with open(self.review_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("1 | p#fs-1234 | old translation | review commentary | new replacement | Đã sửa |", content)
            self.assertIn("3 | p#ambig | duplicate text | review comments | suggestion | Mới |", content) # skipped is unchanged

        # Verify diff report is generated
        diff_report = self.reviews_dir / f"chapter-{self.chapter}-fix-diff.md"
        self.assertTrue(diff_report.is_file())
        with open(diff_report, "r", encoding="utf-8") as f:
            report_text = f.read()
            self.assertIn("Applied Fixes Summary", report_text)
            self.assertIn("Ambiguous / Skipped Fixes (Not Applied)", report_text)
            self.assertIn("Ambiguous: text found in 2 different .vn.visible blocks", report_text)

    @patch("src.pipeline.fix.apply_review_fixes.get_reviews_dir")
    @patch("src.pipeline.fix.apply_review_fixes.get_translated_dir")
    def test_apply_fixes_dry_run(self, mock_get_trans, mock_get_reviews):
        mock_get_reviews.return_value = self.reviews_dir
        mock_get_trans.return_value = self.translated_dir

        # Run fixes with dry_run = True
        exit_code, result = apply_review_fixes(self.book_slug, self.chapter, dry_run=True)
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(result["applied"]), 2)
        self.assertEqual(len(result["skipped"]), 1)

        # Verify HTML file is completely unchanged
        with open(self.html_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), self.html_content)

        # Verify backup file is NOT created
        backup_file = self.translated_dir / "01-intro.html.bak"
        self.assertFalse(backup_file.is_file())

        # Verify markdown file is completely unchanged
        with open(self.review_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), self.review_md_content)

        # Verify diff report is generated
        diff_report = self.reviews_dir / f"chapter-{self.chapter}-fix-diff.md"
        self.assertTrue(diff_report.is_file())
        with open(diff_report, "r", encoding="utf-8") as f:
            self.assertIn("Dry Run Mode:** Active", f.read())

if __name__ == "__main__":
    unittest.main()
