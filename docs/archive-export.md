# Archiving & Export Specifications

This document outlines the archival processes, output exports, and templating systems that transform translation chunks into user-ready textbooks.

---

## Archiving Formats

Once a chapter passes the QA gates, it is compiled into the `07-archive/` folder in two variants:

### 1. Bilingual Edition (`07-archive/bilingual/`)
- **Format:** HTML.
- **Structure:** Keeps both English source blocks (`eng hidden`) and Vietnamese translation blocks (`vn visible`).
- **Use Case:** Used for student review, side-by-side study, and ongoing development auditing.

### 2. Vietnamese-only Edition (`07-archive/vn-only/`)
- **Format:** HTML.
- **Structure:** Strips all `eng hidden` containers. Promotes `vn visible` contents by removing class restrictions or styling overrides.
- **Use Case:** Standard reading format, clean page layout.

---

## Exporters Architecture (`src/exporters/`)

The exporters package converts archived HTML pages into alternative file formats. Each exporter follows a standard signature defined by `src/core/exporter-interface`:

```javascript
class Exporter {
  async export(bookDir, chapterNum, outputPath) {
    // Override in subclass
  }
}
```

### 1. Word Document Exporter (`export-docx.js`)
- **Engine:** Converts HTML elements to Office Open XML fragments.
- **Styles:** Maps HTML tags (`<h1>`, `<p>`, `<blockquote>`, `<table>`) to corresponding Word styling structures defined in a document template.
- **Use Case:** Creating draft versions for off-line editing and printing.

### 2. E-Book Exporter (`export-epub.js`)
- **Engine:** Packages HTML pages, assets, styling files, navigation documents into a standard EPUB zip container.
- **Metadata:** Extracts configuration details (author, publication dates, languages, chapters metadata) from the book's `config.json`.

### 3. PDF Exporter (`export-pdf.js`)
- **Engine:** Uses headless browser printing commands or PDF generation libraries (e.g. Puppeteer/Weasyprint) to convert styled HTML to print-ready PDF.

---

## Reader Templates (`src/reader/templates/`)

To support web publication, Libero uses simple HTML/JS templates to render the book reader interface:

### Elements:
- **Layout Template (`layout.html`):** The primary container rendering sidebar navigations, responsive layouts, theme toggles (dark/light/sepia mode), font controls.
- **Navigation Generator:** Dynamically reads chapter structures and builds cross-chapter menus.
- **Glossary Page Template (`glossary.html`):** Compiles definitions from `glossary.csv` into an interactive search page.
- **Search Index Template:** Creates localized client-side search indexes based on text contents.
