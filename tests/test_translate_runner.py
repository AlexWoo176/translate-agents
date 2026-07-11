import unittest
import tempfile
import shutil
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from src.pipeline.translate.translate_runner import (
    translate_chapter,
    protect_structures,
    restore_structures,
    validate_translation_integrity
)

class TestTranslateRunner(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.book_slug = "test-translate-book"
        self.chapter = "1"

        self.book_root = self.test_dir / self.book_slug
        self.chapter_root = self.book_root / f"chapter-{self.chapter}"
        self.prep_dir = self.chapter_root / "04-prep"
        self.translated_dir = self.chapter_root / "05-translated"
        self.reviews_dir = self.chapter_root / "06-reviews"

        self.prep_dir.mkdir(parents=True, exist_ok=True)
        self.translated_dir.mkdir(parents=True, exist_ok=True)
        self.reviews_dir.mkdir(parents=True, exist_ok=True)

        # Create glossary
        self.glossary_csv = self.book_root / "glossary.csv"
        self.glossary_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(self.glossary_csv, "w", encoding="utf-8") as f:
            f.write("term,translation,context,status,notes\n")
            f.write("probability,xác suất,math,approved,notes\n")

        # Create sample prep HTML
        self.sample_html = (
            "<html>\n"
            "<head><style>.eng.hidden { display: none; }</style></head>\n"
            "<body>\n"
            '  <p id="fs-1" class="eng hidden">Probability is important.</p>\n'
            '  <p id="fs-1-vn" class="vn visible">Probability is important.</p>\n'
            '  <p id="fs-2" class="eng hidden">Formula <math><mfrac><mn>1</mn><mn>2</mn></mfrac></math> here.</p>\n'
            '  <p id="fs-2-vn" class="vn visible">Formula <math><mfrac><mn>1</mn><mn>2</mn></mfrac></math> here.</p>\n'
            "</body>\n"
            "</html>\n"
        )
        self.prep_file = self.prep_dir / "1-1-intro.html"
        with open(self.prep_file, "w", encoding="utf-8") as f:
            f.write(self.sample_html)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch("src.pipeline.translate.translate_runner.get_config")
    @patch("src.pipeline.translate.translate_runner.get_prep_dir")
    @patch("src.pipeline.translate.translate_runner.get_translated_dir")
    @patch("src.pipeline.translate.translate_runner.get_reviews_dir")
    @patch("src.pipeline.translate.translate_runner.get_book_root")
    def test_missing_api_key(self, mock_book_root, mock_reviews_dir, mock_trans_dir, mock_prep_dir, mock_get_config):
        mock_book_root.return_value = self.book_root
        mock_reviews_dir.return_value = self.reviews_dir
        mock_trans_dir.return_value = self.translated_dir
        mock_prep_dir.return_value = self.prep_dir
        
        # API Key is None
        mock_get_config.side_effect = lambda key, default=None: None if key == "GEMINI_API_KEY" else default

        # Temporarily remove from environment to verify fallback fails
        old_env_key = os.environ.pop("GEMINI_API_KEY", None)
        try:
            with self.assertRaises(ValueError) as context:
                translate_chapter(self.book_slug, self.chapter, provider="gemini-api")
            self.assertIn("GEMINI_API_KEY environment variable or config value is missing", str(context.exception))
        finally:
            if old_env_key is not None:
                os.environ["GEMINI_API_KEY"] = old_env_key

    @patch("src.pipeline.translate.translate_runner.get_prep_dir")
    @patch("src.pipeline.translate.translate_runner.get_translated_dir")
    @patch("src.pipeline.translate.translate_runner.get_reviews_dir")
    @patch("src.pipeline.translate.translate_runner.get_book_root")
    def test_default_translate_does_not_require_api_key(self, mock_book_root, mock_reviews_dir, mock_trans_dir, mock_prep_dir):
        mock_book_root.return_value = self.book_root
        mock_reviews_dir.return_value = self.reviews_dir
        mock_trans_dir.return_value = self.translated_dir
        mock_prep_dir.return_value = self.prep_dir

        # Delete any pre-existing translated file to test copy
        out_file = self.translated_dir / "1-1-intro.html"
        if out_file.exists():
            out_file.unlink()

        # Should not raise ValueError even with missing API Key
        results = translate_chapter(self.book_slug, self.chapter, provider="agent")
        self.assertTrue(out_file.is_file())
        self.assertEqual(len(results["failed"]), 1)
        self.assertIn("missing", results["failed"][0]["error"].lower())

        # Second run: file exists but is untranslated template
        results2 = translate_chapter(self.book_slug, self.chapter, provider="agent")
        self.assertEqual(len(results2["failed"]), 1)
        self.assertIn("untranslated", results2["failed"][0]["error"].lower())

    @patch("src.pipeline.translate.translate_runner.get_prep_dir")
    @patch("src.pipeline.translate.translate_runner.get_translated_dir")
    @patch("src.pipeline.translate.translate_runner.get_reviews_dir")
    @patch("src.pipeline.translate.translate_runner.get_book_root")
    def test_provider_manual_copies_and_runs_successfully(self, mock_book_root, mock_reviews_dir, mock_trans_dir, mock_prep_dir):
        mock_book_root.return_value = self.book_root
        mock_reviews_dir.return_value = self.reviews_dir
        mock_trans_dir.return_value = self.translated_dir
        mock_prep_dir.return_value = self.prep_dir

        out_file = self.translated_dir / "1-1-intro.html"
        if out_file.exists():
            out_file.unlink()

        results = translate_chapter(self.book_slug, self.chapter, provider="manual")
        self.assertEqual(len(results["processed"]), 1)
        self.assertEqual(len(results["failed"]), 0)
        self.assertTrue(out_file.is_file())

        with open(out_file, "r", encoding="utf-8") as f:
            out_soup = BeautifulSoup(f.read(), "html.parser")
        links = out_soup.find_all("link", rel="stylesheet")
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["href"], "../../css/style.css")
        self.assertNotIn("book-reader.css", str(out_soup))
        
        # Verify run report created
        report = self.reviews_dir / f"chapter-{self.chapter}-translation-run.md"
        self.assertTrue(report.is_file())
        with open(report, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Provider: manual", content)
            self.assertIn("Resulting Status:** TRANSLATION_READY", content)

    @patch("src.pipeline.translate.translate_runner.get_prep_dir")
    @patch("src.pipeline.translate.translate_runner.get_translated_dir")
    @patch("src.pipeline.translate.translate_runner.get_reviews_dir")
    @patch("src.pipeline.translate.translate_runner.get_book_root")
    def test_provider_agent_validates_partially_translated(self, mock_book_root, mock_reviews_dir, mock_trans_dir, mock_prep_dir):
        mock_book_root.return_value = self.book_root
        mock_reviews_dir.return_value = self.reviews_dir
        mock_trans_dir.return_value = self.translated_dir
        mock_prep_dir.return_value = self.prep_dir

        # Write partially translated file (one block changed, one matching English)
        partial_html = (
            "<html>\n"
            "<body>\n"
            '  <p id="fs-1" class="eng hidden">Probability is important.</p>\n'
            '  <p id="fs-1-vn" class="vn visible">Xác suất là quan trọng.</p>\n'
            '  <p id="fs-2" class="eng hidden">Formula <math><mfrac><mn>1</mn><mn>2</mn></mfrac></math> here.</p>\n'
            '  <p id="fs-2-vn" class="vn visible">Formula <math><mfrac><mn>1</mn><mn>2</mn></mfrac></math> here.</p>\n'
            "</body>\n"
            "</html>"
        )
        out_file = self.translated_dir / "1-1-intro.html"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(partial_html)

        results = translate_chapter(self.book_slug, self.chapter, provider="agent")
        self.assertEqual(len(results["failed"]), 1)
        self.assertIn("partially untranslated", results["failed"][0]["error"])

    @patch("src.pipeline.translate.translate_runner.get_prep_dir")
    @patch("src.pipeline.translate.translate_runner.get_translated_dir")
    @patch("src.pipeline.translate.translate_runner.get_reviews_dir")
    @patch("src.pipeline.translate.translate_runner.get_book_root")
    def test_provider_agent_validates_fully_translated_success(self, mock_book_root, mock_reviews_dir, mock_trans_dir, mock_prep_dir):
        mock_book_root.return_value = self.book_root
        mock_reviews_dir.return_value = self.reviews_dir
        mock_trans_dir.return_value = self.translated_dir
        mock_prep_dir.return_value = self.prep_dir

        # Write fully translated file (both blocks changed)
        translated_html = (
            "<html>\n"
            "<body>\n"
            '  <p id="fs-1" class="eng hidden">Probability is important.</p>\n'
            '  <p id="fs-1-vn" class="vn visible">Xác suất là quan trọng.</p>\n'
            '  <p id="fs-2" class="eng hidden">Formula <math><mfrac><mn>1</mn><mn>2</mn></mfrac></math> here.</p>\n'
            '  <p id="fs-2-vn" class="vn visible">Công thức <math><mfrac><mn>1</mn><mn>2</mn></mfrac></math> ở đây.</p>\n'
            "</body>\n"
            "</html>"
        )
        out_file = self.translated_dir / "1-1-intro.html"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(translated_html)

        results = translate_chapter(self.book_slug, self.chapter, provider="agent")
        self.assertEqual(len(results["processed"]), 1)
        self.assertEqual(len(results["failed"]), 0)

        # Verify run report shows TRANSLATED
        report = self.reviews_dir / f"chapter-{self.chapter}-translation-run.md"
        with open(report, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Resulting Status:** TRANSLATED", content)

    @patch("src.pipeline.translate.translate_runner.requests.post")
    @patch("src.pipeline.translate.translate_runner.get_config")
    @patch("src.pipeline.translate.translate_runner.get_prep_dir")
    @patch("src.pipeline.translate.translate_runner.get_translated_dir")
    @patch("src.pipeline.translate.translate_runner.get_reviews_dir")
    @patch("src.pipeline.translate.translate_runner.get_book_root")
    def test_malformed_json_triggers_fallback_and_fails(self, mock_book_root, mock_reviews_dir, mock_trans_dir, mock_prep_dir, mock_get_config, mock_post):
        mock_book_root.return_value = self.book_root
        mock_reviews_dir.return_value = self.reviews_dir
        mock_trans_dir.return_value = self.translated_dir
        mock_prep_dir.return_value = self.prep_dir
        
        mock_get_config.side_effect = lambda key, default=None: "api-key" if key == "GEMINI_API_KEY" else default

        # Mock API to return malformed JSON for all requests
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": "invalid-json-text"}]}}]}
        mock_post.return_value = mock_resp

        results = translate_chapter(self.book_slug, self.chapter, provider="gemini-api")
        self.assertEqual(len(results["failed"]), 1)
        self.assertIn("Unrecoverable translation failure", results["failed"][0]["error"])

    @patch("src.pipeline.translate.translate_runner.requests.post")
    @patch("src.pipeline.translate.translate_runner.get_config")
    @patch("src.pipeline.translate.translate_runner.get_prep_dir")
    @patch("src.pipeline.translate.translate_runner.get_translated_dir")
    @patch("src.pipeline.translate.translate_runner.get_reviews_dir")
    @patch("src.pipeline.translate.translate_runner.get_book_root")
    def test_missing_translation_item_id(self, mock_book_root, mock_reviews_dir, mock_trans_dir, mock_prep_dir, mock_get_config, mock_post):
        mock_book_root.return_value = self.book_root
        mock_reviews_dir.return_value = self.reviews_dir
        mock_trans_dir.return_value = self.translated_dir
        mock_prep_dir.return_value = self.prep_dir
        
        mock_get_config.side_effect = lambda key, default=None: "api-key" if key == "GEMINI_API_KEY" else default

        # Return JSON with missing item id (e.g. returns item-99 instead of item-0)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        bad_json = json.dumps([{"id": "item-99", "translated_html": "Mangled"}])
        mock_resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": bad_json}]}}]}
        mock_post.return_value = mock_resp

        results = translate_chapter(self.book_slug, self.chapter, provider="gemini-api")
        self.assertEqual(len(results["failed"]), 1)
        self.assertIn("ID mismatch", results["failed"][0]["error"])

    @patch("src.pipeline.translate.translate_runner.requests.post")
    @patch("src.pipeline.translate.translate_runner.get_config")
    @patch("src.pipeline.translate.translate_runner.get_prep_dir")
    @patch("src.pipeline.translate.translate_runner.get_translated_dir")
    @patch("src.pipeline.translate.translate_runner.get_reviews_dir")
    @patch("src.pipeline.translate.translate_runner.get_book_root")
    def test_batch_fallback_success(self, mock_book_root, mock_reviews_dir, mock_trans_dir, mock_prep_dir, mock_get_config, mock_post):
        mock_book_root.return_value = self.book_root
        mock_reviews_dir.return_value = self.reviews_dir
        mock_trans_dir.return_value = self.translated_dir
        mock_prep_dir.return_value = self.prep_dir
        
        mock_get_config.side_effect = lambda key, default=None: "api-key" if key == "GEMINI_API_KEY" else default

        # First request (batch of 2 items) fails by returning invalid JSON
        # Subsequent requests (fallback individual items) succeed
        mock_resp_fail = MagicMock()
        mock_resp_fail.status_code = 200
        mock_resp_fail.json.return_value = {"candidates": [{"content": {"parts": [{"text": "malformed"}]}}]}

        mock_resp_success_0 = MagicMock()
        mock_resp_success_0.status_code = 200
        success_json_0 = json.dumps([{"id": "item-0", "translated_html": "Xác suất là quan trọng."}])
        mock_resp_success_0.json.return_value = {"candidates": [{"content": {"parts": [{"text": success_json_0}]}}]}

        mock_resp_success_1 = MagicMock()
        mock_resp_success_1.status_code = 200
        success_json_1 = json.dumps([{"id": "item-1", "translated_html": "Công thức [[PROTECTED_TAG_0]] ở đây."}])
        mock_resp_success_1.json.return_value = {"candidates": [{"content": {"parts": [{"text": success_json_1}]}}]}

        mock_post.side_effect = [mock_resp_fail, mock_resp_success_0, mock_resp_success_1]

        results = translate_chapter(self.book_slug, self.chapter, provider="gemini-api")
        self.assertEqual(len(results["processed"]), 1)
        self.assertEqual(results["processed"][0]["fallbacks"], 1) # Fallback was triggered once
        self.assertEqual(len(results["failed"]), 0)

        # Check output
        out_file = self.translated_dir / "1-1-intro.html"
        self.assertTrue(out_file.is_file())
        with open(out_file, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
            
        p1_vn = soup.find("p", id="fs-1-vn")
        self.assertEqual(p1_vn.text, "Xác suất là quan trọng.")
        p2_vn = soup.find("p", id="fs-2-vn")
        self.assertIn("Công thức", p2_vn.text)
        # MathML tag must be preserved
        self.assertIsNotNone(p2_vn.find("math"))

    @patch("src.pipeline.translate.translate_runner.requests.post")
    @patch("src.pipeline.translate.translate_runner.get_config")
    @patch("src.pipeline.translate.translate_runner.get_prep_dir")
    @patch("src.pipeline.translate.translate_runner.get_translated_dir")
    @patch("src.pipeline.translate.translate_runner.get_reviews_dir")
    @patch("src.pipeline.translate.translate_runner.get_book_root")
    def test_block_protection_and_html_preservation(self, mock_book_root, mock_reviews_dir, mock_trans_dir, mock_prep_dir, mock_get_config, mock_post):
        mock_book_root.return_value = self.book_root
        mock_reviews_dir.return_value = self.reviews_dir
        mock_trans_dir.return_value = self.translated_dir
        mock_prep_dir.return_value = self.prep_dir
        
        mock_get_config.side_effect = lambda key, default=None: "api-key" if key == "GEMINI_API_KEY" else default

        # Batch succeeds
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        success_json = json.dumps([
            {"id": "item-0", "translated_html": "Xác suất là quan trọng."},
            {"id": "item-1", "translated_html": "Công thức [[PROTECTED_TAG_0]] ở đây."}
        ])
        mock_resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": success_json}]}}]}
        mock_post.return_value = mock_resp

        results = translate_chapter(self.book_slug, self.chapter, provider="gemini-api")
        self.assertEqual(len(results["failed"]), 0)
        self.assertEqual(len(results["processed"]), 1)

        out_file = self.translated_dir / "1-1-intro.html"
        with open(out_file, "r", encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")
        
        # eng hidden blocks must be UNCHANGED
        p1_eng = soup.find("p", id="fs-1")
        self.assertEqual(p1_eng.text, "Probability is important.")
        self.assertIn("eng", p1_eng["class"])
        self.assertIn("hidden", p1_eng["class"])

        # vn visible block must be changed only
        p1_vn = soup.find("p", id="fs-1-vn")
        self.assertEqual(p1_vn.text, "Xác suất là quan trọng.")
        self.assertIn("vn", p1_vn["class"])
        self.assertIn("visible", p1_vn["class"])

        # MathML / formula preservation
        p2_vn = soup.find("p", id="fs-2-vn")
        math_tag = p2_vn.find("math")
        self.assertIsNotNone(math_tag)
        self.assertEqual(math_tag.find("mfrac").text, "12") # <mfrac><mn>1</mn><mn>2</mn></mfrac> text is 12

    @patch("src.pipeline.translate.translate_runner.get_config")
    @patch("src.pipeline.translate.translate_runner.get_prep_dir")
    @patch("src.pipeline.translate.translate_runner.get_translated_dir")
    @patch("src.pipeline.translate.translate_runner.get_reviews_dir")
    @patch("src.pipeline.translate.translate_runner.get_book_root")
    def test_no_overwrite_without_force(self, mock_book_root, mock_reviews_dir, mock_trans_dir, mock_prep_dir, mock_get_config):
        mock_book_root.return_value = self.book_root
        mock_reviews_dir.return_value = self.reviews_dir
        mock_trans_dir.return_value = self.translated_dir
        mock_prep_dir.return_value = self.prep_dir
        
        mock_get_config.side_effect = lambda key, default=None: "api-key" if key == "GEMINI_API_KEY" else default

        # Pre-create target output file
        out_file = self.translated_dir / "1-1-intro.html"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("pre-existing-content")

        # Run without force or resume
        results = translate_chapter(self.book_slug, self.chapter, provider="gemini-api")
        self.assertEqual(len(results["failed"]), 1)
        self.assertIn("Output file already exists", results["failed"][0]["error"])

        # Verify target file was not modified
        with open(out_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "pre-existing-content")

    @patch("src.pipeline.translate.translate_runner.get_config")
    @patch("src.pipeline.translate.translate_runner.get_prep_dir")
    @patch("src.pipeline.translate.translate_runner.get_translated_dir")
    @patch("src.pipeline.translate.translate_runner.get_reviews_dir")
    @patch("src.pipeline.translate.translate_runner.get_book_root")
    def test_resume_mode_skips_completed(self, mock_book_root, mock_reviews_dir, mock_trans_dir, mock_prep_dir, mock_get_config):
        mock_book_root.return_value = self.book_root
        mock_reviews_dir.return_value = self.reviews_dir
        mock_trans_dir.return_value = self.translated_dir
        mock_prep_dir.return_value = self.prep_dir
        
        mock_get_config.side_effect = lambda key, default=None: "api-key" if key == "GEMINI_API_KEY" else default

        out_file = self.translated_dir / "1-1-intro.html"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("pre-existing-content")

        # Run with resume
        results = translate_chapter(self.book_slug, self.chapter, resume=True, provider="gemini-api")
        self.assertEqual(len(results["skipped"]), 1)
        self.assertEqual(results["skipped"][0]["file"], "1-1-intro.html")
        self.assertEqual(len(results["failed"]), 0)

        # Verify target file was not modified
        with open(out_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "pre-existing-content")

if __name__ == "__main__":
    unittest.main()
