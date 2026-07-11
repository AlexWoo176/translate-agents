from pathlib import Path
from bs4 import BeautifulSoup

def read_text_utf8(path: Path) -> str:
    """Read a text file with explicit UTF-8 encoding."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_text_utf8(path: Path, content: str) -> None:
    """Write text content to a file with explicit UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

def ensure_meta_charset_utf8(soup: BeautifulSoup) -> None:
    """
    Ensure that <meta charset="utf-8"> is the first element in <head> of the HTML.
    If <head> is missing, creates it and prepends it to <html> (or soup).
    """
    head = soup.find('head')
    if not head:
        html = soup.find('html')
        head = soup.new_tag('head')
        if html:
            html.insert(0, head)
        else:
            soup.insert(0, head)

    # Check if a meta charset element is already present
    meta_charset = head.find('meta', attrs={'charset': True})
    if meta_charset:
        meta_charset['charset'] = 'utf-8'
    else:
        new_meta = soup.new_tag('meta', charset='utf-8')
        head.insert(0, new_meta)

# Known mojibake tokens to detect
MOJIBAKE_TOKENS = [
    "Î¼",      # mu
    "Ï\x83",   # sigma
    "Ï",       # sigma (sometimes just Ï alone)
    "Î±",      # alpha
    "â‰¤",     # less-than-or-equal
    "â‰¥",     # greater-than-or-equal
    "â€™",     # apostrophe
    "â€—",     # dash
    "â€”",     # dash
    "Â¯",      # overline/macron
]

def has_mojibake(text: str) -> bool:
    """Return whether the text contains any known mojibake tokens."""
    for token in MOJIBAKE_TOKENS:
        if token in text:
            return True
    return False

def detect_mojibake_tokens(text: str) -> list[str]:
    """Return a list of specific mojibake sequences found in the text."""
    found = []
    for token in MOJIBAKE_TOKENS:
        if token in text:
            found.append(token)
    return found
