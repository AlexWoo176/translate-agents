"""
test_verify_resources.py — Integration tests for the verify-resources CLI command
and the resource_verifier orchestrator.

Tests:
- Passes on a valid fixture
- Fails on missing stylesheet
- Fails on missing image file
- Fails on wrong archive image path
- Fails on book-reader.css inside archive
- Fails on duplicate style links
- Error messages include file path
- Warns on issues in raw stage (does not fail)
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.qa.resource_verifier import verify_book_resources


def _build_book_fixture(root: Path, book_slug: str) -> dict:
    """
    Build a minimal valid book fixture under root/book_slug.
    Returns a dict of key paths for test assertions.
    """
    book_root = root / book_slug
    book_root.mkdir(parents=True)

    # css
    css_dir = book_root / "css"
    css_dir.mkdir()
    (css_dir / "style.css").write_text("body{}", encoding="utf-8")

    # chapter-1
    chap = book_root / "chapter-1"
    assets = chap / "assets"
    assets.mkdir(parents=True)
    (assets / "img-1-1.webp").write_bytes(b"FAKE")

    # 02-clean (working)
    clean = chap / "02-clean"
    clean.mkdir()
    (clean / "1-1.html").write_text(
        '<html><head><link rel="stylesheet" href="../../css/style.css"></head>'
        '<body><img src="../assets/img-1-1.webp" alt="x"/></body></html>',
        encoding="utf-8",
    )

    # 04-prep (working)
    prep = chap / "04-prep"
    prep.mkdir()
    (prep / "1-1.html").write_text(
        '<html><head><link rel="stylesheet" href="../../css/style.css"></head>'
        '<body><p>text</p></body></html>',
        encoding="utf-8",
    )

    # 05-translated (working)
    trans = chap / "05-translated"
    trans.mkdir()
    (trans / "1-1.html").write_text(
        '<html><head><link rel="stylesheet" href="../../css/style.css"></head>'
        '<body><p>text</p></body></html>',
        encoding="utf-8",
    )

    # 07-archive/bilingual/html
    arch_bil = chap / "07-archive" / "bilingual" / "html"
    arch_bil.mkdir(parents=True)
    (arch_bil / "1-1.html").write_text(
        '<html><head><link rel="stylesheet" href="../../../../css/style.css"></head>'
        '<body><img src="../../../assets/img-1-1.webp" alt="x"/></body></html>',
        encoding="utf-8",
    )

    # 07-archive/vn-only/html
    arch_vn = chap / "07-archive" / "vn-only" / "html"
    arch_vn.mkdir(parents=True)
    (arch_vn / "1-1.html").write_text(
        '<html><head><link rel="stylesheet" href="../../../../css/style.css"></head>'
        '<body><p>text</p></body></html>',
        encoding="utf-8",
    )

    # .html preview
    preview_root = book_root / ".html"
    preview_css = preview_root / "css"
    preview_css.mkdir(parents=True)
    (preview_css / "style.css").write_text("body{}", encoding="utf-8")
    preview_br = preview_root / "book-reader"
    preview_br.mkdir()
    (preview_br / "book-reader.css").write_text(".br{}", encoding="utf-8")
    (preview_br / "book-reader.js").write_text("var x=1;", encoding="utf-8")
    preview_chap = preview_root / "chapter-1"
    preview_assets = preview_chap / "assets"
    preview_assets.mkdir(parents=True)
    (preview_assets / "img-1-1.webp").write_bytes(b"FAKE")
    (preview_chap / "1-1.html").write_text(
        '<html><head>'
        '<link rel="stylesheet" href="../css/style.css">'
        '<link rel="stylesheet" href="../book-reader/book-reader.css">'
        '</head><body><img src="assets/img-1-1.webp" alt="x"/></body></html>',
        encoding="utf-8",
    )

    return {"book_root": book_root, "chap": chap, "assets": assets, "arch_bil": arch_bil}


class TestVerifyResourcesValid(unittest.TestCase):
    """verify-resources passes on a correctly structured book."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.book_slug = "test-verify-book"
        self.paths = _build_book_fixture(self.tmp, self.book_slug)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    @patch("src.qa.resource_verifier.get_book_root")
    @patch("src.qa.resource_verifier.get_web_output_root")
    @patch("src.qa.resource_verifier.get_phase_dir")
    @patch("src.qa.resource_verifier.get_archive_dir")
    def test_passes_on_valid_fixture(self, mock_arch, mock_phase, mock_web, mock_book):
        book_root = self.paths["book_root"]
        mock_book.return_value = book_root
        mock_web.return_value = self.tmp / "web-site"  # doesn't exist → web stage skipped without error if not run
        mock_phase.side_effect = lambda b, c, p: book_root / f"chapter-{c}" / {
            "raw": "01-raw", "clean": "02-clean", "prep": "04-prep", "translated": "05-translated"
        }.get(p, p)
        mock_arch.side_effect = lambda b, c, m, f: book_root / f"chapter-{c}" / "07-archive" / m / f

        # Run only chapter-scoped stages (no preview/web — those need web-site to exist)
        exit_code, report = verify_book_resources(self.book_slug, chapter="1", stage="working")
        self.assertEqual(exit_code, 0, f"Expected pass but got errors: {report['errors']}")
        self.assertEqual(report["total_errors"], 0)

    @patch("src.qa.resource_verifier.get_book_root")
    @patch("src.qa.resource_verifier.get_web_output_root")
    @patch("src.qa.resource_verifier.get_phase_dir")
    @patch("src.qa.resource_verifier.get_archive_dir")
    def test_passes_archive_stage(self, mock_arch, mock_phase, mock_web, mock_book):
        book_root = self.paths["book_root"]
        mock_book.return_value = book_root
        mock_web.return_value = self.tmp / "web-site"
        mock_phase.side_effect = lambda b, c, p: book_root / f"chapter-{c}" / {
            "raw": "01-raw", "clean": "02-clean", "prep": "04-prep", "translated": "05-translated"
        }.get(p, p)
        mock_arch.side_effect = lambda b, c, m, f: book_root / f"chapter-{c}" / "07-archive" / m / f

        exit_code, report = verify_book_resources(self.book_slug, chapter="1", stage="archive")
        self.assertEqual(exit_code, 0, f"Expected pass but got errors: {report['errors']}")

    @patch("src.qa.resource_verifier.get_book_root")
    @patch("src.qa.resource_verifier.get_web_output_root")
    @patch("src.qa.resource_verifier.get_phase_dir")
    @patch("src.qa.resource_verifier.get_archive_dir")
    def test_passes_preview_stage(self, mock_arch, mock_phase, mock_web, mock_book):
        book_root = self.paths["book_root"]
        mock_book.return_value = book_root
        mock_web.return_value = self.tmp / "web-site"
        mock_phase.side_effect = lambda b, c, p: book_root / f"chapter-{c}" / {
            "raw": "01-raw", "clean": "02-clean", "prep": "04-prep", "translated": "05-translated"
        }.get(p, p)
        mock_arch.side_effect = lambda b, c, m, f: book_root / f"chapter-{c}" / "07-archive" / m / f

        exit_code, report = verify_book_resources(self.book_slug, chapter="1", stage="preview")
        self.assertEqual(exit_code, 0, f"Expected pass but got errors: {report['errors']}")


