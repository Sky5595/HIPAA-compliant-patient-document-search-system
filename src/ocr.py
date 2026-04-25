"""
Document extraction pipeline.
Supports: native-text PDFs (pdfplumber), scanned PDFs (pytesseract),
          plain text (.txt), and Markdown (.md).
"""
from __future__ import annotations
import io
from pathlib import Path


def extract_text(filepath: str | Path) -> str:
    """
    Extract raw text from a document file.
    Tries native PDF extraction first; falls back to OCR for scanned docs.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf(path)
    elif suffix in (".txt", ".md", ".text"):
        return path.read_text(encoding="utf-8", errors="replace")
    elif suffix in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
        return _extract_image_ocr(path)
    else:
        # Best-effort decode for unknown formats
        return path.read_text(encoding="utf-8", errors="replace")


def _extract_pdf(path: Path) -> str:
    """Try pdfplumber first; fall back to pytesseract if text layer is absent."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        if text_parts:
            return "\n\n".join(text_parts)
    except ImportError:
        pass

    # Fallback: OCR each page
    return _pdf_ocr_fallback(path)


def _pdf_ocr_fallback(path: Path) -> str:
    """Convert PDF pages to images and OCR them with pytesseract."""
    try:
        from pdf2image import convert_from_path
        import pytesseract
        images = convert_from_path(str(path), dpi=300)
        return "\n\n".join(pytesseract.image_to_string(img) for img in images)
    except ImportError:
        raise RuntimeError(
            "OCR fallback requires: pip install pdf2image pytesseract\n"
            "And Tesseract installed: https://github.com/tesseract-ocr/tesseract"
        )


def _extract_image_ocr(path: Path) -> str:
    """OCR a standalone image file."""
    try:
        import pytesseract
        from PIL import Image
        return pytesseract.image_to_string(Image.open(str(path)))
    except ImportError:
        raise RuntimeError("pip install pytesseract Pillow")


def get_document_metadata(filepath: str | Path) -> dict:
    """Extract basic metadata without reading full content."""
    path = Path(filepath)
    stat = path.stat()
    return {
        "filename": path.name,
        "extension": path.suffix.lower(),
        "size_kb": round(stat.st_size / 1024, 1),
        "path": str(path),
    }
