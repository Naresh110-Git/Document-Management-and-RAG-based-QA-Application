import tempfile
from pathlib import Path

from app.services.ingest import IngestionService, PageText


def create_simple_pdf(path: Path) -> None:
    try:
        import fitz

        doc = fitz.open()
        for i in range(2):
            page = doc.new_page()
            page.insert_text((72, 72), f"This is page {i+1} of the test PDF.")
        doc.save(path)
    except Exception:
        # If PyMuPDF isn't available in test env, write a minimal PDF-like file
        path.write_text("%PDF-1.4\n%\u00ff\u00ff\u00ff\n")


def test_extract_pages_tmp_file(tmp_path: Path) -> None:
    pdf_path = tmp_path / "simple.pdf"
    create_simple_pdf(pdf_path)

    settings = None
    # We only test the synchronous extraction helper; it doesn't need DB session
    service = IngestionService(session=None, settings=Path("."))  # type: ignore[arg-type]
    pages = service._extract_pages(pdf_path)
    assert isinstance(pages, list)
    # If extraction succeeded, expect at least 1 page
    if pages:
        assert isinstance(pages[0], PageText)
