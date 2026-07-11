import unittest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch

from src.pipeline.build.build_preview import build_preview, inject_reader_scripts


class TestBuildPreview(unittest.TestCase):
    def setUp(self):
        # Create temp folder structure
        self.test_dir = Path(tempfile.mkdtemp())
        self.book_slug = "test-build-book"

        self.book_root = self.test_dir / self.book_slug
        self.web_output_root = self.test_dir / "web-site"

        self.book_root.mkdir(parents=True, exist_ok=True)
        self.web_output_root.mkdir(parents=True, exist_ok=True)

        # Create mock archived HTML files
        # chapter-1/07-archive/bilingual/html/
        self.chap1_archive = self.book_root / "chapter-1" / "07-archive" / "bilingual" / "html"
        self.chap1_archive.mkdir(parents=True, exist_ok=True)

        self.html_content = (
            "<html>\n"
            "<head><title>Chapter 1 Introduction</title></head>\n"
            "<body><p>Welcome to Chapter 1.</p></body>\n"
            "</html>"
        )
        with open(self.chap1_archive / "01-introduction.html", "w", encoding="utf-8") as f:
            f.write(self.html_content)

        # Create mock style.css
        self.css_dir = self.book_root / "css"
        self.css_dir.mkdir(parents=True, exist_ok=True)
        with open(self.css_dir / "style.css", "w", encoding="utf-8") as f:
            f.write("body { margin: 0; }")

        # Create mock glossary
        with open(self.book_root / "glossary.csv", "w", encoding="utf-8") as f:
            f.write("term,translation,context,status,notes\nentrepreneur,nhà khởi nghiệp,,approved,")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch("src.pipeline.build.build_preview.get_book_root")
    @patch("src.pipeline.build.build_preview.get_web_output_root")
    @patch("src.pipeline.build.build_preview.get_archive_dir")
    def test_build_preview_workflow(self, mock_get_archive_dir, mock_get_web_output_root, mock_get_book_root):
        mock_get_book_root.return_value = self.book_root
        mock_get_web_output_root.return_value = self.web_output_root
        mock_get_archive_dir.side_effect = lambda b, c, m, f: self.book_root / (c if c.startswith("chapter-") else f"chapter-{c}") / "07-archive" / m / f

        # Run preview build
        exit_code, result = build_preview(self.book_slug, mode="bilingual", copy_to_web=False)
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["total_pages"], 1)

        # Verify output directory .html exists under book root
        output_html_dir = self.book_root / ".html"
        self.assertTrue(output_html_dir.is_dir())

        # Verify reader css, style css and js copied
        self.assertTrue((output_html_dir / "book-reader" / "book-reader.js").is_file())
        self.assertTrue((output_html_dir / "book-reader" / "book-reader.css").is_file())
        self.assertTrue((output_html_dir / "css" / "style.css").is_file())

        # Verify page manifest generated
        pages_js_path = output_html_dir / "book-reader" / "book-pages.js"
        self.assertTrue(pages_js_path.is_file())
        with open(pages_js_path, "r", encoding="utf-8") as f:
            self.assertIn("['/chapter-1/01-introduction.html']", f.read())

        # Verify redirect index.html created
        index_path = output_html_dir / "index.html"
        self.assertTrue(index_path.is_file())
        with open(index_path, "r", encoding="utf-8") as f:
            self.assertIn("/chapter-1/01-introduction.html", f.read())

        # Verify copied HTML file contains reader script injections, style.css link, and body class
        copied_html_path = output_html_dir / "chapter-1" / "01-introduction.html"
        self.assertTrue(copied_html_path.is_file())
        with open(copied_html_path, "r", encoding="utf-8") as f:
            html_text = f.read()
            self.assertIn('<script src="../book-reader/book-pages.js"></script>', html_text)
            self.assertIn('<link rel="stylesheet" href="../book-reader/book-reader.css">', html_text)
            self.assertIn('<script src="../book-reader/book-reader.js"></script>', html_text)
            self.assertIn('<link rel="stylesheet" href="../css/style.css">', html_text)
            self.assertIn('class="book-reader"', html_text)

        # Verify original archive HTML file does NOT include book-reader.css
        with open(self.chap1_archive / "01-introduction.html", "r", encoding="utf-8") as f:
            archive_text = f.read()
            self.assertNotIn('book-reader.css', archive_text)

        # Verify book-reader.css has no raw unscoped "body {" global selector
        reader_css_path = output_html_dir / "book-reader" / "book-reader.css"
        self.assertTrue(reader_css_path.is_file())
        with open(reader_css_path, "r", encoding="utf-8") as f:
            css_text = f.read()
            self.assertNotIn("\nbody {", css_text)
            self.assertFalse(css_text.startswith("body {"))
            self.assertIn("body.book-reader {", css_text)
            self.assertIn("body.book-reader.lang-swap #br-main-content td.eng.hidden", css_text)
            self.assertIn("body.book-reader:not(.lang-swap) #br-main-content td.vn.visible", css_text)
            self.assertIn("#br-eng-content td.eng.hidden", css_text)

        # Verify no files written to web_output_root since copy_to_web=False
        self.assertFalse((self.web_output_root / self.book_slug).exists())

    @patch("src.pipeline.build.build_preview.get_book_root")
    @patch("src.pipeline.build.build_preview.get_web_output_root")
    @patch("src.pipeline.build.build_preview.get_archive_dir")
    def test_build_preview_copy_to_web(self, mock_get_archive_dir, mock_get_web_output_root, mock_get_book_root):
        mock_get_book_root.return_value = self.book_root
        mock_get_web_output_root.return_value = self.web_output_root
        mock_get_archive_dir.side_effect = lambda b, c, m, f: self.book_root / (c if c.startswith("chapter-") else f"chapter-{c}") / "07-archive" / m / f

        # Run preview build with copy_to_web=True
        exit_code, result = build_preview(self.book_slug, mode="bilingual", copy_to_web=True)
        self.assertEqual(exit_code, 0)

        # Verify files copied to web site output location
        web_book_dir = self.web_output_root / self.book_slug
        self.assertTrue(web_book_dir.is_dir())
        self.assertTrue((web_book_dir / "index.html").is_file())
        self.assertTrue((web_book_dir / "book-reader" / "book-pages.js").is_file())
        self.assertTrue((web_book_dir / "chapter-1" / "01-introduction.html").is_file())


