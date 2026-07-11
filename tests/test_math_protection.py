from bs4 import BeautifulSoup
from src.pipeline.translate.math_protection import (
    protect_math_and_formulas,
    restore_math_and_formulas,
    extract_protected_items,
    compare_protected_items,
    restore_math_from_source
)

def test_protect_math_tags():
    html = '<p>Some text with <math><mfrac><mn>1</mn><mn>2</mn></mfrac></math> and <span class="os-math-in-para">x + y</span> and <em>z</em>.</p>'
    protected, mapping = protect_math_and_formulas(html)
    
    assert "[[PROTECTED_TAG_0]]" in protected
    assert "[[PROTECTED_TAG_1]]" in protected
    assert "[[PROTECTED_TAG_2]]" in protected
    assert len(mapping) == 3
    
    assert mapping[0][1] == "<math><mfrac><mn>1</mn><mn>2</mn></mfrac></math>"
    assert mapping[1][1] == '<span class="os-math-in-para">x + y</span>'
    assert mapping[2][1] == "<em>z</em>"

def test_protect_text_patterns():
    html = '<p>The hypothesis is H0, which has mean μ < 5. Also p-value = 0.02. t-score is t = -2.34.</p>'
    protected, mapping = protect_math_and_formulas(html)
    
    # H0, μ < 5, p-value, t = -2.34 are expected to be protected
    # Let's see: H0, μ, p < 5, p-value, t = -2.34, etc.
    # Note: μ < 5 matches standard inequality pattern: \b[a-zA-ZμσαβχρηλθπΣ]\b\s*[\<\>\=≤≥≠±≈]\s*-?\d+(?:\.\d+)?
    # Wait, 'μ < 5' will match that regex! 't = -2.34' also matches it!
    # 'p-value' matches the statistical terms.
    assert len(mapping) >= 4
    
    restored = restore_math_and_formulas(protected, mapping)
    assert restored == html

def test_compare_and_heal():
    # Source block
    src = '<p class="eng hidden">The hypothesis <em>H<sub>0</sub></em> is μ < 5.</p>'
    # Translation block with minor corruption or translation of math
    trans = '<p class="vn visible">Giả thuyết <em>H<sub>0</sub></em> là μ < 5.</p>'
    # A corrupted translation block
    corrupted_trans = '<p class="vn visible">Giả thuyết H 0 là mu < 5.</p>'
    
    # Compare src and trans
    match, err = compare_protected_items(src, trans)
    assert match is True
    
    # Compare src and corrupted
    # Wait, the corrupted block might have a different number of protected items, or different contents
    match_corr, err_corr = compare_protected_items(src, corrupted_trans)
    # The counts or values should mismatch
    assert match_corr is False or "mismatch" in err_corr
    
    # Let's test healing
    # If the counts match but contents differ slightly:
    # Say we translated: 'μ < 5' -> 'mu < 5' (which doesn't match Greek letter pattern, count mismatch)
    # But if it translated: 'μ < 5' -> 'μ < 5,0' (which matches the inequality pattern, so count matches but text differs)
    src_h = '<p>The value is μ = 0.05.</p>'
    trans_h = BeautifulSoup('<p>Giá trị là μ = 0.05.</p>', 'html.parser')
    
    # Mutate to make it slightly different
    trans_h_corrupted = BeautifulSoup('<p>Giá trị là μ = 0,05.</p>', 'html.parser')
    
    heal_result = restore_math_from_source(src_h, trans_h_corrupted)
    assert "μ = 0.05" in str(heal_result)
