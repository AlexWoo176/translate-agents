"""
test_html_resources.py — Regression tests for src/utils/html_resources.py

Covers:
- Stylesheet helpers: ensure, normalize, deduplicate, ensure-no-reader
- Image helpers: archive normalization, preview normalization, srcset, idempotency
- Validation helpers: stylesheet, image links, forbidden CSS, duplicates, src pattern
"""

import tempfile
import shutil
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

from src.utils.html_resources import (
    # Stylesheet helpers
    ensure_stylesheet_link,
    normalize_stylesheet_links,
    remove_duplicate_book_stylesheet_links,
    ensure_no_reader_css,
    # Image helpers
    normalize_archive_image_paths,
    normalize_preview_image_paths,
    normalize_working_image_paths,
    # Validation helpers
    validate_stylesheet_links,
    validate_image_links,
    validate_no_forbidden_css,
    validate_no_duplicate_stylesheets,
    validate_image_src_pattern,
)


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _html_with_img(src: str) -> str:
    return f'<html><head><title>T</title></head><body><img src="{src}" alt="x"/></body></html>'


# ===========================================================================
# Stylesheet Helpers
# ===========================================================================

class TestEnsureStylesheetLink(unittest.TestCase):

    def test_inserts_link_when_missing(self):
        soup = _soup("<html><head><title>X</title></head><body></body></html>")
        ensure_stylesheet_link(soup, "../../css/style.css")
        links = [l["href"] for l in soup.find_all("link", rel="stylesheet") if "style.css" in l.get("href", "")]
        self.assertIn("../../css/style.css", links)

    def test_updates_wrong_href(self):
        soup = _soup('<html><head><link rel="stylesheet" href="../wrong/style.css"></head><body></body></html>')
        ensure_stylesheet_link(soup, "../../css/style.css")
        links = [l["href"] for l in soup.find_all("link", rel="stylesheet") if "style.css" in l.get("href", "")]
        self.assertEqual(links, ["../../css/style.css"])

    def test_correct_href_unchanged(self):
        soup = _soup('<html><head><link rel="stylesheet" href="../../css/style.css"></head><body></body></html>')
        ensure_stylesheet_link(soup, "../../css/style.css")
        links = [l["href"] for l in soup.find_all("link", rel="stylesheet") if "style.css" in l.get("href", "")]
        self.assertEqual(links, ["../../css/style.css"])

    def test_removes_reader_css(self):
        soup = _soup(
            '<html><head>'
            '<link rel="stylesheet" href="../book-reader/book-reader.css">'
            '<link rel="stylesheet" href="../../css/style.css">'
            '</head><body></body></html>'
        )
        ensure_stylesheet_link(soup, "../../css/style.css")
        hrefs = [l["href"] for l in soup.find_all("link", rel="stylesheet")]
        self.assertNotIn("../book-reader/book-reader.css", hrefs)

    def test_idempotent(self):
        soup = _soup("<html><head></head><body></body></html>")
        ensure_stylesheet_link(soup, "../../css/style.css")
        ensure_stylesheet_link(soup, "../../css/style.css")
        style_links = [l for l in soup.find_all("link", rel="stylesheet") if "style.css" in l.get("href", "")]
        self.assertEqual(len(style_links), 1)


class TestNormalizeStylesheetLinks(unittest.TestCase):

    def test_normalizes_and_deduplicates(self):
        soup = _soup(
            '<html><head>'
            '<link rel="stylesheet" href="../../css/style.css">'
            '<link rel="stylesheet" href="../../css/style.css">'
            '</head><body></body></html>'
        )
        normalize_stylesheet_links(soup, "../../../../css/style.css")
        links = [l["href"] for l in soup.find_all("link", rel="stylesheet") if "style.css" in l.get("href", "")]
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0], "../../../../css/style.css")


class TestRemoveDuplicates(unittest.TestCase):

    def test_keeps_first_removes_duplicates(self):
        soup = _soup(
            '<html><head>'
            '<link rel="stylesheet" href="../../css/style.css">'
            '<link rel="stylesheet" href="../../css/style.css">'
            '<link rel="stylesheet" href="../../css/style.css">'
            '</head><body></body></html>'
        )
        remove_duplicate_book_stylesheet_links(soup)
        links = [l for l in soup.find_all("link", rel="stylesheet") if "style.css" in l.get("href", "")]
        self.assertEqual(len(links), 1)

    def test_preserves_non_style_links(self):
        soup = _soup(
            '<html><head>'
            '<link rel="stylesheet" href="other.css">'
            '<link rel="stylesheet" href="../../css/style.css">'
            '</head><body></body></html>'
        )
        remove_duplicate_book_stylesheet_links(soup)
        hrefs = [l["href"] for l in soup.find_all("link", rel="stylesheet")]
        self.assertIn("other.css", hrefs)
        self.assertIn("../../css/style.css", hrefs)


