import os
import requests
from pathlib import Path

urls = [
    "https://openstax.org/books/introductory-statistics-2e/pages/11-introduction",
    "https://openstax.org/books/introductory-statistics-2e/pages/11-1-facts-about-the-chi-square-distribution",
    "https://openstax.org/books/introductory-statistics-2e/pages/11-2-goodness-of-fit-test",
    "https://openstax.org/books/introductory-statistics-2e/pages/11-3-test-of-independence",
    "https://openstax.org/books/introductory-statistics-2e/pages/11-4-test-for-homogeneity",
    "https://openstax.org/books/introductory-statistics-2e/pages/11-5-comparison-of-the-chi-square-tests",
    "https://openstax.org/books/introductory-statistics-2e/pages/11-6-test-of-a-single-variance",
    "https://openstax.org/books/introductory-statistics-2e/pages/11-7-lab-1-chi-square-goodness-of-fit",
    "https://openstax.org/books/introductory-statistics-2e/pages/11-8-lab-2-chi-square-test-of-independence",
    "https://openstax.org/books/introductory-statistics-2e/pages/11-key-terms",
    "https://openstax.org/books/introductory-statistics-2e/pages/11-chapter-review",
    "https://openstax.org/books/introductory-statistics-2e/pages/11-formula-review",
    "https://openstax.org/books/introductory-statistics-2e/pages/11-practice",
    "https://openstax.org/books/introductory-statistics-2e/pages/11-homework",
    "https://openstax.org/books/introductory-statistics-2e/pages/11-bringing-it-together-homework",
    "https://openstax.org/books/introductory-statistics-2e/pages/11-references",
    "https://openstax.org/books/introductory-statistics-2e/pages/11-solutions"
]

dest_dir = Path("D:/OPENSTAX/books/introductory-statistics-2e/chapter-11/01-raw")
dest_dir.mkdir(parents=True, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print(f"Scraping {len(urls)} pages for Chapter 11...")

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