class TestInjectReaderScriptsImagePaths(unittest.TestCase):
    """
    Unit tests for image path normalization in inject_reader_scripts.
    Covers Part F requirements: all depth variants, idempotency, srcset,
    CSS normalization.
    """

    def _make_html(self, img_src):
        """Create minimal HTML with an img tag using the given src."""
        return (
            f'<html><head><link href="../../../../css/style.css" rel="stylesheet"/></head>'
            f'<body><img src="{img_src}" alt="fig"/></body></html>'
        )

    def _make_html_srcset(self, srcset_val):
        """Create minimal HTML with an img tag using the given srcset."""
        return (
            f'<html><head><title>T</title></head>'
            f'<body><img srcset="{srcset_val}" alt="fig"/></body></html>'
        )

    # ------------------------------------------------------------------
    # Part F Test 2: ../../../assets/foo.webp -> assets/foo.webp
    # ------------------------------------------------------------------
    def test_three_dots_normalized(self):
        html = self._make_html("../../../assets/img-1-1-1.webp")
        result = inject_reader_scripts(html)
        self.assertIn('src="assets/img-1-1-1.webp"', result)
        self.assertNotIn("../../../assets/", result)

    # ------------------------------------------------------------------
    # Part F Test 3: ../assets/foo.webp -> assets/foo.webp
    # ------------------------------------------------------------------
    def test_one_dot_normalized(self):
        html = self._make_html("../assets/img-1-1-1.webp")
        result = inject_reader_scripts(html)
        self.assertIn('src="assets/img-1-1-1.webp"', result)
        self.assertNotIn("../assets/", result)

    # Additional depth: ../../assets/foo.webp -> assets/foo.webp
    def test_two_dots_normalized(self):
        html = self._make_html("../../assets/img-1-1-1.webp")
        result = inject_reader_scripts(html)
        self.assertIn('src="assets/img-1-1-1.webp"', result)
        self.assertNotIn("../../assets/", result)

    # ------------------------------------------------------------------
    # Part F Test 4: assets/foo.webp left unchanged
    # ------------------------------------------------------------------
    def test_bare_assets_unchanged(self):
        html = self._make_html("assets/img-1-1-1.webp")
        result = inject_reader_scripts(html)
        self.assertIn('src="assets/img-1-1-1.webp"', result)

    # ------------------------------------------------------------------
    # Part F Test 5: idempotency - running twice must not produce assets/assets/
    # ------------------------------------------------------------------
    def test_idempotent_no_double_assets(self):
        html = self._make_html("../../../assets/img-1-1-1.webp")
        result1 = inject_reader_scripts(html)
        result2 = inject_reader_scripts(result1)
        self.assertIn('src="assets/img-1-1-1.webp"', result2)
        self.assertNotIn("assets/assets/", result2)

    # ------------------------------------------------------------------
    # Part F Test 6: no invalid relative paths remain in output
    # ------------------------------------------------------------------
    def test_no_relative_assets_in_output(self):
        for depth in ["../assets/img.webp", "../../assets/img.webp", "../../../assets/img.webp"]:
            html = self._make_html(depth)
            result = inject_reader_scripts(html)
            self.assertNotIn("../assets/", result, f"Failed for: {depth}")
            self.assertNotIn("../../assets/", result, f"Failed for: {depth}")
            self.assertNotIn("../../../assets/", result, f"Failed for: {depth}")

    # ------------------------------------------------------------------
    # Part F Test 7: output contains src="assets/foo.webp"
    # ------------------------------------------------------------------
    def test_output_contains_bare_assets_src(self):
        html = self._make_html("../../../assets/img-1-1-1.webp")
        result = inject_reader_scripts(html)
        self.assertIn('src="assets/img-1-1-1.webp"', result)

    # ------------------------------------------------------------------
    # srcset normalization (responsive images)
    # ------------------------------------------------------------------
    def test_srcset_double_quote_normalized(self):
        html = self._make_html_srcset("../../../assets/img.webp 1x, ../../../assets/img@2x.webp 2x")
        result = inject_reader_scripts(html)
        self.assertNotIn("../../../assets/", result)

    def test_srcset_single_dot_normalized(self):
        html = self._make_html_srcset("../assets/img.webp 480w")
        result = inject_reader_scripts(html)
        self.assertNotIn("../assets/", result)

    # ------------------------------------------------------------------
    # Subdirectory within assets preserved
    # ------------------------------------------------------------------
    def test_subdirectory_in_assets_preserved(self):
        html = self._make_html("../../../assets/figures/img-1-1-1.webp")
        result = inject_reader_scripts(html)
        self.assertIn('src="assets/figures/img-1-1-1.webp"', result)

    # ------------------------------------------------------------------
    # Part F Test 11: CSS links still present after normalization
    # ------------------------------------------------------------------
    def test_css_links_present_in_output(self):
        html = '<html><head><link href="../../../../css/style.css" rel="stylesheet"/></head><body></body></html>'
        result = inject_reader_scripts(html)
        self.assertIn('../css/style.css', result)
        self.assertIn("book-reader.css", result)

    def test_archive_css_path_normalized_for_preview(self):
        """archive HTML using ../../../../css/style.css normalized to ../css/style.css for preview."""
        html = '<html><head><link href="../../../../css/style.css" rel="stylesheet"/></head><body></body></html>'
        result = inject_reader_scripts(html)
        self.assertIn('../css/style.css', result)
        self.assertNotIn('../../../../css/style.css', result)


