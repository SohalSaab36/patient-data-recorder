"""Local OCR with graceful fallback when Tesseract/Poppler are missing."""

import os

from flask import current_app


def _tesseract_cmd():
    cmd = current_app.config.get("TESSERACT_CMD") or os.getenv("TESSERACT_CMD")
    if cmd:
        try:
            import pytesseract

            pytesseract.pytesseract.tesseract_cmd = cmd
        except ImportError:
            pass


def extract_text(filepath, mime_hint=""):
    _tesseract_cmd()
    ext = os.path.splitext(filepath)[1].lower()
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return None, "OCR libraries are not installed. File stored for manual review."

    try:
        if ext == ".pdf":
            try:
                from pdf2image import convert_from_path
            except ImportError:
                return None, "pdf2image is not installed. PDF stored for manual review."
            kwargs = {}
            poppler = current_app.config.get("POPPLER_PATH")
            if poppler:
                kwargs["poppler_path"] = poppler
            images = convert_from_path(filepath, dpi=200, **kwargs)
            chunks = [pytesseract.image_to_string(img) for img in images[:8]]
            text = "\n".join(chunks).strip()
        else:
            with Image.open(filepath) as img:
                text = pytesseract.image_to_string(img).strip()
    except Exception as exc:
        return None, f"OCR could not run ({exc.__class__.__name__}). File stored for manual review."

    if not text:
        return "", "OCR completed but no readable text was found. Needs manual review."
    return text, "OCR completed (prototype accuracy only)."
