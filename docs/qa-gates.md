# Quality Assurance Gates (QA Gates)

Libero establishes three rigorous layers of validation to ensure translated outputs match academic publishing quality: **Structural Integrity Check**, **Glossary Consistency Checking**, and **Semantic Review Rounds**.

```text
[Bilingual HTML] ➔ [1. Structural Integrity Check] ➔ [2. Glossary Consistency Check] ➔ [3. Semantic Review Round] ➔ PASS
```

---

## 1. Structural Integrity Check (Automated)
This gate prevents syntax breakages, formatting layout drops, or lost content blocks when mapping raw HTML translations.

### Rules & Checks:
- **Element Parity Check:** Compares the sanitized source (`02-clean/`) with the bilingual target (`05-translated/`). The number of logical block tags (paragraphs `<p>`, tables `<table>`, list elements `<li>`, divisions `<div>`, headings `<hN>`) must match exactly.
- **Inline Tag Protection:** Ensures inline visual tags (such as `<strong>`, `<em>`, `<a>`, `<span>`) are preserved inside the translated `vn visible` container. 
- **DOM Hierarchy Integrity:** Validates that nested children structures are identical. No inline tags are stripped or combined.
- **ID Configuration Consistency:**
  - Suffix `-vn` must be applied only to parent container tag IDs (e.g., `<p id="intro-vn">`).
  - Child elements, glossary tags (like `<span data-type="term" id="term-1002">`), and layout markers **must not** receive a `-vn` suffix. Doing so breaks cross-referencing and glossary lookups.

---

## 2. Glossary Consistency Check (Automated)
Verifies that the translator agent strictly adhered to the single-source-of-truth vocabulary.

### Rules & Checks:
- **Term Extraction matching:** Scans translated text for terms defined in `<span data-type="term" id="...">` tags.
- **Translation Matching:** Verifies that the text within the tag is equivalent to the corresponding value in the `translation` column of `glossary.csv`.
- **Anomalies Report:** Flags any deviations, translation gaps, or outdated terminology usage.

---

## 3. Semantic Review Rounds (Human-in-the-Loop)
An interactive correction process using round-based feedback reports.

### Workflow:
1. **Report Generation:** A reviewer script matches bilingual translations, evaluates readability, checks tone, and generates a review report under `06-reviews/` named `[section]-semantic-review-round-[N].md`.
2. **Review Table Format:** Issue logs are structured as Markdown tables:
   | Original English | Current translation | Error Class | Suggested Revision | Status |
   | --- | --- | --- | --- | --- |
   | `Learn to bootstrap.` | `Học cách tự động.` | Terminology | `Học cách khởi nghiệp tự lực.` | `pending` |
3. **Approval:** A human editor reviews the suggestions, updates status flags to `accepted` or `rejected`, and updates the suggested revision text if needed.
4. **Patching Execution:** The CLI runs the fix module (`src/pipeline/fix`), scanning the table. It replaces the translation text inside `vn visible` blocks with the accepted revision text using exact substring matching.
5. **Dry-Run Enforcements:** The fix script must execute with a `--dry-run` validation flag first. It will abort and throw an error if any accepted row in the table cannot be mapped to the HTML text, ensuring zero corruptions occur.
