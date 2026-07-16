import unittest
import tempfile
from pathlib import Path
from src.qa.translation_qa import check_file_translation_qa

class TestTranslationQA(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _create_html(self, content):
        f = self.tmp_path / "test.html"
        f.write_text(content, encoding="utf-8")
        return f

    def test_pass_clean_bilingual(self):
        html = """
        <html><body>
          <p id="p1" class="eng hidden">This is a valid English sentence for testing.</p>
          <p id="p1-vn" class="vn visible">Đây là một câu tiếng Việt hợp lệ để kiểm tra.</p>
        </body></html>
        """
        f = self._create_html(html)
        res = check_file_translation_qa(f)
        self.assertEqual(res["status"], "PASS")
        self.assertEqual(len(res["issues"]), 0)

    def test_fail_untranslated_block(self):
        html = """
        <html><body>
          <p id="p1" class="eng hidden">This is a valid English sentence for testing.</p>
          <p id="p1-vn" class="vn visible">This is a valid English sentence for testing.</p>
        </body></html>
        """
        f = self._create_html(html)
        res = check_file_translation_qa(f)
        self.assertEqual(res["status"], "FAIL")
        self.assertTrue(any("matches EN exactly" in issue for issue in res["issues"]))

    def test_fail_english_stopwords_leak(self):
        html = """
        <html><body>
          <p id="p1" class="eng hidden">This is a valid English sentence for testing.</p>
          <p id="p1-vn" class="vn visible">Đây là một câu tiếng Việt with some English stopwords like the or and.</p>
        </body></html>
        """
        f = self._create_html(html)
        res = check_file_translation_qa(f)
        self.assertEqual(res["status"], "FAIL")
        self.assertTrue(any("English stopwords" in issue for issue in res["issues"]))

    def test_fail_truncation(self):
        html = """
        <html><body>
          <p id="p1" class="eng hidden">This is a very long English sentence designed to test whether the translation is too short or not.</p>
          <p id="p1-vn" class="vn visible">Ngắn quá.</p>
        </body></html>
        """
        f = self._create_html(html)
        res = check_file_translation_qa(f)
        self.assertEqual(res["status"], "FAIL")
        self.assertTrue(any("Potential Truncation" in issue for issue in res["issues"]))

    def test_fail_hallucination(self):
        html = """
        <html><body>
          <p id="p1" class="eng hidden">Short English.</p>
          <p id="p1-vn" class="vn visible">Đây là một câu dịch siêu dài, lặp đi lặp lại rất nhiều từ ngữ nhằm mục đích tạo ra một tỷ lệ ký tự vượt quá giới hạn ba trăm phần trăm so với văn bản gốc tiếng Anh ban đầu.</p>
        </body></html>
        """
        f = self._create_html(html)
        res = check_file_translation_qa(f)
        self.assertEqual(res["status"], "FAIL")
        self.assertTrue(any("Potential Hallucination" in issue for issue in res["issues"]))

    def test_reference_exemption(self):
        # A block containing English stopwords or identical text inside a reference container should pass
        html = """
        <html><body>
          <div class="references">
            <p id="p1" class="eng hidden">Boas, Franz. 1922. The Mind of Primitive Man.</p>
            <p id="p1-vn" class="vn visible">Boas, Franz. 1922. The Mind of Primitive Man.</p>
          </div>
        </body></html>
        """
        f = self._create_html(html)
        res = check_file_translation_qa(f)
        self.assertEqual(res["status"], "PASS")
        self.assertEqual(len(res["issues"]), 0)

    def test_credit_exemption(self):
        # A block containing credit text should be exempt from stopword checks and identity checks
        html = """
        <html><body>
          <p id="p1" class="eng hidden">This image is courtesy of NASA, CC BY 2.0.</p>
          <p id="p1-vn" class="vn visible">This image is courtesy of NASA, CC BY 2.0.</p>
        </body></html>
        """
        f = self._create_html(html)
        res = check_file_translation_qa(f)
        self.assertEqual(res["status"], "PASS")
        self.assertEqual(len(res["issues"]), 0)

if __name__ == "__main__":
    unittest.main()