class TestEnsureNoReaderCss(unittest.TestCase):

    def test_removes_reader_css(self):
        soup = _soup(
            '<html><head>'
            '<link rel="stylesheet" href="../book-reader/book-reader.css">'
            '<link rel="stylesheet" href="../../css/style.css">'
            '</head><body></body></html>'
        )
        ensure_no_reader_css(soup)
        hrefs = [l["href"] for l in soup.find_all("link", rel="stylesheet")]
        self.assertNotIn("../book-reader/book-reader.css", hrefs)
        self.assertIn("../../css/style.css", hrefs)

    def test_idempotent_when_no_reader_css(self):
        soup = _soup('<html><head><link rel="stylesheet" href="../../css/style.css"></head><body></body></html>')
        ensure_no_reader_css(soup)
        ensure_no_reader_css(soup)
        links = soup.find_all("link", rel="stylesheet")
        self.assertEqual(len(links), 1)


# ===========================================================================
# Image Path Helpers
# ===========================================================================

class TestNormalizeArchiveImagePaths(unittest.TestCase):

    def test_bare_assets_to_archive_depth(self):
        soup = _soup(_html_with_img("assets/img.webp"))
        normalize_archive_image_paths(soup)
        self.assertEqual(soup.find("img")["src"], "../../../assets/img.webp")

    def test_working_depth_to_archive_depth(self):
        soup = _soup(_html_with_img("../assets/img.webp"))
        normalize_archive_image_paths(soup)
        self.assertEqual(soup.find("img")["src"], "../../../assets/img.webp")

    def test_already_archive_depth_unchanged(self):
        soup = _soup(_html_with_img("../../../assets/img.webp"))
        normalize_archive_image_paths(soup)
        self.assertEqual(soup.find("img")["src"], "../../../assets/img.webp")

    def test_idempotent(self):
        soup = _soup(_html_with_img("../assets/img.webp"))
        normalize_archive_image_paths(soup)
        normalize_archive_image_paths(soup)
        self.assertEqual(soup.find("img")["src"], "../../../assets/img.webp")

    def test_non_assets_src_unchanged(self):
        soup = _soup(_html_with_img("https://example.com/img.jpg"))
        normalize_archive_image_paths(soup)
        self.assertEqual(soup.find("img")["src"], "https://example.com/img.jpg")


class TestNormalizePreviewImagePaths(unittest.TestCase):

    def test_three_dots_to_bare(self):
        html = _html_with_img("../../../assets/img.webp")
        result = normalize_preview_image_paths(html)
        self.assertIn('src="assets/img.webp"', result)

    def test_two_dots_to_bare(self):
        html = _html_with_img("../../assets/img.webp")
        result = normalize_preview_image_paths(html)
        self.assertIn('src="assets/img.webp"', result)

    def test_one_dot_to_bare(self):
        html = _html_with_img("../assets/img.webp")
        result = normalize_preview_image_paths(html)
        self.assertIn('src="assets/img.webp"', result)

    def test_bare_unchanged(self):
        html = _html_with_img("assets/img.webp")
        result = normalize_preview_image_paths(html)
        self.assertIn('src="assets/img.webp"', result)

    def test_idempotent_no_double_assets(self):
        html = _html_with_img("../../../assets/img.webp")
        result1 = normalize_preview_image_paths(html)
        result2 = normalize_preview_image_paths(result1)
        self.assertNotIn("assets/assets/", result2)
        self.assertIn('src="assets/img.webp"', result2)

    def test_srcset_multi_url_normalized(self):
        html = '<html><body><img srcset="../../../assets/a.webp 1x, ../../../assets/b.webp 2x"/></body></html>'
        result = normalize_preview_image_paths(html)
        self.assertNotIn("../../../assets/", result)

    def test_no_relative_paths_in_output(self):
        for depth in ["../assets/img.webp", "../../assets/img.webp", "../../../assets/img.webp"]:
            html = _html_with_img(depth)
            result = normalize_preview_image_paths(html)
            self.assertNotIn("../assets/", result)
            self.assertNotIn("../../assets/", result)
            self.assertNotIn("../../../assets/", result)

    def test_subdirectory_preserved(self):
        html = _html_with_img("../../../assets/figures/img.webp")
        result = normalize_preview_image_paths(html)
        self.assertIn('src="assets/figures/img.webp"', result)

    def test_external_url_unchanged(self):
        html = _html_with_img("https://cdn.example.com/img.jpg")
        result = normalize_preview_image_paths(html)
        self.assertIn('src="https://cdn.example.com/img.jpg"', result)


