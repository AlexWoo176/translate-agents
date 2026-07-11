import unittest
import tempfile
import shutil
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.pipeline.archive.archive_chapter import archive_chapter

class TestArchiveChapter(unittest.TestCase):
    def setUp(self):
        # Create temporary folders structure
        self.test_dir = Path(tempfile.mkdtemp())
        self.book_slug = "test-archive-book"
        self.chapter = "1"

        self.book_root = self.test_dir / self.book_slug
        self.chapter_root = self.book_root / f"chapter-{self.chapter}"
        self.translated_dir = self.chapter_root / "05-translated"
        self.archive_dir = self.chapter_root / "07-archive"

        self.translated_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # Standard HTML files in translated
        self.html_content = (
            "<html>\n"
            "<head><title>Bilingual Page</title>\n"
            "<style>.eng.hidden { display:none; } .vn.visible { color:#000; }</style></head>\n"
            "<body>\n"
            "  <p class=\"eng hidden\" id=\"p1\">English text</p>\n"
            "  <p class=\"vn visible\" id=\"p1-vn\">Vietnamese text</p>\n"
            "</body>\n"
            "</html>"
        )
        self.html_file = self.translated_dir / "01-intro.html"
        with open(self.html_file, "w", encoding="utf-8") as f:
            f.write(self.html_content)

        # Create chapter.json (QA gate failed/pending by default)
        self.chapter_json = self.chapter_root / "chapter.json"
        with open(self.chapter_json, "w", encoding="utf-8") as f:
            json.dump({
                "book": self.book_slug,
                "chapter": 1,
                "qa": {"review_gate": "failed"},
                "phases": {"translate": {"status": "completed"}}
            }, f)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch("src.pipeline.archive.archive_chapter.get_chapter_root")
    @patch("src.pipeline.archive.archive_chapter.get_translated_dir")
    @patch("src.exporters.export_chapter.get_archive_dir")
    def test_archive_blocked_by_qa_gate(self, mock_get_archive_dir, mock_get_trans, mock_get_chap):
        mock_get_chap.return_value = self.chapter_root
        mock_get_trans.return_value = self.translated_dir
        # Mock archive dirs
        mock_get_archive_dir.side_effect = lambda b, c, m, f: self.archive_dir / m / f

        # Run without force -> should be blocked, return exit code 1
        exit_code, msg = archive_chapter(self.book_slug, self.chapter, force=False)
        self.assertEqual(exit_code, 1)
        self.assertIn("QA review gate is not passed", msg)

        # Check that no files were archived
        self.assertFalse((self.archive_dir / "bilingual").exists())

    @patch("src.pipeline.archive.archive_chapter.get_chapter_root")
    @patch("src.pipeline.archive.archive_chapter.get_translated_dir")
    @patch("src.exporters.export_chapter.get_archive_dir")
    def test_archive_with_force_override(self, mock_get_archive_dir, mock_get_trans, mock_get_chap):
        mock_get_chap.return_value = self.chapter_root
        mock_get_trans.return_value = self.translated_dir
        mock_get_archive_dir.side_effect = lambda b, c, m, f: self.archive_dir / m / f

        # Run with force -> should proceed, exit code 0
        exit_code, result = archive_chapter(self.book_slug, self.chapter, force=True)
        self.assertEqual(exit_code, 0)
        self.assertTrue(result["review_gate_forced"])

        # Check folder structure created
        self.assertTrue((self.archive_dir / "bilingual" / "html").is_dir())
        self.assertTrue((self.archive_dir / "bilingual" / "md").is_dir())
        self.assertTrue((self.archive_dir / "vn-only" / "html").is_dir())
        self.assertTrue((self.archive_dir / "vn-only" / "md").is_dir())

        # Check bilingual HTML retains both English and Vietnamese blocks
        bil_html = self.archive_dir / "bilingual" / "html" / "01-intro.html"
        self.assertTrue(bil_html.is_file())
        with open(bil_html, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("English text", content)
            self.assertIn("Vietnamese text", content)

        # Check vn-only HTML removes English blocks and debug styles
        vn_html = self.archive_dir / "vn-only" / "html" / "01-intro.html"
        self.assertTrue(vn_html.is_file())
        with open(vn_html, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertNotIn("English text", content)
            self.assertIn("Vietnamese text", content)
            self.assertNotIn(".eng.hidden", content)

        # Check markdown files generated
        bil_md = self.archive_dir / "bilingual" / "md" / "01-intro.md"
        self.assertTrue(bil_md.is_file())
        with open(bil_md, "r", encoding="utf-8") as f:
            self.assertIn("English text", f.read())

        # Check chapter.json updated correctly
        with open(self.chapter_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertTrue(data["qa"]["review_gate_forced"])
            self.assertTrue(data["archive"]["bilingual"]["html"])
            self.assertTrue(data["archive"]["vn-only"]["html"])

    @patch("src.pipeline.archive.archive_chapter.get_chapter_root")
    @patch("src.pipeline.archive.archive_chapter.get_translated_dir")
    @patch("src.exporters.export_chapter.get_archive_dir")
    def test_archive_passed_qa_gate(self, mock_get_archive_dir, mock_get_trans, mock_get_chap):
        mock_get_chap.return_value = self.chapter_root
        mock_get_trans.return_value = self.translated_dir
        mock_get_archive_dir.side_effect = lambda b, c, m, f: self.archive_dir / m / f

        # Mark QA gate as passed
        with open(self.chapter_json, "w", encoding="utf-8") as f:
            json.dump({
                "book": self.book_slug,
                "chapter": 1,
                "qa": {"review_gate": "passed"},
                "phases": {"translate": {"status": "completed"}}
            }, f)

        # Run without force -> should pass, exit code 0
        exit_code, result = archive_chapter(self.book_slug, self.chapter, force=False)
        self.assertEqual(exit_code, 0)
        self.assertFalse(result["review_gate_forced"])

    def test_normalize_archive_resources(self):
        from bs4 import BeautifulSoup
        from src.exporters.html_exporter import normalize_archive_resources

        # 1. Test standard stylesheet rewrite and book-reader.css removal
        html = (
            "<html>\n"
            "<head>\n"
            "  <link rel=\"stylesheet\" href=\"book-reader/book-reader.css\">\n"
            "  <link rel=\"stylesheet\" href=\"../../../css/style.css\">\n"
            "</head>\n"
            "<body>\n"
            "  <img src=\"../assets/foo.webp\">\n"
            "</body>\n"
            "</html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        normalize_archive_resources(soup)

        # Assertions
        links = soup.find_all("link", rel="stylesheet")
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["href"], "../../../../css/style.css")
        self.assertNotIn("book-reader.css", str(soup))

        img = soup.find("img")
        self.assertEqual(img["src"], "../../../assets/foo.webp")

        # 2. Test idempotency (running twice does not change links or paths)
        normalize_archive_resources(soup)
        links2 = soup.find_all("link", rel="stylesheet")
        self.assertEqual(len(links2), 1)
        self.assertEqual(links2[0]["href"], "../../../../css/style.css")
        img2 = soup.find("img")
        self.assertEqual(img2["src"], "../../../assets/foo.webp")

if __name__ == "__main__":
    unittest.main()
