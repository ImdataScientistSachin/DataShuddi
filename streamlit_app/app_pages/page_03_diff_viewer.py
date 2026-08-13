"""
DataShuddi -- Streamlit Page 3: Dynamic Before/After Diff Viewer.

Renders interactive side-by-side comparison between raw unscrubbed documents
and PII-anonymized output. Caches detection results to avoid re-running
Presidio on every widget interaction.
"""
import hashlib
from pathlib import Path

import streamlit as st

from streamlit_app.ui_components import diff_line, status_badge


@st.cache_data(show_spinner="Running PII detection...")
def _run_diff_detection(file_hash: str, raw_text: str) -> dict:
    """Run PII detection and masking on raw text, cached by file hash.

    Args:
        file_hash: SHA-256 hash of the file content for cache keying.
        raw_text: Raw document text to analyze.

    Returns:
        Dict with masked_text, pii_count, and pii_entities.
    """
    from src.agent.nodes.pii_detector import pii_detector_node
    from src.agent.nodes.pii_masker import pii_masker_node
    from src.agent.state import create_initial_state

    state = create_initial_state(
        doc_id=f"diff_{file_hash[:16]}",
        doc_path="",
        source_system="local",
        mime_type="text/plain",
        raw_text=raw_text,
        pages=[raw_text],
    )
    state["cleaned_text"] = raw_text
    state["is_sanitized"] = True

    det_state = pii_detector_node(state)
    mask_state = pii_masker_node(det_state)

    return {
        "masked_text": mask_state.get("masked_text", ""),
        "pii_count": mask_state.get("pii_count", 0),
        "pii_entities": mask_state.get("pii_entities", []),
    }


