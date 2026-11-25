"""
DataShuddi -- PDF Processing & Visual Redaction Utilities.

Provides headless PDF manipulation and visual black-bar redactions using PyMuPDF (fitz).
Decoupled from UI layers for clean use in REST API and worker microservices.
"""
from pathlib import Path
from typing import Any


def generate_sanitized_pdf(
    source_pdf: Path | str,
    output_pdf: Path | str,
    pii_entities: list[dict[str, Any]] | None = None,
    hf_lines: list[str] | None = None,
) -> bool:
    """Generate a visually redacted PDF file with black redaction bars using PyMuPDF.

    Args:
        source_pdf: Path to raw source PDF.
        output_pdf: Destination path for sanitized PDF.
        pii_entities: List of PII entity dictionaries.
        hf_lines: List of header/footer boilerplate lines.

    Returns:
        True if PDF redaction succeeded, False otherwise.
    """
    import fitz

    src = Path(source_pdf)
    out = Path(output_pdf)
    if not src.exists() or src.suffix.lower() != ".pdf":
        return False

    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        doc = fitz.open(str(src))

        for page in doc:
            if hf_lines:
                for line in hf_lines:
                    if len(line.strip()) > 3:
                        for rect in page.search_for(line.strip()):
                            page.add_redact_annot(rect, text="[HEADER_REDACTED]", fill=(0.1, 0.15, 0.25))

            if pii_entities:
                for ent in pii_entities:
                    snippet = ent.get("text", "")
                    ent_type = ent.get("type", "PII")
                    if snippet and len(snippet.strip()) > 1:
                        for rect in page.search_for(snippet):
                            page.add_redact_annot(rect, text=f"[{ent_type}_REDACTED]", fill=(0.05, 0.08, 0.15))

            page.apply_redactions()

        doc.save(str(out))
        doc.close()
        return True
    except Exception:
        return False
