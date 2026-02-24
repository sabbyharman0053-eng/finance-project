from __future__ import annotations

from pathlib import Path


SUPPORTED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_text(path)
    if suffix in SUPPORTED_IMAGE_EXT:
        return _extract_image_text(path)
    raise ValueError(f"Unsupported file type: {path}")


def _extract_pdf_text(path: Path) -> str:
    import pdfplumber
    import pytesseract

    chunks: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            chunks.append(page_text)
    text = "\n".join(chunks).strip()
    if text:
        return text
    # If PDF text layer is absent, OCR rendered page images.
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            img = page.to_image(resolution=300).original
            chunks.append(pytesseract.image_to_string(img))
    return "\n".join(chunks)


def _extract_image_text(path: Path) -> str:
    import pytesseract
    from PIL import Image

    image = Image.open(path)
    return pytesseract.image_to_string(image)
