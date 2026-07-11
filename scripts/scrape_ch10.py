import os
import requests
from pathlib import Path

urls = [
    "https://openstax.org/books/introductory-statistics-2e/pages/10-introduction",
    "https://openstax.org/books/introductory-statistics-2e/pages/10-1-two-population-means-with-unknown-standard-deviations",
    "https://openstax.org/books/introductory-statistics-2e/pages/10-2-two-population-means-with-known-standard-deviations",
    "https://openstax.org/books/introductory-statistics-2e/pages/10-3-comparing-two-independent-population-proportions",
    "https://openstax.org/books/introductory-statistics-2e/pages/10-4-matched-or-paired-samples",
    "https://openstax.org/books/introductory-statistics-2e/pages/10-5-hypothesis-testing-for-two-means-and-two-proportions",
    "https://openstax.org/books/introductory-statistics-2e/pages/10-key-terms",
    "https://openstax.org/books/introductory-statistics-2e/pages/10-chapter-review",
    "https://openstax.org/books/introductory-statistics-2e/pages/10-formula-review",
    "https://openstax.org/books/introductory-statistics-2e/pages/10-practice",
    "https://openstax.org/books/introductory-statistics-2e/pages/10-homework",
    "https://openstax.org/books/introductory-statistics-2e/pages/10-references",
    "https://openstax.org/books/introductory-statistics-2e/pages/10-solutions"
]

dest_dir = Path("D:/OPENSTAX/books/introductory-statistics-2e/chapter-10/01-raw")
dest_dir.mkdir(parents=True, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print(f"Scraping {len(urls)} pages for Chapter 10...")

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
