"""
DataShuddi — Streamlit UI Component Library.

Reusable HTML/CSS components for the glassmorphic dashboard.
All components return raw HTML strings for st.markdown(unsafe_allow_html=True).
"""
import time
from pathlib import Path
from typing import Any


def load_css() -> str:
    """Load the custom CSS file and return it wrapped in a <style> tag."""
    css_path = Path(__file__).parent / "assets" / "styles.css"
    if css_path.exists():
        return f"<style>{css_path.read_text(encoding='utf-8')}</style>"
    return ""


def status_badge(text: str, variant: str = "info") -> str:
    """Render a colored status badge.

    Args:
        text: Badge label text.
        variant: One of 'pass', 'fail', 'warn', 'info'.

    Returns:
        HTML string for the badge.
    """
    return f'<span class="badge badge-{variant}">{text}</span>'


def pipeline_visualization(active_node: str = "", completed: list[str] | None = None, error_node: str = "") -> str:
    """Render the 8-node pipeline flow diagram.

    Args:
        active_node: Currently executing node name.
        completed: List of completed node names.
        error_node: Node that encountered an error.

    Returns:
        HTML string for the pipeline visualization.
    """
    completed = completed or []
    completed_lower = [c.lower() for c in completed]
    nodes = [
        ("N0", "Security", "security_sanitizer"),
        ("N1", "Extractor", "extractor"),
        ("N2", "H/F Detect", "hf_detector"),
        ("N3", "PII Detect", "pii_detector"),
        ("N4", "PII Mask", "pii_masker"),
        ("N5", "Validator", "schema_validator"),
        ("N6", "Reflector", "reflector"),
        ("N7", "Output", "output_node"),
    ]

    html_parts = ['<div class="pipeline-container">']
    for i, (node_id, label, key) in enumerate(nodes):
        css_class = "pipeline-node"
        if key == error_node or label.lower().replace(" ", "_").replace("/", "_") == error_node:
            css_class += " error"
        elif key == active_node or label.lower().replace(" ", "_").replace("/", "_") == active_node:
            css_class += " active"
        elif key in completed_lower or label.lower().replace(" ", "_").replace("/", "_") in completed_lower:
            css_class += " done"

        html_parts.append(f'<div class="{css_class}"><strong>{node_id}</strong><br>{label}</div>')
        if i < len(nodes) - 1:
            html_parts.append('<span class="pipeline-arrow">→</span>')

    html_parts.append("</div>")
    return "".join(html_parts)


def glass_card(content: str, title: str = "") -> str:
    """Render content inside a glassmorphic card.

    Args:
        content: HTML content for the card body.
        title: Optional card title.

    Returns:
        HTML string for the glass card.
    """
    title_html = f"<h3 style='margin-top:0;margin-bottom:0.6rem;'>{title}</h3>" if title else ""
    return f'<div class="glass-card">{title_html}{content}</div>'


def diff_line(text: str, kind: str = "added") -> str:
    """Render a single diff line with color coding.

    Args:
        text: Line text content.
        kind: 'added' or 'removed'.

    Returns:
        HTML string for the diff line.
    """
    css_class = "diff-added" if kind == "added" else "diff-removed"
    # Escape HTML in text content.
    safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<div class="{css_class}">{safe_text}</div>'


def app_footer(version: str = "3.0.0") -> str:
    """Render the application footer.

    Args:
        version: Application version string.

    Returns:
        HTML string for the footer.
    """
    return (
        f'<div class="app-footer">'
        f'🧹 DataShuddi v{version} · Enterprise PII Scrubbing Agent · '
        f'Local-First · GTX 1650 · Zero Cloud Cost'
        f'</div>'
    )


def pulse_indicator(label: str = "LIVE") -> str:
    """Render an animated pulse dot with label.

    Args:
        label: Text next to the pulse indicator.

    Returns:
        HTML string.
    """
    style = "color: var(--accent-teal); font-weight: 600; font-size: 0.85rem;"
    return (
        f'<span class="pulse-dot"></span>'
        f'<span style="{style}">{label}</span>'
    )


