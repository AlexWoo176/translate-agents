# Resource Contract

This document defines the canonical CSS and asset path rules for every stage of the
translate-agents pipeline. All pipeline code and tests must comply with this contract.

---

## Overview

The workspace layout is:

```
D:\OPENSTAX\
├── translate-agents\     ← stateless engine repo (this repo)
├── books\
│   └── <book-slug>\      ← real book data (never inside translate-agents)
│       ├── css\
│       │   └── style.css
│       ├── chapter-N\
│       │   ├── 01-raw\
│       │   ├── 02-clean\
│       │   ├── 03-analyzed\
│       │   ├── 04-prep\
│       │   ├── 05-translated\
│       │   ├── 06-reviews\
│       │   ├── 07-archive\
│       │   │   ├── bilingual\html\
│       │   │   └── vn-only\html\
│       │   └── assets\
│       └── .html\         ← preview build output
│           ├── css\
│           ├── book-reader\
│           └── chapter-N\
│               ├── assets\
│               └── *.html
└── web-site\
    └── <book-slug>\       ← copy of .html for deployment
```

---

## Stage Definitions

### 1 · 01-raw

**Path:** `books/<book-slug>/chapter-N/01-raw/`

**Purpose:** Raw scrape/source artifact. Immutable reference copy.

| Property | Rule |
|---|---|
| CSS | **Must NOT receive injected style.css links** as part of any normal workflow |
| Images | Left as-is from original scrape |
| book-reader.css | **Forbidden** |
| Mutations | **Forbidden** by default (unless `--include-raw` is explicitly passed to apply-css) |

> [!CAUTION]
> Never modify 01-raw in automated pipelines. It is the canonical source truth.

---

### 2 · Working Folders

**Paths:**
- `books/<book-slug>/chapter-N/02-clean/`
- `books/<book-slug>/chapter-N/04-prep/`
- `books/<book-slug>/chapter-N/05-translated/`

**Purpose:** Human-reviewable working copies. Must be directly openable in a browser.

| Property | Rule |
|---|---|
| CSS link | `<link rel="stylesheet" href="../../css/style.css">` |
| Images | `src="../assets/<filename>"` (resolves to `chapter-N/assets/`) |
| book-reader.css | **Forbidden** |
| Duplicate style.css | **Forbidden** — must be idempotent |

**Rationale for `../../css/style.css`:**
Working HTML files are at `chapter-N/<phase>/filename.html`. To reach `<book-root>/css/`:
- `..` → `chapter-N/`
- `../..` → `<book-root>/`
- `../../css/style.css` → `<book-root>/css/style.css` ✓

**Image path rationale (`../assets/`):**
Working HTML files are at `chapter-N/<phase>/`. Assets live at `chapter-N/assets/`. So:
- `..` → `chapter-N/`
- `../assets/img.webp` → `chapter-N/assets/img.webp` ✓

---

### 3 · Archive Folders

**Paths:**
- `books/<book-slug>/chapter-N/07-archive/bilingual/html/`
- `books/<book-slug>/chapter-N/07-archive/vn-only/html/`

**Purpose:** Compiled, read-only archive of translated content.

| Property | Rule |
|---|---|
| CSS link | `<link rel="stylesheet" href="../../../../css/style.css">` |
| Images | `src="../../../assets/<filename>"` |
| book-reader.css | **Forbidden** |
| Duplicate style.css | **Forbidden** |

**Rationale for `../../../../css/style.css`:**
Archive HTML files are at `chapter-N/07-archive/<mode>/html/filename.html`. To reach `<book-root>/css/`:
- `..` → `html/`
- `../..` → `<mode>/` (e.g. bilingual)
- `../../..` → `07-archive/`
- `../../../..` → `chapter-N/`
- `../../../../..` → `<book-root>/`
- `../../../../css/style.css` ✓

