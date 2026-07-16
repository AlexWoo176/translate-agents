"""
html_resources.py — Centralized CSS and image resource helpers.

This module is the single source of truth for all HTML resource normalization and
validation. Every pipeline stage (apply-css, archive, build, verify-resources) must
import its helpers from here rather than duplicating logic.

Resource contract reference: docs/resource-contract.md

Stage CSS hrefs:
  working (02-clean, 04-prep, 05-translated)  : ../../css/style.css
  archive (07-archive/<mode>/html/)            : ../../../../css/style.css
  preview (.html/chapter-N/)                  : ../css/style.css
  web-site (web-site/<slug>/chapter-N/)       : ../css/style.css  (same as preview)

Stage image src:
  working                                     : ../assets/<filename>
  archive                                     : ../../../assets/<filename>
  preview / web-site                          : assets/<filename>  (bare, no leading ../)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup, Tag

# ---------------------------------------------------------------------------
# Helpers for resource validation skipping
# ---------------------------------------------------------------------------

def should_skip_resource_tag(tag: Tag) -> bool:
    """
    Skip resource tag if inside comment/script/style/code/pre/template or eng hidden.
    """
    curr = tag
    while curr and curr.name != '[document]':
        if curr.name in ('script', 'style', 'code', 'pre', 'template'):
            return True
        # Check if inside eng hidden
        classes = curr.get('class', [])
        classes_list = [classes] if isinstance(classes, str) else classes
        if 'eng' in classes_list and 'hidden' in classes_list:
            return True
        curr = curr.parent
    return False


# ---------------------------------------------------------------------------
# Stage constants — canonical CSS href for each stage
# ---------------------------------------------------------------------------

STAGE_CSS_HREF = {
    "working": "../../css/style.css",
    "archive": "../../../../css/style.css",
    "preview": "../css/style.css",
    "web":     "../css/style.css",
}

# Illegal image path patterns for each stage (used in validation)
ARCHIVE_IMG_PREFIX = "../../../assets/"
WORKING_IMG_PREFIX = "../assets/"
PREVIEW_IMG_PREFIX = "assets/"   # bare, no ../ allowed


# ===========================================================================
#  STYLESHEET HELPERS  (BeautifulSoup-based, mutate soup in-place)
# ===========================================================================

def ensure_stylesheet_link(soup: BeautifulSoup, href: str) -> None:
    """
    Ensure exactly one stylesheet link with the given href exists in <head>.

    Rules:
    - Removes any book-reader.css link.
    - If a style.css link already exists with a wrong href, updates it.
    - If no style.css link exists, appends a new one.
    - Idempotent: calling twice with the same href produces no change.
    """
    # Remove book-reader.css links
    for link in list(soup.find_all("link", rel="stylesheet")):
        h = link.get("href", "")
        if "book-reader.css" in h:
            link.decompose()

    # Find any existing style.css link
    style_link: Optional[Tag] = None
    for link in soup.find_all("link", rel="stylesheet"):
        if "style.css" in link.get("href", ""):
            style_link = link
            break

    if style_link is not None:
        style_link["href"] = href
    else:
        new_link = soup.new_tag("link", rel="stylesheet", href=href)
        if soup.head:
            soup.head.append(new_link)
        else:
            soup.append(new_link)


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


def normalize_stylesheet_links(soup: BeautifulSoup, expected_href: str) -> None:
    """
    Ensure exactly one stylesheet link with expected_href exists and there are no
    duplicates or wrong-path style.css links.

    - Removes book-reader.css links.
    - Normalises all style.css links to expected_href.
    - Removes any duplicate style.css links (keeps first).
    - Idempotent.
    """
    ensure_stylesheet_link(soup, expected_href)
    remove_duplicate_book_stylesheet_links(soup)


def remove_duplicate_book_stylesheet_links(soup: BeautifulSoup) -> None:
    """
    Remove duplicate style.css links, keeping only the first occurrence.
    Does not remove non-style.css links.
    """
    seen_style = False
    for link in list(soup.find_all("link", rel="stylesheet")):
        if "style.css" in link.get("href", ""):
            if seen_style:
                link.decompose()
            else:
                seen_style = True


def ensure_no_reader_css(soup: BeautifulSoup) -> None:
    """
    Remove all book-reader.css stylesheet links from the soup.
    Should be called for working and archive stages.
    """
    for link in list(soup.find_all("link", rel="stylesheet")):
        if "book-reader.css" in link.get("href", ""):
            link.decompose()


# ===========================================================================
#  IMAGE PATH HELPERS  (string/regex-based for performance)
# ===========================================================================

_rel_prefix_re = re.compile(r'(?:\.\./)+(assets/)')


def _norm_url_to_bare_assets(url: str) -> str:
    """Strip any leading ../ chains before assets/ leaving just assets/foo."""
    return _rel_prefix_re.sub(r'\1', url)


def _norm_url_to_archive_assets(url: str) -> str:
    """
    Normalize an image src to archive depth: ../../../assets/foo.
    Accepts bare (assets/foo), working (../assets/foo), or any other depth.
    """
    # Strip any relative prefix first
    stripped = _rel_prefix_re.sub(r'\1', url)
    if stripped.startswith("assets/"):
        return "../../../" + stripped
    return url  # not an assets/ URL — leave alone


def _norm_srcset(val: str, norm_fn) -> str:
    """
    Normalize all URL tokens in a srcset value (comma-separated url+descriptor pairs).
    Applies norm_fn to each URL token independently; preserves descriptors like 1x, 480w.
    """
    parts = val.split(',')
    out = []
    for part in parts:
        tokens = part.strip().split()
        if tokens:
            tokens[0] = norm_fn(tokens[0])
        out.append(' '.join(tokens))
    return ', '.join(out)


def normalize_preview_image_paths(html_str: str) -> str:
    """
    Normalize img[src], img[srcset], source[srcset] paths for preview/web-site output.

    Any leading ../ chains before assets/ are stripped leaving bare assets/<filename>.
    Idempotent: 'assets/foo.webp' → 'assets/foo.webp' (no change).
    Does NOT touch book-reader.js/CSS src attributes.
    """
    def _sub_src(m: re.Match) -> str:
        quote = m.group(1)
        val = m.group(2)
        return f'src={quote}{_norm_url_to_bare_assets(val)}{quote}'

    def _sub_srcset(m: re.Match) -> str:
        quote = m.group(1)
        val = m.group(2)
        return f'srcset={quote}{_norm_srcset(val, _norm_url_to_bare_assets)}{quote}'

    result = re.sub(r'src=(["\'])([^"\']*)\1', _sub_src, html_str)
    result = re.sub(r'srcset=(["\'])([^"\']*)\1', _sub_srcset, result)
    return result


def normalize_archive_image_paths(soup: BeautifulSoup) -> None:
    """
    Normalize img[src] in an archive soup so all assets/ references use ../../../assets/.
    Mutates soup in-place. Idempotent.
    """
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src:
            continue
        # Normalize any depth or bare path to ../../../assets/
        normalized = _norm_url_to_archive_assets(src)
        if normalized != src:
            img["src"] = normalized

    # Also handle source[srcset] in archive
    for source in soup.find_all("source"):
        srcset = source.get("srcset", "")
        if srcset:
            source["srcset"] = _norm_srcset(srcset, _norm_url_to_archive_assets)


def normalize_working_image_paths(soup: BeautifulSoup) -> None:
    """
    Normalize img[src] in a working-folder soup so all assets/ references use ../assets/.
    Mutates soup in-place. Idempotent.
    """
    prefix = "../assets/"
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src:
            continue
        # Strip any existing relative chain to bare assets/, then add ../
        stripped = _rel_prefix_re.sub(r'\1', src)
        if stripped.startswith("assets/"):
            img["src"] = "../" + stripped


# ===========================================================================
#  RESOURCE VALIDATION HELPERS
# ===========================================================================

def validate_stylesheet_links(html_file: Path, stage: str) -> dict:
    """
    Validate that the HTML file contains the correct style.css link for its stage.

    Returns: {"ok": bool, "errors": [str]}

    stage: one of "working", "archive", "preview", "web", "raw"
    """
    errors = []
    if not html_file.is_file():
        return {"ok": False, "errors": [f"File not found: {html_file}"]}

    expected_href = STAGE_CSS_HREF.get(stage)
    if expected_href is None:
        # "raw" — no requirement
        return {"ok": True, "errors": []}

    try:
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
        soup = BeautifulSoup(content, "html.parser")
    except Exception as e:
        return {"ok": False, "errors": [f"Parse error in {html_file}: {e}"]}

    style_links = [
        lnk for lnk in soup.find_all("link", rel="stylesheet")
        if "style.css" in lnk.get("href", "")
    ]

    if not style_links:
        errors.append(f"Missing style.css link (expected href='{expected_href}'): {html_file}")
    else:
        for lnk in style_links:
            if lnk.get("href") != expected_href:
                errors.append(
                    f"Wrong style.css href '{lnk.get('href')}' "
                    f"(expected '{expected_href}'): {html_file}"
                )

    return {"ok": len(errors) == 0, "errors": errors}


def validate_image_links(html_file: Path, assets_dir: Path) -> dict:
    """
    Validate that every img[src] in the HTML file resolves to an existing file
    under assets_dir. Only checks src values that start with 'assets/' (preview/web)
    or '../../../assets/' (archive).

    Returns: {"ok": bool, "errors": [str]}
    """
    errors = []
    if not html_file.is_file():
        return {"ok": False, "errors": [f"File not found: {html_file}"]}

    try:
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
        soup = BeautifulSoup(content, "html.parser")
    except Exception as e:
        return {"ok": False, "errors": [f"Parse error in {html_file}: {e}"]}

    for img in soup.find_all("img"):
        if should_skip_resource_tag(img):
            continue
        src = img.get("src", "")
        if not src:
            continue
        # Bare assets/ (preview)
        if src.startswith("assets/"):
            filename = src[len("assets/"):]
            target = assets_dir / filename
            if not target.is_file():
                errors.append(f"Missing image file '{target}': {html_file}")
        # Archive depth ../../../assets/
        elif src.startswith("../../../assets/"):
            filename = src[len("../../../assets/"):]
            target = assets_dir / filename
            if not target.is_file():
                errors.append(f"Missing image file '{target}': {html_file}")
        # Working depth ../assets/
        elif src.startswith("../assets/"):
            filename = src[len("../assets/"):]
            target = assets_dir / filename
            if not target.is_file():
                errors.append(f"Missing image file '{target}': {html_file}")

    return {"ok": len(errors) == 0, "errors": errors}


def validate_no_forbidden_css(html_file: Path, stage: str) -> dict:
    """
    Validate that the HTML file does not contain forbidden CSS for the given stage.

    - archive, working, raw: book-reader.css is forbidden
    - preview, web: book-reader.css is expected/allowed

    Also validates no garbage path patterns appear in any href.

    Returns: {"ok": bool, "errors": [str]}
    """
    errors = []
    if not html_file.is_file():
        return {"ok": False, "errors": [f"File not found: {html_file}"]}

    try:
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
        soup = BeautifulSoup(content, "html.parser")
    except Exception as e:
        return {"ok": False, "errors": [f"Parse error in {html_file}: {e}"]}

    # book-reader.css forbidden in working/archive/raw
    if stage in ("working", "archive", "raw"):
        for lnk in soup.find_all("link", rel="stylesheet"):
            if "book-reader.css" in lnk.get("href", ""):
                errors.append(
                    f"Forbidden book-reader.css found in stage '{stage}': {html_file}"
                )

    # Check for garbage path patterns
    garbage_patterns = [
        "assets/assets/",
        "css/css/",
        "../../../../../../assets/",
        "../../../../../../css/",
    ]
    for lnk in soup.find_all("link", href=True):
        for pat in garbage_patterns:
            if pat in lnk["href"]:
                errors.append(
                    f"Garbage path pattern '{pat}' in link href: {html_file}"
                )

    for img in soup.find_all("img", src=True):
        for pat in garbage_patterns:
            if pat in img["src"]:
                errors.append(
                    f"Garbage path pattern '{pat}' in img src: {html_file}"
                )

    return {"ok": len(errors) == 0, "errors": errors}


def validate_no_duplicate_stylesheets(html_file: Path) -> dict:
    """
    Validate that the HTML file does not contain duplicate style.css or
    book-reader.css links.

    Returns: {"ok": bool, "errors": [str]}
    """
    errors = []
    if not html_file.is_file():
        return {"ok": False, "errors": [f"File not found: {html_file}"]}

    try:
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
        soup = BeautifulSoup(content, "html.parser")
    except Exception as e:
        return {"ok": False, "errors": [f"Parse error in {html_file}: {e}"]}

    style_hrefs = [
        lnk.get("href", "")
        for lnk in soup.find_all("link", rel="stylesheet")
        if "style.css" in lnk.get("href", "")
    ]
    reader_hrefs = [
        lnk.get("href", "")
        for lnk in soup.find_all("link", rel="stylesheet")
        if "book-reader.css" in lnk.get("href", "")
    ]

    if len(style_hrefs) > 1:
        errors.append(
            f"Duplicate style.css links ({len(style_hrefs)} found): {html_file}"
        )
    if len(reader_hrefs) > 1:
        errors.append(
            f"Duplicate book-reader.css links ({len(reader_hrefs)} found): {html_file}"
        )

    return {"ok": len(errors) == 0, "errors": errors}


def validate_image_src_pattern(html_file: Path, stage: str) -> dict:
    """
    Validate that img[src] values match the expected pattern for the given stage.

    - archive: must use ../../../assets/
    - preview/web: must use assets/ (bare)
    - working: must use ../assets/
    - raw: no requirement

    Also detects wrong patterns (e.g. ../assets/ in archive, etc.)

    Returns: {"ok": bool, "errors": [str]}
    """
    errors = []
    if not html_file.is_file():
        return {"ok": False, "errors": [f"File not found: {html_file}"]}

    # Stage → expected prefix and illegal prefixes
    expected_prefixes = {
        "archive": "../../../assets/",
        "preview": "assets/",
        "web": "assets/",
        "working": "../assets/",
    }
    illegal_prefixes = {
        "archive": ["../assets/", "../../assets/", "assets/", "assets/assets/"],
        "preview": ["../assets/", "../../assets/", "../../../assets/", "assets/assets/"],
        "web": ["../assets/", "../../assets/", "../../../assets/", "assets/assets/"],
        "working": ["../../assets/", "../../../assets/", "assets/assets/"],
    }

    if stage == "raw":
        return {"ok": True, "errors": []}

    expected = expected_prefixes.get(stage)
    illegal = illegal_prefixes.get(stage, [])

    try:
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
        soup = BeautifulSoup(content, "html.parser")
    except Exception as e:
        return {"ok": False, "errors": [f"Parse error in {html_file}: {e}"]}

    for img in soup.find_all("img"):
        if should_skip_resource_tag(img):
            continue
        src = img.get("src", "")
        if not src or src.startswith("http://") or src.startswith("https://") or src.startswith("data:") or src.startswith("mailto:") or src.startswith("doi:") or src.startswith("#"):
            continue
        if "assets/" not in src:
            continue  # Not an assets reference, skip
        for bad in illegal:
            if src.startswith(bad):
                errors.append(
                    f"Wrong image path pattern '{src}' for stage '{stage}' "
                    f"(illegal prefix '{bad}'): {html_file}"
                )
                break

    return {"ok": len(errors) == 0, "errors": errors}
