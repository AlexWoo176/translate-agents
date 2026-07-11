import unittest
import tempfile
import shutil
from pathlib import Path

from src.exporters.pdf_exporter import export_html_to_pdf

class TestPdfExporter(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.html_file = self.test_dir / "test.html"
        self.pdf_file = self.test_dir / "test.pdf"

        with open(self.html_file, "w", encoding="utf-8") as f:
            f.write("<html><body><p>Hello PDF</p></body></html>")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_pdf_export_graceful_handling(self):
        # This will return True if a PDF engine is available, or False if none are installed.
        # It should not raise unexpected exceptions.
        try:
            result = export_html_to_pdf(self.html_file, self.pdf_file)
            if result:
                self.assertTrue(self.pdf_file.is_file())
            else:
                self.assertFalse(self.pdf_file.is_file())
        except Exception as e:
            self.fail(f"PDF exporter raised unexpected exception: {e}")

if __name__ == "__main__":
    unittest.main()
