# Book Structure Specification

Each textbook directory under `books/<book-slug>/` contains the source material, intermediate translation files, review assets, and compiled outputs for a specific book. This structure follows the **Data Versioning Principle**, ensuring that output files from any stage are kept separate from the inputs of that stage.

## Root Directory Structure

```text
books/[book-slug]/
├── config.json                     # Book-level metadata and configuration
├── glossary.csv                    # Single Source of Truth terminology mapping
├── tasks.md                        # Master project progress tracker
├── css/
│   └── style.css                   # Custom global styling sheet
├── _book-level/                    # Non-chapter segments (preface, index, appendix)
└── chapter-{N}/                    # Chapter folders (chapter-1, chapter-2, etc.)
```

---

## Chapter Directory Structure

Each chapter directory isolates the processing pipeline steps:

```text
chapter-{N}/
├── 01-raw/                         # Raw HTML crawled from OpenStax
├── 02-clean/                       # Sanitized HTML core (no head, menu, scripts, styles)
├── 03-analyzed/                    # Culture, grammatical, and risk analysis reports
├── 04-prep/                        # Structural bilingual template wrapper (pending translation)
├── 05-translated/                  # Translated bilingual HTML (eng hidden / vn visible)
├── 06-reviews/                     # Semantic review rounds markdown reports (HITL)
├── 07-archive/                     # Final output builds
│   ├── bilingual/                  # Final checked bilingual HTML files
│   └── vn-only/                    # Final Vietnamese-only HTML files
└── assets/                         # Chapter WebP and image files
```

---

## Standard Specifications of Key Files

### 1. `config.json`
Specifies configuration parameters used by the engine when scraping, cleaning, and translating:
```json
{
  "bookName": "Entrepreneurship",
  "bookSlug": "entrepreneurship",
  "sourceUrl": "https://openstax.org/books/entrepreneurship/pages/1-introduction",
  "languages": {
    "source": "en",
    "target": "vi"
  },
  "translationOptions": {
    "defaultTone": "inspiring",
    "pronouns": {
      "you": "Bạn",
      "we": "Chúng ta"
    }
  }
}
```

### 2. `glossary.csv`
Contains terminology definitions mapped to Vietnam equivalents.
Columns:
- `key`: English source term (exact spelling).
- `translation`: Finalized Vietnamese translation.
- `definition`: Explanation/Context of term.
- `status`: Lifecycle stage (e.g., `suggested`, `approved`).

### 3. `tasks.md`
Tracks progress across chapters. Checkpoints must match the pipelines:
- [x] Phase 1: Scrape & Clean
- [x] Phase 2: Term Extraction & Glossary Agreement
- [x] Phase 3: Cultural Risk Analysis
- [x] Phase 4: Bilingual Translation
- [x] Phase 5: QA Integrity & Review rounds
- [x] Phase 6: Compilation & Archiving
