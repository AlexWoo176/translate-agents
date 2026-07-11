import shutil
from pathlib import Path
from bs4 import BeautifulSoup
from src.utils.html_resources import (
    ensure_stylesheet_link,
    normalize_archive_image_paths,
    ensure_no_reader_css,
)

# Re-export ensure_stylesheet_link so existing importers don't break
__all__ = ["ensure_stylesheet_link", "normalize_archive_resources",
           "export_bilingual_html", "export_vn_only_html"]


def normalize_archive_resources(soup: BeautifulSoup) -> None:
    """
    Normalize CSS and image paths for archive stage HTML files.

    Applies:
    - Ensures meta charset is set to utf-8
    - Ensures one style.css link with href='../../../../css/style.css'
    - Removes book-reader.css links
    - Normalizes img[src] to ../../../assets/<filename>

    Idempotent: calling twice produces the same result.
    """
    from src.utils.html_encoding import ensure_meta_charset_utf8
    ensure_meta_charset_utf8(soup)
    ensure_stylesheet_link(soup, "../../../../css/style.css")
    normalize_archive_image_paths(soup)


def export_bilingual_html(source_path: Path, dest_path: Path) -> bool:
    """
    Copy the translated bilingual HTML file to target archive destination and normalize resources.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    with open(source_path, "r", encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")
    normalize_archive_resources(soup)

    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    return True


def export_vn_only_html(source_path: Path, dest_path: Path) -> bool:
    """
    Generate Vietnamese-only HTML by removing original English sections and debug styles,
    and normalize resources.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    with open(source_path, "r", encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")

    # Remove English hidden elements
    for eng_elem in soup.find_all(class_=lambda x: x and "eng" in x.split() and "hidden" in x.split()):
        eng_elem.decompose()

    # Clean up vn visible classes
    for vn_elem in soup.find_all(class_=lambda x: x and "vn" in x.split() and "visible" in x.split()):
        classes = vn_elem.get("class", [])
        if isinstance(classes, str):
            classes = classes.split()
        elif classes is None:
            classes = []

        remaining_classes = [c for c in classes if c not in ["vn", "visible"]]
        if remaining_classes:
            vn_elem["class"] = remaining_classes
        else:
            del vn_elem["class"]

    # Remove debug stylesheet block
    for style in soup.find_all("style"):
        if ".eng.hidden" in style.text or ".vn.visible" in style.text:
            style.decompose()

    # Normalize resource paths and stylesheet links
    normalize_archive_resources(soup)

    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    return True