class TestVerifyResourcesFailures(unittest.TestCase):
    """verify-resources correctly detects contract violations."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.book_slug = "test-fail-book"
        self.paths = _build_book_fixture(self.tmp, self.book_slug)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _run(self, chapter, stage):
        book_root = self.paths["book_root"]
        with patch("src.qa.resource_verifier.get_book_root", return_value=book_root), \
             patch("src.qa.resource_verifier.get_web_output_root", return_value=self.tmp / "web-site"), \
             patch("src.qa.resource_verifier.get_phase_dir",
                   side_effect=lambda b, c, p: book_root / f"chapter-{c}" / {
                       "raw": "01-raw", "clean": "02-clean",
                       "prep": "04-prep", "translated": "05-translated"
                   }.get(p, p)), \
             patch("src.qa.resource_verifier.get_archive_dir",
                   side_effect=lambda b, c, m, f: book_root / f"chapter-{c}" / "07-archive" / m / f):
            return verify_book_resources(self.book_slug, chapter=chapter, stage=stage)

    def test_fails_missing_stylesheet_in_working(self):
        # Corrupt a working file by removing style.css link
        html_file = self.paths["book_root"] / "chapter-1" / "02-clean" / "1-1.html"
        html_file.write_text("<html><head></head><body></body></html>", encoding="utf-8")

        exit_code, report = self._run("1", "working")
        self.assertEqual(exit_code, 1)
        self.assertGreater(report["total_errors"], 0)
        all_errors = " ".join(e for errs in report["errors"].values() for e in errs)
        self.assertIn("Missing style.css", all_errors)
        # Error must include the file path
        self.assertTrue(any(str(html_file) in k for k in report["errors"]))

    def test_fails_missing_image_file(self):
        # Reference a non-existent image
        html_file = self.paths["book_root"] / "chapter-1" / "02-clean" / "1-1.html"
        html_file.write_text(
            '<html><head><link rel="stylesheet" href="../../css/style.css"></head>'
            '<body><img src="../assets/missing.webp" alt="x"/></body></html>',
            encoding="utf-8",
        )

        exit_code, report = self._run("1", "working")
        self.assertEqual(exit_code, 1)
        all_errors = " ".join(e for errs in report["errors"].values() for e in errs)
        self.assertIn("Missing image", all_errors)
        self.assertTrue(any(str(html_file) in k for k in report["errors"]))

    def test_fails_wrong_archive_image_path(self):
        # Use wrong depth (../assets/ instead of ../../../assets/)
        arch_file = self.paths["arch_bil"] / "1-1.html"
        arch_file.write_text(
            '<html><head><link rel="stylesheet" href="../../../../css/style.css"></head>'
            '<body><img src="../assets/img-1-1.webp" alt="x"/></body></html>',
            encoding="utf-8",
        )

        exit_code, report = self._run("1", "archive")
        self.assertEqual(exit_code, 1)
        all_errors = " ".join(e for errs in report["errors"].values() for e in errs)
        self.assertIn("Wrong image path pattern", all_errors)
        self.assertTrue(any(str(arch_file) in k for k in report["errors"]))

    def test_fails_reader_css_in_archive(self):
        arch_file = self.paths["arch_bil"] / "1-1.html"
        arch_file.write_text(
            '<html><head>'
            '<link rel="stylesheet" href="../../../../css/style.css">'
            '<link rel="stylesheet" href="../book-reader/book-reader.css">'
            '</head><body></body></html>',
            encoding="utf-8",
        )

        exit_code, report = self._run("1", "archive")
        self.assertEqual(exit_code, 1)
        all_errors = " ".join(e for errs in report["errors"].values() for e in errs)
        self.assertIn("book-reader.css", all_errors)
        self.assertTrue(any(str(arch_file) in k for k in report["errors"]))

    def test_fails_duplicate_style_links(self):
        html_file = self.paths["book_root"] / "chapter-1" / "02-clean" / "1-1.html"
        html_file.write_text(
            '<html><head>'
            '<link rel="stylesheet" href="../../css/style.css">'
            '<link rel="stylesheet" href="../../css/style.css">'
            '</head><body></body></html>',
            encoding="utf-8",
        )

        exit_code, report = self._run("1", "working")
        self.assertEqual(exit_code, 1)
        all_errors = " ".join(e for errs in report["errors"].values() for e in errs)
        self.assertIn("Duplicate", all_errors)
        self.assertTrue(any(str(html_file) in k for k in report["errors"]))

    def test_error_messages_include_file_path(self):
        """All error messages must contain the affected file path."""
        html_file = self.paths["book_root"] / "chapter-1" / "02-clean" / "1-1.html"
        html_file.write_text("<html><head></head><body></body></html>", encoding="utf-8")

        exit_code, report = self._run("1", "working")
        self.assertEqual(exit_code, 1)
        # Every error dict key should be a path to a real file
        for key in report["errors"]:
            self.assertTrue(
                key.startswith("__") or Path(key).suffix in (".html", ".css"),
                f"Error key doesn't look like a file path: {key}"
            )


class TestVerifyResourcesRawPolicy(unittest.TestCase):
    """01-raw is report-only — never causes exit_code=1."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.book_slug = "test-raw-book"
        self.paths = _build_book_fixture(self.tmp, self.book_slug)
        # Create a raw folder with injected style.css (should only warn, not error)
        raw_dir = self.paths["book_root"] / "chapter-1" / "01-raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / "1-1.html").write_text(
            "<html><head><link rel='stylesheet' href='../../css/style.css'></head><body></body></html>",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    @patch("src.qa.resource_verifier.get_book_root")
    @patch("src.qa.resource_verifier.get_web_output_root")
    @patch("src.qa.resource_verifier.get_phase_dir")
    @patch("src.qa.resource_verifier.get_archive_dir")
    def test_raw_issues_are_warnings_not_errors(self, mock_arch, mock_phase, mock_web, mock_book):
        book_root = self.paths["book_root"]
        mock_book.return_value = book_root
        mock_web.return_value = self.tmp / "web-site"
        mock_phase.side_effect = lambda b, c, p: book_root / f"chapter-{c}" / {
            "raw": "01-raw", "clean": "02-clean", "prep": "04-prep", "translated": "05-translated"
        }.get(p, p)
        mock_arch.side_effect = lambda b, c, m, f: book_root / f"chapter-{c}" / "07-archive" / m / f

        # 01-raw with no style.css — should warn only, not error
        raw_dir = self.paths["book_root"] / "chapter-1" / "01-raw"
        (raw_dir / "1-1.html").write_text("<html><head></head><body></body></html>", encoding="utf-8")

        exit_code, report = verify_book_resources(self.book_slug, chapter="1", stage="raw")
        self.assertEqual(exit_code, 0, "raw stage issues should not cause exit_code=1")
        self.assertEqual(report["total_errors"], 0)


if __name__ == "__main__":
    unittest.main()