class TestBuildPreviewAssetsCopy(unittest.TestCase):
    """
    Integration-style tests verifying that chapter assets are copied to
    .html/chapter-N/assets/ and web-site/chapter-N/assets/ (Part F Tests 1, 8, 9, 10).
    """

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.book_slug = "test-asset-book"
        self.book_root = self.test_dir / self.book_slug
        self.web_output_root = self.test_dir / "web-site"
        self.book_root.mkdir(parents=True, exist_ok=True)
        self.web_output_root.mkdir(parents=True, exist_ok=True)

        # Archive HTML with archive-depth image path (../../../assets/img.webp)
        self.chap1_archive = self.book_root / "chapter-1" / "07-archive" / "bilingual" / "html"
        self.chap1_archive.mkdir(parents=True, exist_ok=True)
        html_with_img = (
            '<html><head><link href="../../../../css/style.css" rel="stylesheet"/></head>'
            '<body><img src="../../../assets/img-1-1-1.webp" alt="fig"/></body></html>'
        )
        with open(self.chap1_archive / "1-1-test.html", "w", encoding="utf-8") as f:
            f.write(html_with_img)

        # Chapter assets
        assets_src = self.book_root / "chapter-1" / "assets"
        assets_src.mkdir(parents=True, exist_ok=True)
        (assets_src / "img-1-1-1.webp").write_bytes(b"FAKE_WEBP")

        # CSS
        css_dir = self.book_root / "css"
        css_dir.mkdir(parents=True, exist_ok=True)
        (css_dir / "style.css").write_text("body{}", encoding="utf-8")

        # Glossary
        with open(self.book_root / "glossary.csv", "w", encoding="utf-8") as f:
            f.write("term,translation,context,status,notes\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch("src.pipeline.build.build_preview.get_book_root")
    @patch("src.pipeline.build.build_preview.get_web_output_root")
    @patch("src.pipeline.build.build_preview.get_archive_dir")
    def test_assets_copied_to_html_output(self, mock_archive, mock_web, mock_book):
        """Part F Test 1: Build preview copies chapter assets to .html/chapter-N/assets/"""
        mock_book.return_value = self.book_root
        mock_web.return_value = self.web_output_root
        mock_archive.side_effect = lambda b, c, m, f: self.book_root / (c if c.startswith("chapter-") else f"chapter-{c}") / "07-archive" / m / f

        exit_code, _ = build_preview(self.book_slug, mode="bilingual", copy_to_web=False)
        self.assertEqual(exit_code, 0)

        # Part F Test 1: assets copied to .html/chapter-N/assets/
        asset_path = self.book_root / ".html" / "chapter-1" / "assets" / "img-1-1-1.webp"
        self.assertTrue(asset_path.is_file(), f"Expected asset at {asset_path}")

        # Part F Tests 6 & 7: HTML output uses src="assets/..." without relative prefixes
        html_out = (self.book_root / ".html" / "chapter-1" / "1-1-test.html").read_text(encoding="utf-8")
        self.assertIn('src="assets/img-1-1-1.webp"', html_out)
        self.assertNotIn("../../../assets/", html_out)
        self.assertNotIn("../../assets/", html_out)
        self.assertNotIn("../assets/", html_out)

    @patch("src.pipeline.build.build_preview.get_book_root")
    @patch("src.pipeline.build.build_preview.get_web_output_root")
    @patch("src.pipeline.build.build_preview.get_archive_dir")
    def test_assets_copied_to_web_site(self, mock_archive, mock_web, mock_book):
        """Part F Tests 8 & 9: web-site contains assets and correct HTML paths."""
        mock_book.return_value = self.book_root
        mock_web.return_value = self.web_output_root
        mock_archive.side_effect = lambda b, c, m, f: self.book_root / (c if c.startswith("chapter-") else f"chapter-{c}") / "07-archive" / m / f

        exit_code, _ = build_preview(self.book_slug, mode="bilingual", copy_to_web=True)
        self.assertEqual(exit_code, 0)

        # Part F Test 8: web-site contains chapter-N/assets/
        web_asset = self.web_output_root / self.book_slug / "chapter-1" / "assets" / "img-1-1-1.webp"
        self.assertTrue(web_asset.is_file(), f"Expected web-site asset at {web_asset}")

        # Part F Test 9: web-site HTML uses src="assets/..."
        web_html = (self.web_output_root / self.book_slug / "chapter-1" / "1-1-test.html").read_text(encoding="utf-8")
        self.assertIn('src="assets/img-1-1-1.webp"', web_html)
        self.assertNotIn("../../../assets/", web_html)

    @patch("src.pipeline.build.build_preview.get_book_root")
    @patch("src.pipeline.build.build_preview.get_web_output_root")
    @patch("src.pipeline.build.build_preview.get_archive_dir")
    def test_archive_html_not_modified(self, mock_archive, mock_web, mock_book):
        """Part F Test 10: archive HTML must still use ../../../assets/ paths."""
        mock_book.return_value = self.book_root
        mock_web.return_value = self.web_output_root
        mock_archive.side_effect = lambda b, c, m, f: self.book_root / (c if c.startswith("chapter-") else f"chapter-{c}") / "07-archive" / m / f

        exit_code, _ = build_preview(self.book_slug, mode="bilingual", copy_to_web=False)
        self.assertEqual(exit_code, 0)

        # Archive source must be untouched
        archive_html = (self.chap1_archive / "1-1-test.html").read_text(encoding="utf-8")
        self.assertIn("../../../assets/img-1-1-1.webp", archive_html,
                      "Archive HTML must preserve ../../../assets/ paths")


if __name__ == "__main__":
    unittest.main()
