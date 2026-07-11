import unittest
import tempfile
import shutil
from pathlib import Path
from bs4 import BeautifulSoup

from src.exporters.markdown_exporter import export_html_to_markdown

class TestMarkdownExporter(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.html_file = self.test_dir / "test.html"
        self.md_file = self.test_dir / "test.md"

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_markdown_conversions(self):
        html_content = (
            "<html>\n"
            "<body>\n"
            "  <h1>Heading 1</h1>\n"
            "  <h2>Heading 2</h2>\n"
            "  <p>This is a paragraph with <strong>bold</strong> and <em>italics</em> and <a href=\"https://example.com\">link</a>.</p>\n"
            "  <ul>\n"
            "    <li>First item</li>\n"
            "    <li>Second item</li>\n"
            "  </ul>\n"
            "  <table>\n"
            "    <tr><th>Header A</th><th>Header B</th></tr>\n"
            "    <tr><td>Value 1</td><td>Value 2</td></tr>\n"
            "  </table>\n"
            "</body>\n"
            "</html>"
        )
        with open(self.html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        success = export_html_to_markdown(self.html_file, self.md_file)
        self.assertTrue(success)
        self.assertTrue(self.md_file.is_file())

        with open(self.md_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Check conversion details
        self.assertIn("# Heading 1", content)
        self.assertIn("## Heading 2", content)
        self.assertIn("This is a paragraph with **bold** and *italics* and [link](https://example.com).", content)
        self.assertIn("- First item", content)
        self.assertIn("- Second item", content)
        self.assertIn("| Header A | Header B |", content)
        self.assertIn("| Value 1 | Value 2 |", content)

if __name__ == "__main__":
    unittest.main()
