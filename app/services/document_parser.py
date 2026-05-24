from pathlib import Path


def extract_text_from_upload(filename: str, content: bytes) -> str | None:
    """Safe document parsing foundation.

    Text extraction is intentionally conservative for Railway. TXT/CSV are parsed now.
    PDF/DOCX OCR can be enabled later with pypdf/python-docx/OCR workers without breaking upload flow.
    """
    ext = Path(filename or "").suffix.lower()
    if ext in {".txt", ".csv"}:
        return content.decode("utf-8", errors="ignore")[:50000]
    return None