class TestNormalizeWorkingImagePaths(unittest.TestCase):

    def test_bare_assets_to_working_depth(self):
        soup = _soup(_html_with_img("assets/img.webp"))
        normalize_working_image_paths(soup)
        self.assertEqual(soup.find("img")["src"], "../assets/img.webp")

    def test_already_working_depth_unchanged(self):
        soup = _soup(_html_with_img("../assets/img.webp"))
        normalize_working_image_paths(soup)
        self.assertEqual(soup.find("img")["src"], "../assets/img.webp")

    def test_idempotent(self):
        soup = _soup(_html_with_img("assets/img.webp"))
        normalize_working_image_paths(soup)
        normalize_working_image_paths(soup)
        self.assertEqual(soup.find("img")["src"], "../assets/img.webp")


# ===========================================================================
# Validation Helpers
# ===========================================================================

class TestValidateStylesheetLinks(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write(self, name, html):
        p = self.tmp / name
        p.write_text(html, encoding="utf-8")
        return p

    def test_passes_correct_working_href(self):
        f = self._write("working.html",
            '<html><head><link rel="stylesheet" href="../../css/style.css"></head><body></body></html>')
        result = validate_stylesheet_links(f, "working")
        self.assertTrue(result["ok"])
        self.assertEqual(result["errors"], [])

    def test_fails_missing_stylesheet(self):
        f = self._write("no_css.html", "<html><head></head><body></body></html>")
        result = validate_stylesheet_links(f, "working")
        self.assertFalse(result["ok"])
        self.assertTrue(any("Missing style.css" in e for e in result["errors"]))
        self.assertTrue(any(str(f) in e for e in result["errors"]))

    def test_fails_wrong_href(self):
        f = self._write("wrong.html",
            '<html><head><link rel="stylesheet" href="../wrong/style.css"></head><body></body></html>')
        result = validate_stylesheet_links(f, "working")
        self.assertFalse(result["ok"])
        self.assertTrue(any("Wrong style.css href" in e for e in result["errors"]))

    def test_passes_archive_href(self):
        f = self._write("archive.html",
            '<html><head><link rel="stylesheet" href="../../../../css/style.css"></head><body></body></html>')
        result = validate_stylesheet_links(f, "archive")
        self.assertTrue(result["ok"])

    def test_raw_stage_always_passes(self):
        f = self._write("raw.html", "<html><head></head><body></body></html>")
        result = validate_stylesheet_links(f, "raw")
        self.assertTrue(result["ok"])

    def test_missing_file_returns_error(self):
        result = validate_stylesheet_links(self.tmp / "nonexistent.html", "working")
        self.assertFalse(result["ok"])


class TestValidateImageLinks(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.assets = self.tmp / "assets"
        self.assets.mkdir()
        (self.assets / "img.webp").write_bytes(b"FAKE")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write(self, name, html):
        p = self.tmp / name
        p.write_text(html, encoding="utf-8")
        return p

    def test_passes_when_image_exists_preview(self):
        f = self._write("preview.html", _html_with_img("assets/img.webp"))
        result = validate_image_links(f, self.assets)
        self.assertTrue(result["ok"])

    def test_fails_when_image_missing_preview(self):
        f = self._write("preview.html", _html_with_img("assets/missing.webp"))
        result = validate_image_links(f, self.assets)
        self.assertFalse(result["ok"])
        self.assertTrue(any("Missing image" in e for e in result["errors"]))
        self.assertTrue(any(str(f) in e for e in result["errors"]))

    def test_passes_when_image_exists_archive(self):
        f = self._write("archive.html", _html_with_img("../../../assets/img.webp"))
        result = validate_image_links(f, self.assets)
        self.assertTrue(result["ok"])

    def test_external_url_not_checked(self):
        f = self._write("ext.html", _html_with_img("https://example.com/img.jpg"))
        result = validate_image_links(f, self.assets)
        self.assertTrue(result["ok"])


class TestValidateNoForbiddenCss(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write(self, name, html):
        p = self.tmp / name
        p.write_text(html, encoding="utf-8")
        return p

    def test_fails_reader_css_in_archive(self):
        f = self._write("arch.html",
            '<html><head>'
            '<link rel="stylesheet" href="../book-reader/book-reader.css">'
            '</head><body></body></html>')
        result = validate_no_forbidden_css(f, "archive")
        self.assertFalse(result["ok"])
        self.assertTrue(any("book-reader.css" in e for e in result["errors"]))
        self.assertTrue(any(str(f) in e for e in result["errors"]))

    def test_fails_reader_css_in_working(self):
        f = self._write("work.html",
            '<html><head>'
            '<link rel="stylesheet" href="../book-reader/book-reader.css">'
            '</head><body></body></html>')
        result = validate_no_forbidden_css(f, "working")
        self.assertFalse(result["ok"])

    def test_passes_no_reader_css_in_archive(self):
        f = self._write("clean.html",
            '<html><head><link rel="stylesheet" href="../../../../css/style.css"></head><body></body></html>')
        result = validate_no_forbidden_css(f, "archive")
        self.assertTrue(result["ok"])

    def test_fails_garbage_path_in_img(self):
        f = self._write("garbage.html",
            '<html><head></head><body><img src="assets/assets/img.webp"/></body></html>')
        result = validate_no_forbidden_css(f, "preview")
        self.assertFalse(result["ok"])

    def test_reader_css_allowed_in_preview(self):
        f = self._write("preview.html",
            '<html><head>'
            '<link rel="stylesheet" href="../book-reader/book-reader.css">'
            '</head><body></body></html>')
        result = validate_no_forbidden_css(f, "preview")
        self.assertTrue(result["ok"])


class TestValidateNoDuplicateStylesheets(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write(self, name, html):
        p = self.tmp / name
        p.write_text(html, encoding="utf-8")
        return p

    def test_passes_single_stylesheet(self):
        f = self._write("ok.html",
            '<html><head><link rel="stylesheet" href="../../css/style.css"></head><body></body></html>')
        result = validate_no_duplicate_stylesheets(f)
        self.assertTrue(result["ok"])

    def test_fails_duplicate_stylesheets(self):
        f = self._write("dup.html",
            '<html><head>'
            '<link rel="stylesheet" href="../../css/style.css">'
            '<link rel="stylesheet" href="../../css/style.css">'
            '</head><body></body></html>')
        result = validate_no_duplicate_stylesheets(f)
        self.assertFalse(result["ok"])
        self.assertTrue(any("Duplicate" in e for e in result["errors"]))
        self.assertTrue(any(str(f) in e for e in result["errors"]))


class TestValidateImageSrcPattern(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write(self, name, html):
        p = self.tmp / name
        p.write_text(html, encoding="utf-8")
        return p

    def test_preview_bare_assets_passes(self):
        f = self._write("ok.html", _html_with_img("assets/img.webp"))
        result = validate_image_src_pattern(f, "preview")
        self.assertTrue(result["ok"])

    def test_preview_relative_fails(self):
        f = self._write("bad.html", _html_with_img("../../../assets/img.webp"))
        result = validate_image_src_pattern(f, "preview")
        self.assertFalse(result["ok"])
        self.assertTrue(any(str(f) in e for e in result["errors"]))

    def test_archive_correct_depth_passes(self):
        f = self._write("ok.html", _html_with_img("../../../assets/img.webp"))
        result = validate_image_src_pattern(f, "archive")
        self.assertTrue(result["ok"])

    def test_archive_wrong_depth_fails(self):
        f = self._write("bad.html", _html_with_img("../assets/img.webp"))
        result = validate_image_src_pattern(f, "archive")
        self.assertFalse(result["ok"])
        self.assertTrue(any("Wrong image path pattern" in e for e in result["errors"]))

    def test_raw_stage_always_passes(self):
        f = self._write("raw.html", _html_with_img("anything/img.webp"))
        result = validate_image_src_pattern(f, "raw")
        self.assertTrue(result["ok"])

    def test_external_url_not_flagged(self):
        f = self._write("ext.html", _html_with_img("https://example.com/img.jpg"))
        result = validate_image_src_pattern(f, "preview")
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
