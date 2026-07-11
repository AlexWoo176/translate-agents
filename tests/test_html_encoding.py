import unittest
import tempfile
import os
from pathlib import Path
from bs4 import BeautifulSoup

from src.utils.html_encoding import (
    read_text_utf8,
    write_text_utf8,
    ensure_meta_charset_utf8,
    has_mojibake,
    detect_mojibake_tokens
)

class TestHtmlEncoding(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_utf8_symbols_survival(self):
        """Test that UTF-8 symbols survive write and read operations."""
        symbols = "μ, σ, α, ≤, ≥, ≠, ±, x̄, ’, —, tiếng Việt có dấu huyền sắc hỏi ngã nặng"
        test_file = self.temp_dir / "test_symbols.txt"
        
        write_text_utf8(test_file, symbols)
        read_content = read_text_utf8(test_file)
        
        self.assertEqual(read_content, symbols)

    def test_ensure_meta_charset_utf8_adds_tag(self):
        """Test that ensure_meta_charset_utf8 adds the charset meta tag to HTML head."""
        html = "<html><head><title>Test</title></head><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        
        ensure_meta_charset_utf8(soup)
        
        meta = soup.find('meta', charset=True)
        self.assertIsNotNone(meta)
        self.assertEqual(meta['charset'], 'utf-8')
        # Check that it's prepended (first child in head)
        self.assertEqual(soup.head.contents[0], meta)

    def test_ensure_meta_charset_utf8_creates_head_if_missing(self):
        """Test that ensure_meta_charset_utf8 creates head tag if it's missing."""
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        
        ensure_meta_charset_utf8(soup)
        
        self.assertIsNotNone(soup.head)
        meta = soup.head.find('meta', charset=True)
        self.assertIsNotNone(meta)
        self.assertEqual(meta['charset'], 'utf-8')

    def test_mojibake_detection(self):
        """Test that mojibake detection correctly flags corrupted strings."""
        corrupted_cases = [
            "H0: Î¼ = 2.0",
            "standard deviation is Ïσ",
            "alpha: Î±",
            "value â‰¤ 15",
            "value â‰¥ 15",
            "participantâ€™s name",
            "beautyâ€”instead",
            "overline Â¯"
        ]
        
        for case in corrupted_cases:
            self.assertTrue(has_mojibake(case), f"Failed to detect mojibake in: {case}")
            tokens = detect_mojibake_tokens(case)
            self.assertGreater(len(tokens), 0, f"No tokens detected in: {case}")

    def test_no_mojibake_false_positives_on_vietnamese(self):
        """Test that mojibake detection does not falsely flag correct Vietnamese text."""
        clean_vietnamese = (
            "Xin chào, đây là tiếng Việt có dấu. "
            "Biến cố hợp, biến cố giao, mức ý nghĩa alpha. "
            "Các ký hiệu toán học chính xác: μ, σ, α, ≤, ≥, ≠, ±, x̄, ’, —. "
            "Giá trị trung bình quần thể."
        )
        self.assertFalse(has_mojibake(clean_vietnamese))
        self.assertEqual(len(detect_mojibake_tokens(clean_vietnamese)), 0)

    def test_no_implicit_path_io_without_encoding_in_core(self):
        """
        Static analysis test:
        Ensure no .read_text() or .write_text() is called in src/ without explicit encoding.
        """
        src_root = Path(__file__).parent.parent / "src"
        pattern_read = ".read_text("
        pattern_write = ".write_text("
        
        violations = []
        
        for root, _, files in os.walk(src_root):
            for file in files:
                if file.endswith(".py"):
                    filepath = Path(root) / file
                    content = filepath.read_text(encoding="utf-8")
                    
                    # Search for occurrences of .read_text(
                    if pattern_read in content:
                        lines = content.splitlines()
                        for idx, line in enumerate(lines):
                            if pattern_read in line and "encoding=" not in line:
                                violations.append(f"{filepath.name}:{idx+1} - {line.strip()}")
                                
                    if pattern_write in content:
                        lines = content.splitlines()
                        for idx, line in enumerate(lines):
                            if pattern_write in line and "encoding=" not in line:
                                violations.append(f"{filepath.name}:{idx+1} - {line.strip()}")
                                
        self.assertEqual(len(violations), 0, f"Found implicit encoding read/write operations: {violations}")

if __name__ == "__main__":
    unittest.main()
