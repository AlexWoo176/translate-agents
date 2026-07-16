import os
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from src.core.paths import get_book_root, get_chapter_root

def scrape_chapter(book_slug: str, chapter: str, start_url: str = None, force: bool = False) -> dict:
    """
    Recursively scrapes HTML pages of a chapter from OpenStax using next-link crawler.
    Saves raw files into chapter-{chapter}/01-raw/ under the book workspace directory.
    """
    raw_dir = get_chapter_root(book_slug, chapter) / "01-raw"
    os.makedirs(raw_dir, exist_ok=True)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    if not start_url:
        # Default start URL pattern for OpenStax
        start_url = f"https://openstax.org/books/{book_slug}/pages/{chapter}-introduction"
        print(f"No start URL provided, guessing: {start_url}")

    current_url = start_url
    processed = []
    skipped = []
    failed = []

    visited_urls = set()

    print(f"\nStarting crawler recursion from: {current_url}")
    while current_url:
        url_normalized = current_url.split('?')[0].rstrip('/')
        if url_normalized in visited_urls:
            print(f"Loop detected at {current_url}, stopping.")
            break
        visited_urls.add(url_normalized)

        slug = url_normalized.split("/")[-1]
        if not slug:
            print(f"Invalid slug parsed from URL: {current_url}, stopping.")
            break

        file_name = f"{slug}.html"
        out_file = raw_dir / file_name

        # If already exists and not forcing, skip downloading but still parse next-link for traversal
        is_skipped = out_file.is_file() and not force

        try:
            if is_skipped:
                print(f"Reading local cache for traversal: {file_name}")
                with open(out_file, "r", encoding="utf-8") as f:
                    content = f.read()
                skipped.append(file_name)
            else:
                print(f"Downloading: {current_url}")
                r = requests.get(current_url, headers=headers, timeout=20)
                r.raise_for_status()
                r.encoding = 'utf-8'
                content = r.text
                
                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(content)
                processed.append(file_name)
                time.sleep(1) # Gentle throttling

            soup = BeautifulSoup(content, 'html.parser')

            # Search for Next link
            next_slug = None
            candidate_links = []
            
            # OpenStax pages standard next page navigation link selectors
            for a in soup.find_all('a', href=True):
                href = a['href']
                # match relative or absolute books paths
                if href.startswith(f"/books/{book_slug}/pages/"):
                    cand_slug = href.split("/")[-1]
                    candidate_links.append((a.text.strip(), cand_slug))
                elif href.startswith(f"https://openstax.org/books/{book_slug}/pages/"):
                    cand_slug = href.split("/")[-1]
                    candidate_links.append((a.text.strip(), cand_slug))
                elif not href.startswith("http") and "/" not in href and href != "":
                    # some pages have pure slug hrefs
                    candidate_links.append((a.text.strip(), href))

            for text, cand_slug in candidate_links:
                text_lower = text.lower()
                if 'next' in text_lower or 'tiếp' in text_lower:
                    next_slug = cand_slug
                    break

            if not next_slug:
                print(f"No next link found. Stopping traversal.")
                break

            # Bound checking: stop traversal if next page jumps out of chapter prefix bounds
            # For preface/appendices, we check prefix matches to avoid crawling all remaining parts
            if not next_slug.startswith(f"{chapter}-") and not chapter.isalpha():
                print(f"Next slug '{next_slug}' does not start with chapter prefix '{chapter}-'. Stopping.")
                break

            current_url = f"https://openstax.org/books/{book_slug}/pages/{next_slug}"

        except Exception as e:
            print(f"Error fetching page {current_url}: {e}")
            failed.append({"url": current_url, "error": str(e)})
            break

    return {
        "processed": processed,
        "skipped": skipped,
        "failed": failed
    }
