import unittest
from bs4 import BeautifulSoup
from scripts.audit_english_residue import (
    is_hidden,
    should_skip_tag,
    is_formula_or_notation,
    is_proper_noun_list_or_entity,
    is_credit_text,
    is_answer_key,
    is_reference,
    check_text_residue_v3,
    deduplicate_findings
)
from pathlib import Path

class TestAuditEnglishResidueV3(unittest.TestCase):
    
    def test_proper_noun_restaurant_list_should_not_be_p0_p1(self):
        # 1. Proper noun restaurant list should not be P0/P1
        text = "Amber Indian, La Fiesta, Fiesta del Mar, Dawit"
        html = f'<p>{text}</p>'
        tag = BeautifulSoup(html, 'html.parser').p
        res = check_text_residue_v3(tag, text)
        # Expected: NOT_ISSUE (ignored) or P2 (review), not actionable P0/P1 issue
        self.assertIn(res['status'], ['ignored', 'review'])
        if res['status'] == 'review':
            self.assertEqual(res['severity'], 'P2')

    def test_formula_y_a_bx_should_not_be_p0_p1(self):
        # 2. Formula y=a+bx should not be P0/P1
        text = "y = a + bx"
        html = f'<p>{text}</p>'
        tag = BeautifulSoup(html, 'html.parser').p
        res = check_text_residue_v3(tag, text)
        self.assertEqual(res['status'], 'ignored')
        self.assertEqual(res['category'], 'formula_only')

    def test_hypothesis_notation_should_not_be_p0_p1(self):
        # 3. Hypothesis notation should not be P0/P1
        text = "Ha: μd < 0"
        html = f'<p>{text}</p>'
        tag = BeautifulSoup(html, 'html.parser').p
        res = check_text_residue_v3(tag, text)
        self.assertEqual(res['status'], 'ignored')
        self.assertEqual(res['category'], 'formula_only')

    def test_answer_key_should_not_be_p0_p1(self):
        # 4. Answer key should not be P0/P1
        text = "1. f; 2. g; 3. e; 4. d"
        html = f'<p>{text}</p>'
        tag = BeautifulSoup(html, 'html.parser').p
        res = check_text_residue_v3(tag, text)
        self.assertEqual(res['status'], 'ignored')
        self.assertEqual(res['category'], 'answer_keys')

    def test_formula_label_should_be_p1(self):
        # 5. Formula label should be P1
        text = "The standard error is:"
        html = f'<p>{text}</p>'
        tag = BeautifulSoup(html, 'html.parser').p
        res = check_text_residue_v3(tag, text)
        self.assertEqual(res['status'], 'issue')
        self.assertEqual(res['severity'], 'P1')

    def test_full_english_instruction_should_be_p0(self):
        # 6. Full English instruction should be P0
        text = "Survey the students in your class, asking them if they were born in this state."
        html = f'<p>{text}</p>'
        tag = BeautifulSoup(html, 'html.parser').p
        res = check_text_residue_v3(tag, text)
        self.assertEqual(res['status'], 'issue')
        self.assertEqual(res['severity'], 'P0')

    def test_english_prose_with_technical_term_should_still_be_issue(self):
        # 7. English prose with technical term should still be issue
        text = "If the p-value is less than the significance level (α = 0.05):"
        html = f'<p>{text}</p>'
        tag = BeautifulSoup(html, 'html.parser').p
        res = check_text_residue_v3(tag, text)
        self.assertEqual(res['status'], 'issue')
        self.assertIn(res['severity'], ['P0', 'P1'])

    def test_credit_only_caption_should_not_be_p0_p1(self):
        # 8. Credit-only caption should not be P0/P1
        text = "credit: modification of work by Phil Whitehouse/Flickr, CC BY 2.0"
        
        # Scenario A: Outside caption (Ignored/NOT_ISSUE)
        html_out = f'<div>{text}</div>'
        tag_out = BeautifulSoup(html_out, 'html.parser').div
        res_out = check_text_residue_v3(tag_out, text)
        self.assertEqual(res_out['status'], 'ignored')
        self.assertEqual(res_out['category'], 'credits')

        # Scenario B: Inside caption (P2 Review)
        html_in = f'<caption>{text}</caption>'
        tag_in = BeautifulSoup(html_in, 'html.parser').caption
        res_in = check_text_residue_v3(tag_in, text)
        self.assertEqual(res_in['status'], 'review')
        self.assertEqual(res_in['severity'], 'P2')

    def test_deduplicate_same_issue_across_stages(self):
        # 9. Deduplicate same issue across stages
        findings = [
            {
                'severity': 'P0', 'chapter': 'chapter-1', 'file': 'ex1.html', 'stage': '05-translated',
                'block_id': 'p1', 'tag': 'p', 'likely_cause': 'CAUSE_TRANSLATION_SKIPPED', 'issue_type': 'English prose residue',
                'vn_snippet': 'This is English.', 'source_snippet': 'This is English.', 'root_cause': 'CAUSE_TRANSLATION_SKIPPED'
            },
            {
                'severity': 'P0', 'chapter': 'chapter-1', 'file': 'ex1.html', 'stage': '07-archive-vn-only',
                'block_id': 'p1', 'tag': 'p', 'likely_cause': 'CAUSE_TRANSLATION_SKIPPED', 'issue_type': 'English prose in vn-only',
                'vn_snippet': 'This is English.', 'source_snippet': 'This is English.', 'root_cause': 'CAUSE_TRANSLATION_SKIPPED'
            },
            {
                'severity': 'P0', 'chapter': 'chapter-1', 'file': 'ex1.html', 'stage': 'preview',
                'block_id': 'p1', 'tag': 'p', 'likely_cause': 'CAUSE_TRANSLATION_SKIPPED', 'issue_type': 'English prose in preview',
                'vn_snippet': 'This is English.', 'source_snippet': 'This is English.', 'root_cause': 'CAUSE_TRANSLATION_SKIPPED'
            }
        ]
        
        repairs = deduplicate_findings(findings, Path("books"), Path("web-site"))
        self.assertEqual(len(repairs), 1)
        rep = repairs[0]
        self.assertEqual(rep['repair_target_stage'], '05-translated')
        self.assertEqual(rep['downstream_impacted_stages'], '07-archive-vn-only, preview')

    def test_downstream_only_issue(self):
        # 10. Downstream-only issue
        findings = [
            {
                'severity': 'P0', 'chapter': 'chapter-1', 'file': 'ex1.html', 'stage': '07-archive-vn-only',
                'block_id': 'p1', 'tag': 'p', 'likely_cause': 'CAUSE_EXPORTER_SELECTED_WRONG_BLOCK', 'issue_type': 'English prose in vn-only',
                'vn_snippet': 'This is English.', 'source_snippet': 'This is English.', 'root_cause': 'CAUSE_EXPORTER_SELECTED_WRONG_BLOCK'
            }
        ]
        repairs = deduplicate_findings(findings, Path("books"), Path("web-site"))
        self.assertEqual(len(repairs), 1)
        rep = repairs[0]
        self.assertEqual(rep['repair_target_stage'], 'exporter/archive')
        self.assertEqual(rep['downstream_impacted_stages'], 'none')

    def test_hidden_english_still_ignored(self):
        # 11. Hidden English still ignored
        html = '<div class="eng hidden">The curve is nonsymmetrical.</div>'
        tag = BeautifulSoup(html, 'html.parser').div
        res = check_text_residue_v3(tag, "The curve is nonsymmetrical.")
        self.assertEqual(res['status'], 'ignored')
        self.assertEqual(res['category'], 'hidden_english')

    def test_mixed_vietnamese_plus_english_sentence_should_be_p1(self):
        # 12. Mixed Vietnamese + English sentence should be P1
        text = "Nội dung đã dịch. The standard deviation is:"
        html = f'<p>{text}</p>'
        tag = BeautifulSoup(html, 'html.parser').p
        res = check_text_residue_v3(tag, text)
        self.assertEqual(res['status'], 'issue')
        self.assertEqual(res['severity'], 'P1')

    # Audit V4 Test Cases
    def test_mathjax_formula_should_not_be_actionable(self):
        # MathJax formula with math tags should not trigger english residue
        html = '<p id="p-math-1">y = a + bx <span class="os-math-in-para"><mjx-container>some_mjx_math_tokens</mjx-container></span></p>'
        soup = BeautifulSoup(html, 'html.parser')
        tag = soup.find(id="p-math-1")
        from scripts.audit_english_residue import get_text_excluding_math
        clean_text = get_text_excluding_math(tag)
        self.assertEqual(clean_text.strip(), "y = a + bx")
        res = check_text_residue_v3(tag, clean_text)
        self.assertEqual(res['status'], 'ignored')
        self.assertEqual(res['category'], 'formula_only')

    def test_mean_of_frequency_table_in_mathjax_should_not_be_actionable(self):
        # Mean of Frequency Table inside MathJax should be ignored
        html = '<p id="p-math-2"><mjx-container>Mean of Frequency Table</mjx-container></p>'
        soup = BeautifulSoup(html, 'html.parser')
        tag = soup.find(id="p-math-2")
        from scripts.audit_english_residue import get_text_excluding_math
        clean_text = get_text_excluding_math(tag)
        self.assertEqual(clean_text.strip(), "")
        res = check_text_residue_v3(tag, clean_text)
        self.assertEqual(res['status'], 'ignored')
        self.assertEqual(res['category'], 'empty')

    def test_calculator_command_should_not_be_actionable(self):
        # Calculator command should not flag as English residue
        text = "Nhấn STAT. Di chuyển sang TESTS. Nhấn 5:2-SampTTest."
        html = f'<p>{text}</p>'
        tag = BeautifulSoup(html, 'html.parser').p
        res = check_text_residue_v3(tag, text)
        self.assertEqual(res['status'], 'ignored')

    def test_translated_vietnamese_with_english_product_names_should_not_be_actionable(self):
        # Translated Vietnamese with English terms like Excel, TI-83/84
        text = "Sử dụng phần mềm Excel hoặc máy tính TI-83/84 để phân tích."
        html = f'<p>{text}</p>'
        tag = BeautifulSoup(html, 'html.parser').p
        res = check_text_residue_v3(tag, text)
        self.assertEqual(res['status'], 'ignored')

    def test_table_label_should_be_p1_actionable(self):
        # Table label should be P1 label issue
        text = "Table 11.18 Nhu cầu thành công trong học tập"
        html = f'<p>{text}</p>'
        tag = BeautifulSoup(html, 'html.parser').p
        res = check_text_residue_v3(tag, text)
        self.assertEqual(res['status'], 'label_issue')
        self.assertEqual(res['severity'], 'P1')
        self.assertEqual(res['current_label'], 'Table 11.18')
        self.assertEqual(res['expected_label'], 'Bảng 11.18')

    def test_figure_label_should_be_p1_actionable(self):
        # Figure label should be P1 label issue
        text = "Figure 9.1 Phân phối chuẩn"
        html = f'<p>{text}</p>'
        tag = BeautifulSoup(html, 'html.parser').p
        res = check_text_residue_v3(tag, text)
        self.assertEqual(res['status'], 'label_issue')
        self.assertEqual(res['severity'], 'P1')
        self.assertEqual(res['current_label'], 'Figure 9.1')
        self.assertEqual(res['expected_label'], 'Hình 9.1')

    def test_example_label_should_be_p1_actionable(self):
        # Example label should be P1 label issue
        text = "Example 4.3 Khảo sát mẫu"
        html = f'<p>{text}</p>'
        tag = BeautifulSoup(html, 'html.parser').p
        res = check_text_residue_v3(tag, text)
        self.assertEqual(res['status'], 'label_issue')
        self.assertEqual(res['severity'], 'P1')
        self.assertEqual(res['current_label'], 'Example 4.3')
        self.assertEqual(res['expected_label'], 'Ví dụ 4.3')

    def test_full_english_caption_should_be_p0(self):
        # Full English caption containing Table label should be P0 prose issue
        text = "Table 12.3 Table showing the scores on the final exam based on scores from the third exam."
        html = f'<p>{text}</p>'
        tag = BeautifulSoup(html, 'html.parser').p
        res = check_text_residue_v3(tag, text)
        self.assertEqual(res['status'], 'issue')
        self.assertEqual(res['severity'], 'P0')
        self.assertEqual(res['issue_type'], 'LABEL_LOCALIZATION_MISSING')

    def test_hidden_english_table_label_should_not_be_actionable(self):
        # Table label in eng hidden block should be ignored
        html = '<div class="eng hidden">Table 11.18 Academic achievement</div>'
        tag = BeautifulSoup(html, 'html.parser').div
        res = check_text_residue_v3(tag, "Table 11.18 Academic achievement")
        self.assertEqual(res['status'], 'ignored')
        self.assertEqual(res['category'], 'hidden_english')

    def test_bibliographic_title_containing_table_should_not_be_actionable(self):
        # Reference/bibliography should be P2 manual review, not P0/P1
        text = "Table of Critical Values for the Chi-Square Distribution"
        html = '<p class="reference">Table of Critical Values for the Chi-Square Distribution</p>'
        tag = BeautifulSoup(html, 'html.parser').p
        res = check_text_residue_v3(tag, text)
        self.assertEqual(res['status'], 'review')
        self.assertEqual(res['severity'], 'P2')

    def test_table_inside_attributes_should_not_be_actionable(self):
        # Check that table text inside tag attributes isn't checked as text
        html = '<a href="table_11_18" id="table-11-18">Xem bảng</a>'
        tag = BeautifulSoup(html, 'html.parser').a
        res = check_text_residue_v3(tag, "Xem bảng")
        self.assertEqual(res['status'], 'ignored')

if __name__ == "__main__":
    unittest.main()
