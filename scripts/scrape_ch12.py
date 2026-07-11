import os
import requests
from pathlib import Path

urls = [
    "https://openstax.org/books/introductory-statistics-2e/pages/12-introduction",
    "https://openstax.org/books/introductory-statistics-2e/pages/12-1-linear-equations",
    "https://openstax.org/books/introductory-statistics-2e/pages/12-2-scatter-plots",
    "https://openstax.org/books/introductory-statistics-2e/pages/12-3-the-regression-equation",
    "https://openstax.org/books/introductory-statistics-2e/pages/12-4-testing-the-significance-of-the-correlation-coefficient",
    "https://openstax.org/books/introductory-statistics-2e/pages/12-5-prediction",
    "https://openstax.org/books/introductory-statistics-2e/pages/12-6-outliers",
    "https://openstax.org/books/introductory-statistics-2e/pages/12-7-regression-distance-from-school",
    "https://openstax.org/books/introductory-statistics-2e/pages/12-8-regression-textbook-cost",
    "https://openstax.org/books/introductory-statistics-2e/pages/12-9-regression-fuel-efficiency",
    "https://openstax.org/books/introductory-statistics-2e/pages/12-key-terms",
    "https://openstax.org/books/introductory-statistics-2e/pages/12-chapter-review",
    "https://openstax.org/books/introductory-statistics-2e/pages/12-formula-review",
    "https://openstax.org/books/introductory-statistics-2e/pages/12-practice",
    "https://openstax.org/books/introductory-statistics-2e/pages/12-homework",
    "https://openstax.org/books/introductory-statistics-2e/pages/12-bringing-it-together-homework",
    "https://openstax.org/books/introductory-statistics-2e/pages/12-references",
    "https://openstax.org/books/introductory-statistics-2e/pages/12-solutions"
]

dest_dir = Path("D:/OPENSTAX/books/introductory-statistics-2e/chapter-12/01-raw")
dest_dir.mkdir(parents=True, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print(f"Scraping {len(urls)} pages for Chapter 12...")

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
