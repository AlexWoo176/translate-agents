import shutil
from pathlib import Path

def copy_reader_assets(output_dir: Path):
    """
    Copy reader JS, CSS, and templates to finalized preview output location.
    """
    reader_dst = output_dir / "book-reader"
    reader_dst.mkdir(parents=True, exist_ok=True)

    src_dir = Path(__file__).parent
    
    # Copy assets
    shutil.copy2(src_dir / "book-reader.js", reader_dst / "book-reader.js")
    shutil.copy2(src_dir / "book-reader.css", reader_dst / "book-reader.css")
    return True

def write_pages_js(output_dir: Path, pages: list):
    """
    Write page navigation manifest list.
    """
    pages_js_path = output_dir / "book-reader" / "book-pages.js"
    pages_js_path.parent.mkdir(parents=True, exist_ok=True)

    with open(pages_js_path, "w", encoding="utf-8") as f:
        f.write(f"window.BOOK_PAGES = {pages};")
    return True

def generate_root_index(output_dir: Path, first_page: str, book_title: str):
    """
    Render and write the entrypoint redirect index page.
    """
    src_dir = Path(__file__).parent
    template_path = src_dir / "templates" / "index.html"
    index_path = output_dir / "index.html"

    if template_path.is_file():
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        # Fallback inline template
        content = (
            "<!DOCTYPE html>\n"
            "<html>\n"
            "<head>\n"
            "    <meta charset=\"utf-8\">\n"
            "    <meta http-equiv=\"refresh\" content=\"0; url={{ first_page }}\" />\n"
            "</head>\n"
            "<body><p>Redirecting to <a href=\"{{ first_page }}\">Start Reading</a>...</p></body>\n"
            "</html>"
        )

    rendered = content.replace("{{ first_page }}", first_page).replace("{{ book_title }}", book_title)

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(rendered)
    return True
