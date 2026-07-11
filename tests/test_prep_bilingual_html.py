import unittest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

# Import paths & prep code
from src.pipeline.prep.prep_bilingual_html import prep_chapter, prep_file

class TestPrepBilingualHtml(unittest.TestCase):
    def setUp(self):
        # Create a temp directory for mock book data
        self.test_dir = Path(tempfile.mkdtemp())
        self.book_slug = "test-prep-book"
        self.chapter = "1"

        # Construct books paths inside temp directory
        self.book_root = self.test_dir / self.book_slug
        self.chapter_root = self.book_root / f"chapter-{self.chapter}"
        self.clean_dir = self.chapter_root / "02-clean"
        self.prep_dir = self.chapter_root / "04-prep"

        # Create dirs
        self.clean_dir.mkdir(parents=True, exist_ok=True)
        self.prep_dir.mkdir(parents=True, exist_ok=True)

        # Create a sample clean HTML file
        self.sample_html = (
            "<html>\n"
            "<head><title>Test Clean Page</title></head>\n"
            "<body>\n"
            "  <div class=\"container\">\n"
            "    <h1 id=\"title-1\">Main Title</h1>\n"
            "    <p id=\"para-1\" class=\"intro\">Entrepreneurs identify opportunities.</p>\n"
            "    <p>No ID block text.</p>\n"
            "    <ul>\n"
            "      <li id=\"item-1\">Bullet point item</li>\n"
            "    </ul>\n"
            "  </div>\n"
            "</body>\n"
            "</html>\n"
        )
        self.clean_file = self.clean_dir / "01-introduction.html"
        with open(self.clean_file, "w", encoding="utf-8") as f:
            f.write(self.sample_html)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch("src.pipeline.prep.prep_bilingual_html.get_clean_dir")
    @patch("src.pipeline.prep.prep_bilingual_html.get_prep_dir")
    def test_prep_bilingual_duplication(self, mock_get_prep_dir, mock_get_clean_dir):
        mock_get_clean_dir.return_value = self.clean_dir
        mock_get_prep_dir.return_value = self.prep_dir

        # Run prep
        results = prep_chapter(self.book_slug, self.chapter, force=False)
        self.assertEqual(len(results["processed"]), 1)
        self.assertEqual(len(results["skipped"]), 0)
        self.assertEqual(len(results["failed"]), 0)

        # Verify output exists
        prep_file_path = self.prep_dir / "01-introduction.html"
        self.assertTrue(prep_file_path.is_file())

        # Verify source file is unchanged
        with open(self.clean_file, "r", encoding="utf-8") as f:
            source_content = f.read()
            self.assertEqual(source_content, self.sample_html)

        # Verify target HTML outputs
        with open(prep_file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # Verify style.css link and absence of book-reader.css
        links = soup.find_all("link", rel="stylesheet")
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["href"], "../../css/style.css")
        self.assertNotIn("book-reader.css", str(soup))

        # Verify style tag injected in head
        style_tag = soup.find("head").find("style")
        self.assertIsNotNone(style_tag)
        self.assertIn(".eng.hidden", style_tag.string)

        # Verify original block has class eng hidden
        p1 = soup.find("p", id="para-1")
        self.assertIsNotNone(p1)
        self.assertIn("eng", p1["class"])
        self.assertIn("hidden", p1["class"])
        self.assertIn("intro", p1["class"])

        # Verify cloned block exists with id suffix -vn and class vn visible
        p1_vn = soup.find("p", id="para-1-vn")
        self.assertIsNotNone(p1_vn)
        self.assertIn("vn", p1_vn["class"])
        self.assertIn("visible", p1_vn["class"])
        self.assertIn("intro", p1_vn["class"])
        self.assertNotIn("eng", p1_vn["class"])
        self.assertNotIn("hidden", p1_vn["class"])
        self.assertEqual(p1_vn.text, "Entrepreneurs identify opportunities.")

        # Check th / td / li are prepped
        li_orig = soup.find("li", id="item-1")
        li_clone = soup.find("li", id="item-1-vn")
        self.assertIsNotNone(li_orig)
        self.assertIsNotNone(li_clone)
        self.assertIn("eng", li_orig["class"])
        self.assertIn("vn", li_clone["class"])

        # Check element without id receives prefix/cloning
        non_id_paras = soup.find_all("p")
        # Should be 4 paragraphs now (2 original, 2 cloned)
        self.assertEqual(len(non_id_paras), 4)

    @patch("src.pipeline.prep.prep_bilingual_html.get_clean_dir")
    @patch("src.pipeline.prep.prep_bilingual_html.get_prep_dir")
    def test_prep_overwrite_protection(self, mock_get_prep_dir, mock_get_clean_dir):
        mock_get_clean_dir.return_value = self.clean_dir
        mock_get_prep_dir.return_value = self.prep_dir

        # Pre-create output prep file with custom content
        prep_file_path = self.prep_dir / "01-introduction.html"
        with open(prep_file_path, "w", encoding="utf-8") as f:
            f.write("custom-prep-content")

        # Run without force
        results = prep_chapter(self.book_slug, self.chapter, force=False)
        self.assertEqual(len(results["processed"]), 0)
        self.assertEqual(len(results["skipped"]), 1)
        self.assertEqual(results["skipped"][0], "01-introduction.html")

        # Verify content remained unchanged
        with open(prep_file_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "custom-prep-content")

        # Run with force
        results = prep_chapter(self.book_slug, self.chapter, force=True)
        self.assertEqual(len(results["processed"]), 1)
        self.assertEqual(len(results["skipped"]), 0)

        # Verify content got overwritten with prepped html
        with open(prep_file_path, "r", encoding="utf-8") as f:
            self.assertIn("eng hidden", f.read())

if __name__ == "__main__":
    unittest.main()
