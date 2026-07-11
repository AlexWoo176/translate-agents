import os
from pathlib import Path
from src.core.paths import get_archive_dir
from src.exporters.html_exporter import export_bilingual_html, export_vn_only_html
from src.exporters.markdown_exporter import export_html_to_markdown
from src.exporters.pdf_exporter import export_html_to_pdf

def export_single_file(source_html: Path, book_slug: str, chapter, filename: str):
    """
    Export a single translated HTML file to bilingual and vn-only modes (HTML, Markdown, PDF).
    Returns a dictionary of export statuses.
    """
    bil_html_dir = get_archive_dir(book_slug, chapter, "bilingual", "html")
    bil_md_dir = get_archive_dir(book_slug, chapter, "bilingual", "md")
    bil_pdf_dir = get_archive_dir(book_slug, chapter, "bilingual", "pdf")

    vn_html_dir = get_archive_dir(book_slug, chapter, "vn-only", "html")
    vn_md_dir = get_archive_dir(book_slug, chapter, "vn-only", "md")
    vn_pdf_dir = get_archive_dir(book_slug, chapter, "vn-only", "pdf")

    status = {
        "bilingual": {"html": False, "md": False, "pdf": False},
        "vn-only": {"html": False, "md": False, "pdf": False}
    }

    # -- 1. Bilingual exports --
    # HTML
    bil_html_path = bil_html_dir / filename
    status["bilingual"]["html"] = export_bilingual_html(source_html, bil_html_path)

    # Markdown (from bilingual HTML)
    bil_md_path = bil_md_dir / filename.replace(".html", ".md")
    status["bilingual"]["md"] = export_html_to_markdown(bil_html_path, bil_md_path)

    # PDF (from bilingual HTML)
    bil_pdf_path = bil_pdf_dir / filename.replace(".html", ".pdf")
    status["bilingual"]["pdf"] = export_html_to_pdf(bil_html_path, bil_pdf_path)


    # -- 2. VN-only exports --
    # HTML
    vn_html_path = vn_html_dir / filename
    status["vn-only"]["html"] = export_vn_only_html(source_html, vn_html_path)

    # Markdown (from vn-only HTML)
    vn_md_path = vn_md_dir / filename.replace(".html", ".md")
    status["vn-only"]["md"] = export_html_to_markdown(vn_html_path, vn_md_path)

    # PDF (from vn-only HTML)
    vn_pdf_path = vn_pdf_dir / filename.replace(".html", ".pdf")
    status["vn-only"]["pdf"] = export_html_to_pdf(vn_html_path, vn_pdf_path)

    return status
