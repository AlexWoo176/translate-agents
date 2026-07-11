# Libero Translation Pipeline

This document defines the 9 sequential stages of the Libero Translation Pipeline, detailing inputs, processes, and outputs for each step.

```text
[Scrape] ➔ [Cleanup] ➔ [Analyze] ➔ [Prep] ➔ [Translate] ➔ [Review] ➔ [Fix] ➔ [Archive] ➔ [Build]
```

---

## Pipeline Lifecycle Details

### 1. Scrape (`scrape`)
- **Inputs:** Base URL or page TOC from OpenStax, book configurations.
- **Process:** Traverses chapter links, fetches HTML contents including layout wrappers, styles, scripts, and captures original image assets.
- **Outputs:** Saves to `01-raw/` folder in the target book directory.

### 2. Cleanup (`cleanup`)
- **Inputs:** `01-raw/` HTML documents.
- **Process:** Parses the HTML, strips off boilerplate elements (navigation panels, sidebars, headers, footers, script files, inline styling blocks). Keeps only the core textbook document, rewriting image source links to local assets directory, converting files to standard UTF-8.
- **Outputs:** Saves sanitized HTML files to `02-clean/` and extracts images to the chapter's `assets/` folder.

### 3. Analyze (`analyze`)
- **Inputs:** `02-clean/` HTML documents.
- **Process:** 
  1. Terminology scanning: Detects terms formatted as `<span data-type="term">` and academic keywords to generate vocabulary candidates.
  2. Risk analysis: Analyzes complex sentences, cultural specifics (idioms, American context, baseball/sports jokes), and suggests guidelines.
- **Outputs:** Proposal glossary list (to be merged with root `glossary.csv`) and `03-analyzed/[section]-translate-analysis.md` guide.

### 4. Prep (`prep`)
- **Inputs:** `02-clean/` HTML documents.
- **Process:** Prepares the bilingual document schema. Duplicates structural nodes (such as paragraphs `<p>`, list items `<li>`, headers `<hN>`, tables, captions) and tags them as:
  - `class="eng hidden"`: Holds the original English content.
  - `class="vn visible"`: Holds a clone of the English text, designated to be replaced with Vietnamese translation.
  - Applies a `-vn` suffix strictly to container node IDs (e.g. `<p id="abc">` and `<p id="abc-vn">`).
- **Outputs:** Staged HTML templates written to `04-prep/`.

### 5. Translate (`translate`)
- **Inputs:** `04-prep/` HTML, root `glossary.csv`, cultural guide from `03-analyzed/`.
- **Process:** Calls the LLM to translate text inside `vn visible` tag containers, applying matching glossary definitions, maintaining correct style guidelines, and keeping all inline HTML children intact.
- **Outputs:** Completed bilingual documents in `05-translated/`.

### 6. Review (`review`)
- **Inputs:** `05-translated/` HTML, compared against `02-clean/` and root `glossary.csv`.
- **Process:** Automated tests (integrity and glossary checks) and LLM-assisted semantic review. Analyzes the translation for inaccuracies, tone deviation, grammatical issues, or missed terms, compiling a tabular log of discrepancies.
- **Outputs:** Review markdown files written to `06-reviews/` (e.g., `[section]-semantic-review-round-[N].md`).

### 7. Fix (`fix`)
- **Inputs:** `05-translated/` HTML and the selected `06-reviews/` review file.
- **Process:** Parsers scan the tables of review items, search the HTML source for matched text fragments, and patch the translation with correct reviewer fixes.
- **Outputs:** Modifies/updates HTML files directly in `05-translated/` (or generates a fresh patched version).

### 8. Archive (`archive`)
- **Inputs:** Verified `05-translated/` HTML files.
- **Process:** Compiles the translated pages:
  - For **Bilingual variant**: Preserves both `eng hidden` and `vn visible` classes.
  - For **VN-only variant**: Strips `eng hidden` tags, keeps only the Vietnamese content, and formats it as a clean readable webpage.
- **Outputs:** Writes outputs to `07-archive/bilingual/` and `07-archive/vn-only/`.

### 9. Build (`build`)
- **Inputs:** Combined book chapters in `07-archive/`, shared CSS.
- **Process:** Generates reader navigations, indexes, search indexes, and pack files to prepare contents for publication.
- **Outputs:** Output builds targeted for standard static website hosting or exporters.