def render_file_info_card(file_path: Path) -> str:
    """Render a detailed glassmorphic metadata card for a selected or uploaded document.

    Args:
        file_path: Path to the target document.

    Returns:
        HTML string representing the file metadata card.
    """
    import datetime

    from src.utils.doc_utils import compute_doc_id, detect_mime_type

    if not file_path.exists():
        return glass_card(
            f"<p style='color: var(--accent-red); margin:0;'>⚠️ File not found at path: {file_path}</p>",
            title="File Status",
        )

    stat = file_path.stat()
    size_bytes = stat.st_size
    if size_bytes < 1024:
        size_str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes / 1024:.1f} KB"
    else:
        size_str = f"{size_bytes / (1024 * 1024):.2f} MB"

    mtime_str = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    mime_type = detect_mime_type(file_path)

    try:
        doc_id = compute_doc_id(file_path)
        hash_snippet = f"{doc_id[:16]}..."
    except Exception:
        hash_snippet = "N/A"

    line_count_str = ""
    if file_path.suffix.lower() == ".txt":
        try:
            line_count = len(file_path.read_text(encoding="utf-8", errors="ignore").splitlines())
            line_count_str = f" · Lines: <strong>{line_count}</strong>"
        except Exception:
            pass

    content = (
        f"<div style='display: flex; justify-content: space-between; align-items: center; "
        f"flex-wrap: wrap; gap: 0.5rem;'>"
        f"<div>"
        f"<strong>Path:</strong> <code>{file_path}</code><br>"
        f"<span style='color: var(--text-secondary); font-size: 0.85rem;'>"
        f"Type: <strong>{mime_type}</strong> · Size: <strong>{size_str}</strong>{line_count_str}<br>"
        f"SHA-256 Hash: <code>{hash_snippet}</code> · Modified: <strong>{mtime_str}</strong>"
        f"</span>"
        f"</div>"
        f"<div>{status_badge('READY FOR PROCESSING', 'pass')}</div>"
        f"</div>"
    )
    return glass_card(content, title="📄 Document Metadata")


def render_pdf_page_highlights(
    file_path: Path | str,
    pii_entities: list[dict] | None = None,
    hf_lines: list[str] | None = None,
    page_num: int = 0,
    zoom: float = 2.0,
) -> tuple[Any, int]:
    """Render a PDF page to a PIL Image with bounding-box highlights for PII & H/F boilerplate.

    Args:
        file_path: Path to the target PDF file.
        pii_entities: List of detected PII entity dictionaries.
        hf_lines: List of detected header/footer boilerplate lines.
        page_num: Page index (0-indexed).
        zoom: Rendering resolution zoom factor.

    Returns:
        Tuple of (PIL Image or None, total page count).
    """
    import fitz
    from PIL import Image, ImageDraw

    path = Path(file_path)
    if not path.exists() or path.suffix.lower() != ".pdf":
        return None, 0

    try:
        doc = fitz.open(str(path))
        total_pages = len(doc)
        if total_pages == 0:
            return None, 0
        if page_num < 0 or page_num >= total_pages:
            page_num = 0

        page = doc[page_num]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("RGBA")
        overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))

        draw = ImageDraw.Draw(overlay)

        # Highlight Header/Footer lines in semi-transparent Amber (255, 183, 3, 90)
        if hf_lines:
            for hf in hf_lines:
                if not hf or len(hf.strip()) < 3:
                    continue
                rects = page.search_for(hf.strip())
                for rect in rects:
                    scaled_rect = [rect.x0 * zoom, rect.y0 * zoom, rect.x1 * zoom, rect.y1 * zoom]
                    draw.rectangle(scaled_rect, fill=(255, 183, 3, 90), outline=(255, 183, 3, 200), width=2)

        # Highlight PII entities in semi-transparent Red (255, 77, 109, 110)
        if pii_entities:
            for ent in pii_entities:
                text_snippet = ent.get("text", "")
                if text_snippet and len(text_snippet.strip()) > 1:
                    rects = page.search_for(text_snippet)
                    for rect in rects:
                        scaled_rect = [rect.x0 * zoom, rect.y0 * zoom, rect.x1 * zoom, rect.y1 * zoom]
                        draw.rectangle(scaled_rect, fill=(255, 77, 109, 110), outline=(255, 77, 109, 230), width=2)

        doc.close()
        combined = Image.alpha_composite(img, overlay).convert("RGB")
        return combined, total_pages
    except Exception:
        return None, 0


