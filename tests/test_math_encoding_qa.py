import unittest
import tempfile
import shutil
import json
from pathlib import Path
from bs4 import BeautifulSoup
from unittest.mock import patch

from src.qa.math_encoding_qa import (
    has_mojibake,
    check_mathml_parity,
    check_formula_fragment_parity,
    run_math_encoding_qa
)
from src.cli.commands import qa_math, repair_encoding
from src.pipeline.archive.archive_chapter import archive_chapter

class TestMathEncodingQA(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.book_slug = "test-math-book"
        self.chapter = "1"
        self.book_root = self.test_dir / self.book_slug
        self.chapter_root = self.book_root / f"chapter-{self.chapter}"
        self.translated_dir = self.chapter_root / "05-translated"
        
        self.book_root.mkdir(parents=True, exist_ok=True)
        self.chapter_root.mkdir(parents=True, exist_ok=True)
        self.translated_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_mojibake_detection_fails(self):
        bad_examples = ["Î¼", "Ï", "Î±", "â¤", "â", "Â¯", "hello â world", "val Â¯"]
        for bad in bad_examples:
            self.assertTrue(has_mojibake(bad), f"Failed to detect mojibake in: {bad}")

    def test_mojibake_detection_passes(self):
        good_examples = [
            "μ", "σ", "α", "≤", "≥", "x̄",
            "câu hỏi", "đây là", "dân số", "âm nhạc",
            "Giả thuyết không H0", "Mức ý nghĩa α"
        ]
        for good in good_examples:
            self.assertFalse(has_mojibake(good), f"Incorrectly flagged valid text as mojibake: {good}")

    def test_mathml_parity_passes(self):
        eng = BeautifulSoup('<p><math><mfrac><mn>1</mn><mn>2</mn></mfrac></math></p>', 'html.parser')
        vn = BeautifulSoup('<p><math><mfrac><mn>1</mn><mn>2</mn></mfrac></math></p>', 'html.parser')
        ok, err = check_mathml_parity(eng, vn)
        self.assertTrue(ok)
        self.assertEqual(err, "")

    def test_mathml_parity_fails_on_lost_node(self):
        eng = BeautifulSoup('<p><math><mfrac><mn>1</mn><mn>2</mn></mfrac></math></p>', 'html.parser')
        vn_lost = BeautifulSoup('<p>1/2</p>', 'html.parser')
        ok, err = check_mathml_parity(eng, vn_lost)
        self.assertFalse(ok)
        self.assertIn("MathML count mismatch", err)

    def test_mathml_parity_fails_on_structure_mismatch(self):
        eng = BeautifulSoup('<p><math><mfrac><mn>1</mn><mn>2</mn></mfrac></math></p>', 'html.parser')
        vn_mutated = BeautifulSoup('<p><math><msqrt><mn>2</mn></msqrt></math></p>', 'html.parser')
        ok, err = check_mathml_parity(eng, vn_mutated)
        self.assertFalse(ok)
        self.assertIn("MathML structure mismatch", err)

    def test_formula_fragment_parity_fails_on_missing_h0(self):
        eng = BeautifulSoup('<p>Hypothesis H<sub>0</sub> is true.</p>', 'html.parser')
        vn = BeautifulSoup('<p>Giả thuyết Ha là đúng.</p>', 'html.parser')
        ok, err = check_formula_fragment_parity(eng, vn)
        self.assertFalse(ok)
        self.assertIn("H0", err)

    def test_formula_fragment_parity_fails_on_corrupted_greek(self):
        eng = BeautifulSoup('<p>Standard deviation is σ.</p>', 'html.parser')
        vn = BeautifulSoup('<p>Độ lệch chuẩn là Ï.</p>', 'html.parser')
        ok, err = check_formula_fragment_parity(eng, vn)
        self.assertFalse(ok)
        self.assertIn("Greek symbol 'σ'", err)

    def test_formula_fragment_parity_fails_on_corrupted_operator(self):
        eng = BeautifulSoup('<p>Value ≤ 5.</p>', 'html.parser')
        vn = BeautifulSoup('<p>Giá trị â¤ 5.</p>', 'html.parser')
        ok, err = check_formula_fragment_parity(eng, vn)
        self.assertFalse(ok)
        self.assertIn("Math operator '≤'", err)

    def test_formula_fragment_parity_fails_on_missing_p_value(self):
        eng = BeautifulSoup('<p>The p-value is small.</p>', 'html.parser')
        vn = BeautifulSoup('<p>Giá trị nhỏ.</p>', 'html.parser')
        ok, err = check_formula_fragment_parity(eng, vn)
        self.assertFalse(ok)
        self.assertIn("p-value", err)

    @patch("src.cli.commands.qa_math.get_book_root")
    @patch("src.cli.commands.qa_math.get_translated_dir")
    def test_qa_math_command_execution(self, mock_get_trans, mock_get_book):
        mock_get_book.return_value = self.book_root
        mock_get_trans.return_value = self.translated_dir

        # 1. Create a good fixture file
        good_file = self.translated_dir / "good.html"
        good_content = (
            "<html><head><meta charset=\"utf-8\"/></head><body>"
            "<p class=\"eng hidden\" id=\"p1\">Let H0 be p = 0.50.</p>"
            "<p class=\"vn visible\" id=\"p1-vn\">Hãy chọn H0 là p = 0.50.</p>"
            "</body></html>"
        )
        with open(good_file, "w", encoding="utf-8") as f:
            f.write(good_content)

        # Create CLI arguments mock
        class Args:
            book = "test-math-book"
            chapter = "1"
            file = "good.html"

        exit_code_good = qa_math.run(Args())
        self.assertEqual(exit_code_good, 0)

        # 2. Create a bad fixture file (contains mojibake)
        bad_file = self.translated_dir / "bad.html"
        bad_content = (
            "<html><head><meta charset=\"utf-8\"/></head><body>"
            "<p class=\"eng hidden\" id=\"p2\">Let H0 be μ = 0.50.</p>"
            "<p class=\"vn visible\" id=\"p2-vn\">Hãy chọn H0 là Î¼ = 0.50.</p>"
            "</body></html>"
        )
        with open(bad_file, "w", encoding="utf-8") as f:
            f.write(bad_content)

        class ArgsBad:
            book = "test-math-book"
            chapter = "1"
            file = "bad.html"

        exit_code_bad = qa_math.run(ArgsBad())
        self.assertEqual(exit_code_bad, 1)

    @patch("src.cli.commands.repair_encoding.get_book_root")
    @patch("src.cli.commands.repair_encoding.get_phase_dir")
    def test_repair_encoding_command(self, mock_get_phase, mock_get_book):
        mock_get_book.return_value = self.book_root
        mock_get_phase.return_value = self.translated_dir

        corrupted_content = (
            "<html><body>"
            "<p>Let standard deviation be Ïσ and mean be Î¼. Also value â¤ 5.</p>"
            "<p>Valid Vietnamese câu hỏi và đây là dân số.</p>"
            "</body></html>"
        )
        test_file = self.translated_dir / "corrupted.html"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(corrupted_content)

        # 1. Test Dry Run (does not modify file)
        class ArgsDry:
            book = "test-math-book"
            chapter = "1"
            file = "corrupted.html"
            stage = "translated"
            dry_run = True

        exit_code_dry = repair_encoding.run(ArgsDry())
        self.assertEqual(exit_code_dry, 0)

        with open(test_file, "r", encoding="utf-8") as f:
            content_after_dry = f.read()
        self.assertEqual(content_after_dry, corrupted_content)

        # 2. Test Real Run (modifies file)
        class ArgsReal:
            book = "test-math-book"
            chapter = "1"
            file = "corrupted.html"
            stage = "translated"
            dry_run = False

        exit_code_real = repair_encoding.run(ArgsReal())
        self.assertEqual(exit_code_real, 0)

        with open(test_file, "r", encoding="utf-8") as f:
            repaired_content = f.read()
        
        self.assertIn("standard deviation be σ", repaired_content)
        self.assertIn("mean be μ", repaired_content)
        self.assertIn("value ≤ 5", repaired_content)
        # Verify it doesn't affect unrelated Vietnamese text
        self.assertIn("câu hỏi và đây là dân số", repaired_content)

    @patch("src.pipeline.archive.archive_chapter.get_chapter_root")
    @patch("src.pipeline.archive.archive_chapter.get_translated_dir")
    def test_archive_blocked_on_qa_fail(self, mock_get_trans, mock_get_chap):
        mock_get_chap.return_value = self.chapter_root
        mock_get_trans.return_value = self.translated_dir

        # Create a dummy HTML file so file existence check passes
        dummy_file = self.translated_dir / "dummy.html"
        with open(dummy_file, "w", encoding="utf-8") as f:
            f.write("<html></html>")

        chapter_json_path = self.chapter_root / "chapter.json"
        
        # 1. QA is failed
        chapter_data_fail = {
            "phases": {"translate": {"status": "completed"}},
            "qa": {"review_gate": "failed"}
        }
        with open(chapter_json_path, "w", encoding="utf-8") as f:
            json.dump(chapter_data_fail, f)

        # Run archive with force=False -> Blocked (exit code 1)
        exit_code, res = archive_chapter(self.book_slug, self.chapter, force=False)
        self.assertEqual(exit_code, 1)
        self.assertIn("QA review gate is not passed", res)

        # Run archive with force=True -> Passes gate logic (proceeds to exporters)
        exit_code_forced, res_forced = archive_chapter(self.book_slug, self.chapter, force=True)
        self.assertNotEqual(res_forced, "QA review gate is not passed (status is 'failed'). Archiving blocked. Use --force to override.")