def render() -> None:
    """Render Page 3: Side-by-Side Content Diff Viewer & Export."""
    st.markdown("# 🔍 Before/After Diff Viewer")
    st.caption("Compare raw extracted text vs. anonymized & scrubbed output side-by-side.")

    raw_dir = Path("data/raw")
    raw_files = sorted([f for f in raw_dir.glob("*") if f.is_file() and f.suffix.lower() in (".txt", ".pdf", ".docx") and not f.name.startswith(".")]) if raw_dir.exists() else []

    if not raw_files:
        st.info("📁 No document files (`.pdf`, `.docx`, `.txt`) found in `data/raw/`. Upload a document via the Live Monitor first.")
        return

    file_options = [str(f) for f in raw_files]
    selected_file_str = st.selectbox("Select document to inspect:", file_options)
    selected_path = Path(selected_file_str)

    if not selected_path.exists():
        st.warning(f"File not found: `{selected_file_str}`")
        return

    # Extract or read raw text

    if selected_path.suffix.lower() == ".pdf":
        try:
            import fitz
            doc = fitz.open(str(selected_path))
            raw_text = "\n".join([page.get_text("text") for page in doc])
            doc.close()
        except Exception as exc:
            raw_text = f"Error extracting text from PDF: {exc}"
    elif selected_path.suffix.lower() in (".docx", ".doc"):
        try:
            from docx import Document
            d = Document(str(selected_path))
            raw_text = "\n".join([p.text for p in d.paragraphs if p.text.strip()])
        except Exception as exc:
            raw_text = f"Error extracting text from DOCX: {exc}"
    else:
        raw_text = selected_path.read_text(encoding="utf-8", errors="replace")

    # Run detection button
    if st.button("🔍 Run PII Detection & Diff Analysis", type="primary", use_container_width=True):
        file_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        result = _run_diff_detection(file_hash, raw_text)
        st.session_state["diff_result"] = result
        st.session_state["diff_raw_text"] = raw_text
        st.session_state["diff_file_path"] = selected_path

    # Display results from session state
    diff_result = st.session_state.get("diff_result")
    if diff_result is None or st.session_state.get("diff_file_path") != selected_path:
        st.info("👆 Select a file and click **Run PII Detection & Diff Analysis** to inspect.")
        return

    raw_text = st.session_state.get("diff_raw_text", "")
    masked_text = diff_result["masked_text"]
    pii_count = diff_result["pii_count"]
    pii_entities = diff_result["pii_entities"]

    # Summary badge
    variant = "pass" if pii_count > 0 else "info"
    st.markdown(
        f"{status_badge(f'{pii_count} PII ENTITIES MASKED', variant)}",
        unsafe_allow_html=True,
    )
    st.markdown("")

    # Tabbed Viewports: Text Diff | Visual PDF Redaction | Entity Breakdown
    tab_text, tab_visual, tab_entities = st.tabs([
        "🔍 Side-by-Side Text Diff", "📄 Visual PDF Redaction & Overlays", "📊 PII Entity Breakdown"
    ])

    with tab_text:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🔴 Original Raw Text")
            st.text_area("Raw Input", value=raw_text, height=320, key="diff_raw_area")

        with col2:
            st.markdown("### 🟢 Scrubbed Output")
            st.text_area("Masked Output", value=masked_text, height=320, key="diff_masked_area")

        # Line-level diff highlights
        raw_lines = raw_text.splitlines()
        masked_lines = masked_text.splitlines()
        changed_lines = []
        for i, (r, m) in enumerate(zip(raw_lines, masked_lines, strict=False)):
            if r != m:
                changed_lines.append((i + 1, r, m))

        if changed_lines:
            with st.expander(f"📝 Line-Level Changes ({len(changed_lines)} lines modified)", expanded=False):
                for line_num, original, masked in changed_lines[:50]:
                    st.markdown(f"**Line {line_num}:**")
                    st.markdown(diff_line(original, "removed"), unsafe_allow_html=True)
                    st.markdown(diff_line(masked, "added"), unsafe_allow_html=True)
                    st.markdown("")

    with tab_visual:
        if selected_path.suffix.lower() == ".pdf":
            from streamlit_app.ui_components import generate_sanitized_pdf, render_pdf_page_highlights

            vcol1, vcol2 = st.columns([1, 3])
            with vcol1:
                page_idx = st.number_input("Page Number:", min_value=1, max_value=50, value=1) - 1
                zoom_factor = st.slider("Zoom Level:", min_value=1.0, max_value=3.0, value=2.0, step=0.5)

            with vcol2:
                pil_img, total_pages = render_pdf_page_highlights(
                    file_path=selected_path,
                    pii_entities=pii_entities,
                    hf_lines=[],
                    page_num=page_idx,
                    zoom=zoom_factor,
                )
                if pil_img:
                    st.caption(f"Page {page_idx + 1} of {total_pages} — 🔴 Red Highlights = Detected PII Entities")
                    st.image(pil_img, use_container_width=True)
                else:
                    st.warning("Unable to render visual PDF highlights for this file.")
        else:
            st.info("ℹ️ Visual PDF bounding-box rendering is available for `.pdf` files. Target document is non-PDF.")

    with tab_entities:
        if pii_entities:
            all_types = ["ALL"] + sorted({e.get("type", "UNKNOWN") for e in pii_entities})
            selected_type = st.selectbox("Filter by Entity Type:", all_types, index=0)

            filtered_entities = pii_entities if selected_type == "ALL" else [e for e in pii_entities if e.get("type") == selected_type]

            import pandas as pd
            df_ent = pd.DataFrame(filtered_entities)
            st.dataframe(df_ent, use_container_width=True)
        else:
            st.info("No PII entities detected in this document.")

    # Export controls
    st.markdown("---")
    st.markdown("### 📥 Export Options")
    e1, e2, e3 = st.columns(3)

    with e1:
        st.download_button(
            "📥 Scrubbed Document (.txt)",
            data=masked_text,
            file_name=f"{selected_path.stem}_scrubbed.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with e2:
        combined = (
            f"=== ORIGINAL RAW DOCUMENT ===\n{raw_text}\n\n"
            f"=== SCRUBBED OUTPUT ({pii_count} ENTITIES MASKED) ===\n{masked_text}\n"
        )
        st.download_button(
            "📥 Full Diff Report (.txt)",
            data=combined,
            file_name=f"{selected_path.stem}_diff_report.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with e3:
        if selected_path.suffix.lower() == ".pdf":
            from streamlit_app.ui_components import generate_sanitized_pdf
            temp_redacted_pdf = Path("data/clean") / f"{selected_path.stem}_redacted.pdf"
            ok = generate_sanitized_pdf(selected_path, temp_redacted_pdf, pii_entities=pii_entities)
            if ok and temp_redacted_pdf.exists():
                pdf_bytes = temp_redacted_pdf.read_bytes()
                st.download_button(
                    "📥 Redacted PDF (.pdf)",
                    data=pdf_bytes,
                    file_name=f"{selected_path.stem}_redacted.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.caption("PDF Redaction unavailable for non-PDF file.")
        else:
            st.caption("PDF Redaction unavailable for non-PDF file.")

