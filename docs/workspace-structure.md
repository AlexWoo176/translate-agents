# Libero Workspace Structure

To ensure scalability and clean separation of concerns, the target project structure is configured as a monorepo workspace.

```text
libero-workspace/
├── translate-agents/      # Stateless translation engine (CLI, Core, Pipeline, QA)
├── books/                 # Data directory housing all book content files
│   └── [book-slug]/       # e.g., entrepreneurship, physics, etc.
└── web-site/              # Frontend web application for presenting/reading books
```

---

## Workspace Projects

### 1. `translate-agents/` (Engine)
This folder holds the software codebase for orchestrating the translation lifecycle.
- **Role:** Pure computation, automation, AI agency, QA validation, and document formatting.
- **Constraints:**
  - Must not commit real book assets, raw htmls, translated chunks, or review outputs to git.
  - Must accept input-path and output-path specifications.
  - Must remain independent of any specific book's vocabulary or tasks.

### 2. `books/` (Data Store)
This folder serves as the localized storage database for book resources and translation state.
- **Role:** Content staging, progress records, glossary tracking, review rounds history.
- **Structure:** Contains sub-directories named after book slugs (e.g., `books/entrepreneurship`).
- **Constraints:**
  - Completely decoupled from the engine runtime code.
  - Houses the single source of truth files (like `glossary.csv`, book-level configs, tasks tracking).

### 3. `web-site/` (Presentation Layer)
This folder contains the web application code that serves the final translated books to the end users.
- **Role:** Dynamic book rendering, search index, interactive study aids, responsive reading experiences.
- **Structure:** Typically a Next.js or Vite-based frontend.
- **Constraints:**
  - Consumes compiled production HTML/JSON assets built from `books/[book-slug]/chapter-{N}/07-archive/`.

---

## Cross-Package Interaction

Pipeline commands are executed within `translate-agents`, targeting relative paths or configured environment variables for `books` and `web-site`.

For example, to run the cleanup phase on chapter 1 of `entrepreneurship`:
```bash
bun run libero cleanup --book ../books/entrepreneurship --chapter 1
```

Or to compile static build files directly into the website's public assets:
```bash
bun run libero build --book ../books/entrepreneurship --out ../web-site/public/books/entrepreneurship
```
