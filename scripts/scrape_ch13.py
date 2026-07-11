import os
import requests
from pathlib import Path

urls = [
    "https://openstax.org/books/introductory-statistics-2e/pages/13-introduction",
    "https://openstax.org/books/introductory-statistics-2e/pages/13-1-one-way-anova",
    "https://openstax.org/books/introductory-statistics-2e/pages/13-2-the-f-distribution-and-the-f-ratio",
    "https://openstax.org/books/introductory-statistics-2e/pages/13-3-facts-about-the-f-distribution",
    "https://openstax.org/books/introductory-statistics-2e/pages/13-4-test-of-two-variances",
    "https://openstax.org/books/introductory-statistics-2e/pages/13-5-lab-one-way-anova",
    "https://openstax.org/books/introductory-statistics-2e/pages/13-key-terms",
    "https://openstax.org/books/introductory-statistics-2e/pages/13-chapter-review",
    "https://openstax.org/books/introductory-statistics-2e/pages/13-formula-review",
    "https://openstax.org/books/introductory-statistics-2e/pages/13-practice",
    "https://openstax.org/books/introductory-statistics-2e/pages/13-homework",
    "https://openstax.org/books/introductory-statistics-2e/pages/13-references",
    "https://openstax.org/books/introductory-statistics-2e/pages/13-solutions"
]

dest_dir = Path("D:/OPENSTAX/books/introductory-statistics-2e/chapter-13/01-raw")
dest_dir.mkdir(parents=True, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, http) Chrome/120.0.0.0 Safari/537.36"
}

print(f"Scraping {len(urls)} pages for Chapter 13...")

for idx, url in enumerate(urls):
    filename = url.split("/")[-1] + ".html"
    filepath = dest_dir / filename
    print(f"[{idx+1}/{len(urls)}] Downloading {url} -> {filepath}...")
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(r.content)
        print(f"  Successfully saved {filename}")
    except Exception as e:
        print(f"  Error downloading {url}: {e}")

print("Scraping finished!")
