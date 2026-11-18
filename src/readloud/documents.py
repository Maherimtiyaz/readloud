"""Load text out of the files people actually want read to them."""

from __future__ import annotations

from pathlib import Path

SUPPORTED = {".txt", ".md", ".pdf"}


def load_text(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        return _pdf_text(path)
    raise ValueError(f"unsupported file type {suffix!r}; supported: {sorted(SUPPORTED)}")


def _pdf_text(path: Path) -> str:
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        reader = PdfReader(path)
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
    except PyPdfError as e:
        raise ValueError(f"{path.name} is not a readable PDF ({e})") from e
    text = "\n\n".join(p for p in pages if p)
    if not text:
        # Scanned PDFs are images with no text layer. OCR is a Phase 2 feature.
        raise ValueError(f"{path.name} has no extractable text (scanned PDF? OCR comes later)")
    return text
