from pathlib import Path

def export_html_to_pdf(html_path: Path, pdf_path: Path):
    """
    Attempt to convert HTML to PDF using available system PDF rendering engines:
    WeasyPrint -> pdfkit (wkhtmltopdf) -> xhtml2pdf.
    Fails gracefully if no engines are installed on the system.
    """
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Try WeasyPrint (resolves '../../../css/style.css' relative to html_path)
    try:
        import weasyprint
        weasyprint.HTML(str(html_path), base_url=str(html_path.parent)).write_pdf(str(pdf_path))
        return True
    except ImportError:
        pass
    except Exception as e:
        print(f"WeasyPrint failed: {e}")

    # 2. Try pdfkit
    try:
        import pdfkit
        pdfkit.from_file(str(html_path), str(pdf_path))
        return True
    except (ImportError, OSError):
        pass
    except Exception as e:
        print(f"pdfkit failed: {e}")

    # 3. Try xhtml2pdf
    try:
        from xhtml2pdf import pisa
        with open(html_path, "r", encoding="utf-8") as html_file:
            with open(pdf_path, "wb") as pdf_file:
                pisa_status = pisa.CreatePDF(html_file, dest=pdf_file)
        if pisa_status and not pisa_status.err:
            return True
    except ImportError:
        pass
    except Exception as e:
        print(f"xhtml2pdf failed: {e}")

    return False