def generate_sanitized_pdf(
    source_pdf: Path | str,
    output_pdf: Path | str,
    pii_entities: list[dict] | None = None,
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


def render_node_inspector(state: dict, selected_node: str = "security_sanitizer") -> str:
    """Render a detailed glassmorphic node inspector card for a selected node.

    Args:
        state: Current DataShuddiState dictionary.
        selected_node: Identifier string of the selected node.

    Returns:
        HTML string representing the node inspection report.
    """
    node_meta = {
        "security_sanitizer": ("N0 Security Sanitizer", "Pre-ingestion trust-boundary guard & prompt injection shield."),
        "extractor": ("N1 Extractor", "Multi-format text parser with PaddleOCR CPU fallback."),
        "hf_detector": ("N2 H/F Detector", "Page-split line frequency analysis & boilerplate removal."),
        "pii_detector": ("N3 Hybrid PII Detector", "Presidio deterministic NER + Qwen3B GPU contextual PII."),
        "pii_masker": ("N4 PII Masker", "Presidio Anonymizer token substitution."),
        "schema_validator": ("N5 Schema Validator", "Pydantic v2 EnterpriseDoc contract & residual PII scan."),
        "reflector": ("N6 Reflector Loop", "Qwen14b CPU critique, confidence gate & threshold tuning."),
        "output_node": ("N7 Output Node", "Strict payload allowlist filtering & Qdrant vector upsert."),
    }

    title, desc = node_meta.get(selected_node, (selected_node, "LangGraph Processing Node"))
    timestamps = state.get("node_timestamps", {})
    ts = timestamps.get(selected_node)
    ts_str = time.strftime("%H:%M:%S", time.localtime(ts)) if ts else "N/A"

    extra_details = ""
    if selected_node == "security_sanitizer":
        flags = state.get("security_flags", [])
        badge = status_badge(f"{len(flags)} INJECTIONS DETECTED", "warn") if flags else status_badge("CLEAN — NO THREATS", "pass")
        extra_details = f"<p>Security Flags: {badge}</p>"
        if flags:
            extra_details += "<ul>" + "".join([f"<li><code>{f}</code></li>" for f in flags]) + "</ul>"

    elif selected_node == "extractor":
        pages = state.get("_pages", [])
        char_count = len(state.get("raw_text", ""))
        extra_details = f"<p>Extracted Pages: <strong>{len(pages)}</strong> · Total Chars: <strong>{char_count}</strong></p>"

    elif selected_node == "hf_detector":
        candidates = state.get("header_footer_candidates", [])
        threshold = state.get("hf_threshold", 0.30)
        extra_details = f"<p>Current H/F Threshold: <code>{threshold:.2f}</code> · Removed Lines: <strong>{len(candidates)}</strong></p>"
        if candidates:
            extra_details += "<ul>" + "".join([f"<li><code>{c}</code></li>" for c in candidates[:5]]) + "</ul>"

    elif selected_node == "pii_detector":
        count = state.get("pii_count", 0)
        entities = state.get("pii_entities", [])
        types = list({e.get("type", "PII") for e in entities})
        extra_details = f"<p>Detected PII Count: <strong>{count}</strong> · Entity Types: <code>{', '.join(types) if types else 'None'}</code></p>"

    elif selected_node == "pii_masker":
        masked_len = len(state.get("masked_text", ""))
        extra_details = f"<p>Masked Content Length: <strong>{masked_len} chars</strong> · Status: {status_badge('ANONYMIZED', 'pass')}</p>"

    elif selected_node == "schema_validator":
        passed = state.get("validation_passed", False)
        score = state.get("quality_score", 0.0)
        errors = state.get("validation_errors", [])
        badge = status_badge("VALIDATION PASSED", "pass") if passed else status_badge("VALIDATION FAILED", "fail")
        extra_details = f"<p>Validation Status: {badge} · Quality Score: <strong>{score:.2f}</strong></p>"
        if errors:
            extra_details += "<ul style='color: var(--accent-red);'>" + "".join([f"<li>{e}</li>" for e in errors]) + "</ul>"

    elif selected_node == "reflector":
        retries = state.get("retry_count", 0)
        conf = state.get("reflector_confidence", 0.0)
        critique = state.get("reflection_text", "No reflection executed.")
        escalated = state.get("needs_human_review", False)
        esc_badge = status_badge("HUMAN ESCALATED", "fail") if escalated else status_badge("AUTO RETRY", "info")
        extra_details = f"<p>Retry Attempt: <strong>{retries}</strong> · Reflector Confidence: <code>{conf:.2f}</code> · Status: {esc_badge}<br>Critique: <em>{critique}</em></p>"

    elif selected_node == "output_node":
        ms = state.get("processing_time_ms", 0)
        extra_details = f"<p>Total Processing Time: <strong>{ms} ms</strong> · Vector Upsert: {status_badge('COMPLETED (QDRANT)', 'pass')}<br>Payload Allowed Keys: <code>doc_id, chunk_index, source_system, quality_score, hf_lines_removed, pii_scrubbed</code></p>"

    body = (
        f"<div style='margin-bottom: 0.5rem;'>"
        f"<span style='color: var(--text-secondary); font-size: 0.85rem;'>Execution Timestamp: {ts_str}</span>"
        f"<p style='color: var(--text-secondary); margin-top: 0.2rem;'>{desc}</p>"
        f"<hr style='border-color: var(--border-glass); margin: 0.8rem 0;'>"
        f"{extra_details}"
        f"</div>"
    )
    return glass_card(body, title=title)


def render_sidebar_header(logo_path: str = "streamlit_app/assets/datashuddi_logo.png", version: str = "3.0.0") -> str:
    """Render the high-resolution 3D Isometric Animated Shield Logo for the sidebar.

    Args:
        logo_path: Relative path to the high-resolution logo image asset.
        version: System version string.

    Returns:
        HTML string representing the animated 3D isometric branding card.
    """
    import base64

    p = Path(logo_path)
    b64_str = ""
    if p.exists():
        encoded = base64.b64encode(p.read_bytes()).decode("utf-8")
        b64_str = f"data:image/png;base64,{encoded}"

    img_tag = (
        f'<img src="{b64_str}" class="sidebar-3d-shield-logo" alt="DataShuddi 3D Shield Logo">'
        if b64_str
        else '<span style="font-size: 2.5rem;">🛡️</span>'
    )

    pulse = pulse_indicator("ENGINE ONLINE")
    return (
        f'<div class="sidebar-brand-card">'
        f'  <div class="sidebar-logo-wrapper">'
        f'    <div class="logo-orbit-ring ring-outer"></div>'
        f'    <div class="logo-orbit-ring ring-inner"></div>'
        f'    <div class="logo-ground-glow"></div>'
        f"    {img_tag}"
        f'    <div class="logo-shimmer-sweep"></div>'
        f'    <div class="sparkle-particle p1"></div>'
        f'    <div class="sparkle-particle p2"></div>'
        f'    <div class="sparkle-particle p3"></div>'
        f"  </div>"
        f'  <div class="sidebar-brand-title">DATASHUDDI</div>'
        f'  <div class="sidebar-subtitle">Enterprise PII Scrubbing Engine</div>'
        f'  <div class="sidebar-status-row">{pulse} <span class="version-tag">v{version}</span></div>'
        f"</div>"
    )


def render_hardware_widget() -> str:
    """Render the modernized hardware telemetry card for the sidebar.

    Returns:
        HTML string for the hardware widget.
    """
    return (
        '<div class="hardware-card">'
        '  <div class="hardware-card-header">'
        '    <span class="hardware-title">🔒 LOCAL STACK</span>'
        '    <span class="badge badge-pass">AIR-GAPPED</span>'
        '  </div>'
        '  <div class="hardware-stat-grid">'
        '    <div class="hw-stat-item"><span>🎮 GPU</span><strong>GTX 1650 (4GB)</strong></div>'
        '    <div class="hw-stat-item"><span>🧠 RAM</span><strong>16GB DDR4</strong></div>'
        '    <div class="hw-stat-item"><span>⚙️ Model</span><strong>Ollama / Qwen3B</strong></div>'
        "  </div>"
        "</div>"
    )