**Image path rationale (`../../../assets/`):**
Archive HTML → `chapter-N/07-archive/<mode>/html/img.webp`. Assets at `chapter-N/assets/`:
- `../../../` → `chapter-N/`
- `../../../assets/img.webp` → `chapter-N/assets/img.webp` ✓

**Illegal archive image patterns:**
- `../assets/` ← too shallow
- `../../assets/` ← too shallow
- `assets/assets/` ← doubled prefix
- `../../../../../../assets/` ← too deep

---

### 4 · Preview Build Output

**Path:** `books/<book-slug>/.html/`

**Chapter HTML:** `books/<book-slug>/.html/chapter-N/*.html`

**Purpose:** Interactive, self-contained preview with book-reader UI. Rebuilt by `build_preview`.

| Property | Rule |
|---|---|
| CSS link | `<link rel="stylesheet" href="../css/style.css">` |
| CSS file | `books/<book-slug>/.html/css/style.css` must exist |
| book-reader.css | `<link rel="stylesheet" href="../book-reader/book-reader.css">` |
| book-reader.js | `<script src="../book-reader/book-reader.js">` |
| book-pages.js | `<script src="../book-reader/book-pages.js">` |
| Images | `src="assets/<filename>"` (bare, no relative prefix) |
| Asset dir | `books/<book-slug>/.html/chapter-N/assets/<filename>` must exist |
| Self-contained | **Must NOT** depend on paths outside `.html/` for images |
| Idempotent | Running build twice must produce identical output (no `assets/assets/`) |

---

### 5 · Web-Site Output

**Path:** `web-site/<book-slug>/`

**Chapter HTML:** `web-site/<book-slug>/chapter-N/*.html`

**Purpose:** Public deployment copy. Identical structure to preview build.

| Property | Rule |
|---|---|
| CSS link | `<link rel="stylesheet" href="../css/style.css">` |
| CSS file | `web-site/<book-slug>/css/style.css` must exist |
| book-reader.css | `<link rel="stylesheet" href="../book-reader/book-reader.css">` |
| Images | `src="assets/<filename>"` |
| Asset dir | `web-site/<book-slug>/chapter-N/assets/<filename>` must exist |
| Self-contained | **Must NOT** depend on paths outside `web-site/<book-slug>/` for images |

> [!NOTE]
> Web-site output is always generated by `build --copy-to-web`. It is a direct copy of the
> `.html` preview build. Never write to web-site output directly.

---

## Enforcement

### apply-css command

- Copies `style.css` template to `books/<book-slug>/css/style.css`
- With `--include-working --chapter N`: injects `../../css/style.css` into 02-clean, 04-prep, 05-translated
- With `--include-raw`: also injects into 01-raw (DANGEROUS — use only for manual experiments)
- **Never** injects book-reader.css
- **Idempotent**: running twice does not duplicate the CSS link

### archive command

- Exports translated HTML to `07-archive/bilingual/html/` and `07-archive/vn-only/html/`
- Normalizes CSS to `../../../../css/style.css`
- Normalizes image paths to `../../../assets/<filename>`
- Removes book-reader.css if present

### build command

- Reads from `07-archive/<mode>/html/`
- Normalizes all CSS and image paths for preview/web-site use
- Copies chapter assets to `.html/chapter-N/assets/`
- Injects book-reader UI (CSS, JS) — only at this stage

---

## Quick Reference

| Stage | CSS href | Image src | book-reader? |
|---|---|---|---|
| 01-raw | (not injected) | (as-is) | ✗ |
| 02-clean | `../../css/style.css` | `../assets/img.webp` | ✗ |
| 04-prep | `../../css/style.css` | `../assets/img.webp` | ✗ |
| 05-translated | `../../css/style.css` | `../assets/img.webp` | ✗ |
| 07-archive | `../../../../css/style.css` | `../../../assets/img.webp` | ✗ |
| .html/chapter-N/ | `../css/style.css` | `assets/img.webp` | ✅ |
| web-site/chapter-N/ | `../css/style.css` | `assets/img.webp` | ✅ |
