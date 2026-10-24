"""
DataShuddi -- Streamlit Page 1: Live Monitor & Processing Pipeline.

Provides interactive document upload, live StateGraph execution, real-time telemetry,
and multi-format export functionality (Scrubbed Text, JSON Payload, Telemetry).
"""
import json
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from streamlit_app.ui_components import pipeline_visualization, render_file_info_card, status_badge


@st.cache_data(ttl=30)
def _count_files(directory: str) -> int:
    """Count files in a directory with a 30s cache to avoid repeated globs."""
    p = Path(directory)
    return len(list(p.glob("*"))) if p.exists() else 0


@st.cache_data(ttl=30)
def _count_queue_items(queue_path: str) -> int:
    """Count non-empty lines in the human review queue file."""
    p = Path(queue_path)
    if not p.exists():
        return 0
    with open(p, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


@st.cache_data(ttl=15)
def _get_staged_files() -> list[str]:
    """Retrieve list of staged documents from data/raw and tests/fixtures."""
    raw_files = list(Path("data/raw").glob("*")) if Path("data/raw").exists() else []
    fixture_files = list(Path("tests/fixtures").glob("*")) if Path("tests/fixtures").exists() else []

    all_paths = [str(f) for f in raw_files + fixture_files if f.is_file() and not f.name.startswith(".")]
    return sorted(all_paths)


def render() -> None:
    """Render Page 1: Live Document Processing Feed & Interactive Pipeline."""
    st.markdown("# ⚡ Live Processing Feed")
    st.caption("Ingest untrusted documents through the 8-node self-correcting PII scrubbing StateGraph.")

    # Top metrics row with cached directory scans.
    raw_count = _count_files("data/raw")
    clean_count = _count_files("data/clean")
    queue_count = _count_queue_items("data/human_review/queue.jsonl")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Raw Staged", str(raw_count))
    col2.metric("Scrubbed Clean", str(clean_count))
    delta_text = "Action required" if queue_count > 0 else None
    col3.metric("Human Review", str(queue_count), delta=delta_text, delta_color="inverse")
    col4.metric("Processed", str(st.session_state.get("processed_count", 0)))

    st.markdown("---")

    # Document Staging & File Selection Area
    st.markdown("### 📥 Document Staging & Inspection")

    staged_files = _get_staged_files()

    tab_staged, tab_upload, tab_manual = st.tabs([
        "📋 Select Staged File", "📁 Upload New File", "🔍 Manual Path Input"
    ])

    with tab_upload:
        uploaded_file = st.file_uploader(
            "Select document to scrub (PDF, DOCX, TXT):",
            type=["pdf", "docx", "txt"],
            help="Upload an untrusted document containing potential PII or headers/footers.",
        )
        if uploaded_file is not None:
            raw_dir = Path("data/raw")
            raw_dir.mkdir(parents=True, exist_ok=True)
            target_path = raw_dir / uploaded_file.name
            with open(target_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.session_state["active_staged_file"] = str(target_path)
            st.success(f"Successfully staged upload → `{target_path}`")

    with tab_staged:
        if staged_files:
            current_active = st.session_state.get("active_staged_file")
            default_index = staged_files.index(current_active) if current_active in staged_files else 0
            selected_staged = st.selectbox(
                "Select staged file from repository:",
                staged_files,
                index=default_index,
                key="staged_file_selectbox",
            )
            if selected_staged:
                st.session_state["active_staged_file"] = selected_staged
        else:
            st.info("No staged files found in `data/raw` or `tests/fixtures`. Upload a file in the next tab.")

    with tab_manual:
        manual_path_str = st.text_input(
            "Custom relative or absolute file path:",
            value="",
            placeholder="./data/raw/clean_sample.txt",
        )
        if manual_path_str:
            p = Path(manual_path_str)
            if p.exists() and p.is_file():
                st.session_state["active_staged_file"] = str(p)
            else:
                st.warning(f"File not found or invalid: `{manual_path_str}`")

    # Resolve active file path dynamically from session state
    input_file_path: Path | None = None
    active_path_str = st.session_state.get("active_staged_file")
    if active_path_str:
        p = Path(active_path_str)
        if p.exists() and p.is_file():
            input_file_path = p
    elif staged_files:
        input_file_path = Path(staged_files[0])
        st.session_state["active_staged_file"] = staged_files[0]

    # Display Metadata Card & Text Snippet Preview if a valid file is selected
    if input_file_path and input_file_path.exists():
        st.markdown(render_file_info_card(input_file_path), unsafe_allow_html=True)

        with st.expander("👁️ Document Content Preview (Snippet)", expanded=False):
            try:
                snippet_text = input_file_path.read_text(encoding="utf-8", errors="ignore")[:1000]
                st.code(snippet_text or "[Empty or Binary File]", language="text")
            except Exception as exc:
                st.caption(f"Unable to render text preview: {exc}")

    st.markdown("---")

    source_system = st.selectbox(
        "Source System Domain:",
        ["local", "hr_docs", "hr_salary", "hr_contracts", "legal", "medical", "general_reports", "confluence", "drive"],
        index=0,
        help="High-risk domains (hr_*, legal, medical) trigger Layer 2 Qwen3B contextual extraction.",
    )

    use_checkpointer = st.checkbox("Enable Postgres Checkpointer", value=False)

    # Dynamic pipeline visualization placeholder
    viz_placeholder = st.empty()
    viz_placeholder.markdown(pipeline_visualization(), unsafe_allow_html=True)

    if st.button("🚀 Process Document", type="primary", use_container_width=True):
        if not input_file_path or not input_file_path.exists():
            st.error("Please select or upload a valid document first.")
            return

        _run_pipeline(input_file_path, source_system, use_checkpointer, viz_placeholder)
    elif "last_result" in st.session_state and "last_input_file_path" in st.session_state:
        last_state = st.session_state["last_result"]
        last_path = Path(st.session_state["last_input_file_path"])
        completed_nodes = st.session_state.get("last_completed_nodes", [])
        error_node = "reflector" if last_state.get("needs_human_review") else ""
        viz_placeholder.markdown(
            pipeline_visualization(completed=completed_nodes, error_node=error_node),
            unsafe_allow_html=True,
        )
        _render_results(last_state, last_path)


def _run_pipeline(
    input_file_path: Path,
    source_system: str,
    use_checkpointer: bool,
    viz_placeholder: st.delta_generator.DeltaGenerator,
) -> None:
    """Execute the StateGraph pipeline with live node-by-node streaming visualization.

    Args:
        input_file_path: Path to the document to process.
        source_system: Source system domain classification.
        use_checkpointer: Whether to attach Postgres checkpointer.
        viz_placeholder: Streamlit placeholder for live pipeline visualization updates.
    """
    from src.agent.state import create_initial_state
    from src.utils.doc_utils import compute_doc_id, detect_mime_type

    with st.status("Executing 8-Node StateGraph Pipeline...", expanded=True) as status:
        st.write("Initializing document metadata & SHA-256 doc_id...")
        mime_type = detect_mime_type(input_file_path)
        doc_id = compute_doc_id(input_file_path)

        initial_state = create_initial_state(
            doc_id=doc_id,
            doc_path=str(input_file_path),
            source_system=source_system,
            mime_type=mime_type,
        )

        # Build graph
        st.write(f"Assembling graph (checkpointer={use_checkpointer})...")
        try:
            from src.agent.graph import build_graph
            graph = build_graph(use_checkpointer=use_checkpointer)
        except Exception as exc:
            status.update(label="❌ Graph Build Failed", state="error")
            st.error(f"Failed to build graph: {exc}")
            if use_checkpointer:
                st.info("💡 Try disabling the Postgres Checkpointer if Postgres is not running.")
            return

        st.write("Streaming execution across graph nodes...")
        final_state = dict(initial_state)
        completed_nodes: list[str] = []

        try:
            config = {"configurable": {"thread_id": doc_id}}
            for chunk in graph.stream(initial_state, config=config, stream_mode="updates"):
                for node_name, updated_fields in chunk.items():
                    completed_nodes.append(node_name)
                    final_state.update(updated_fields)

                    # Update live node visualization
                    viz_placeholder.markdown(
                        pipeline_visualization(active_node=node_name, completed=completed_nodes),
                        unsafe_allow_html=True,
                    )
                    st.write(f"✓ Node complete: `{node_name}`")

        except Exception as exc:
            status.update(label="❌ Pipeline Execution Failed", state="error")
            st.error(f"Pipeline error: {exc}")
            return

        if final_state.get("validation_passed", False):
            status.update(label="✅ Pipeline PASSED — Vector Upserted!", state="complete")
        elif final_state.get("needs_human_review", False):
            status.update(label="🚨 Escalated to Human Review Queue!", state="error")
        else:
            status.update(label="⚠️ Completed with Validation Errors", state="error")

    # Final pipeline visualization update
    error_node = "reflector" if final_state.get("needs_human_review") else ""
    viz_placeholder.markdown(
        pipeline_visualization(completed=completed_nodes, error_node=error_node),
        unsafe_allow_html=True,
    )

    # Persist result in session state
    st.session_state["last_result"] = final_state
    st.session_state["last_input_file_path"] = str(input_file_path)
    st.session_state["last_completed_nodes"] = completed_nodes
    st.session_state["processed_count"] = st.session_state.get("processed_count", 0) + 1

    # Save scrubbed document copy with standardized name
    if final_state.get("masked_text"):
        clean_dir = Path("data/clean")
        clean_dir.mkdir(parents=True, exist_ok=True)
        clean_out = clean_dir / f"clean_{doc_id}.txt"
        clean_out.write_text(final_state["masked_text"], encoding="utf-8")

    _render_results(final_state, input_file_path)


def _render_results(final_state: dict, input_file_path: Path) -> None:
    """Display pipeline execution results, charts, and export controls.

    Args:
        final_state: Final pipeline state dictionary.
        input_file_path: Original document path for export naming.
    """
    st.markdown("---")
    st.markdown("### 📊 Execution Results & Telemetry")

    r1, r2, r3, r4 = st.columns(4)
    passed = final_state.get("validation_passed", False)
    r1.metric("Validation", "PASSED" if passed else "FAILED")
    r2.metric("PII Masked", str(final_state.get("pii_count", 0)))
    r3.metric("Quality Score", f"{final_state.get('quality_score', 0.0):.2f}")
    r4.metric("Processing Time", f"{final_state.get('processing_time_ms', 0)} ms")

    # Security and validation alerts.
    for flag in final_state.get("security_flags", []):
        st.markdown(f"{status_badge('SECURITY', 'warn')} 🛡️ {flag}", unsafe_allow_html=True)

    for err in final_state.get("validation_errors", []):
        st.markdown(f"{status_badge('ERROR', 'fail')} {err}", unsafe_allow_html=True)

    # Visual Telemetry Charts (Node Latency & PII Distribution)
    st.markdown("#### 📈 Interactive Visualizations")
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.caption("⏱️ Node Execution Latency Breakdown (ms)")
        timestamps = final_state.get("node_timestamps", {})
        if len(timestamps) >= 2:
            sorted_nodes = sorted(timestamps.items(), key=lambda x: x[1])
            latencies = []
            for i in range(len(sorted_nodes)):
                n_name = sorted_nodes[i][0]
                prev_time = sorted_nodes[i-1][1] if i > 0 else final_state.get("_start_time", sorted_nodes[0][1])
                dur_ms = max(1.0, round((sorted_nodes[i][1] - prev_time) * 1000, 1))
                latencies.append({"Node": n_name, "Latency (ms)": dur_ms})

            df_latency = pd.DataFrame(latencies).set_index("Node")
            st.bar_chart(df_latency)
        else:
            st.info("Insufficient timestamp data for latency chart.")

    with col_chart2:
        st.caption("🏷️ Detected PII Entity Type Breakdown")
        pii_entities = final_state.get("pii_entities", [])
        if pii_entities:
            counts: dict[str, int] = {}
            for e in pii_entities:
                t = e.get("type", "UNKNOWN")
                counts[t] = counts.get(t, 0) + 1
            df_pii = pd.DataFrame(list(counts.items()), columns=["Entity Type", "Count"]).set_index("Entity Type")
            st.bar_chart(df_pii)
        else:
            st.info("No PII entities detected in document.")

    # Output preview
    st.markdown("### 📄 Masked Output Preview")
    masked_content = final_state.get("masked_text", "")
    st.text_area("Scrubbed Text:", value=masked_content, height=220, key="result_masked_output")

    # Interactive Node Deep-Dive Inspector Section
    st.markdown("#### 🔬 Node Deep-Dive Inspector")
    node_keys = ["security_sanitizer", "extractor", "hf_detector", "pii_detector", "pii_masker", "schema_validator", "reflector", "output_node"]
    selected_node = st.radio(
        "Select node to inspect internal state & payload:",
        node_keys,
        format_func=lambda x: {
            "security_sanitizer": "N0 Security",
            "extractor": "N1 Extractor",
            "hf_detector": "N2 H/F Detect",
            "pii_detector": "N3 PII Detect",
            "pii_masker": "N4 PII Mask",
            "schema_validator": "N5 Validator",
            "reflector": "N6 Reflector",
            "output_node": "N7 Output",
        }.get(x, x),
        horizontal=True,
        key="inspector_node_radio",
    )
    from streamlit_app.ui_components import render_node_inspector
    st.markdown(render_node_inspector(final_state, selected_node), unsafe_allow_html=True)

    # Timestamped export filenames.
    ts = time.strftime("%Y%m%d_%H%M%S")
    stem = input_file_path.stem

    e1, e2, e3 = st.columns(3)
    with e1:
        st.download_button(
            "📥 Scrubbed Text (.txt)",
            data=masked_content,
            file_name=f"{stem}_scrubbed_{ts}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with e2:
        payload = {
            "doc_id": final_state.get("doc_id"),
            "source_system": final_state.get("source_system"),
            "quality_score": final_state.get("quality_score"),
            "pii_count": final_state.get("pii_count"),
            "validation_passed": final_state.get("validation_passed"),
            "masked_text": masked_content,
            "pii_entities": final_state.get("pii_entities"),
        }
        st.download_button(
            "📥 Payload (.json)",
            data=json.dumps(payload, indent=2),
            file_name=f"{stem}_payload_{ts}.json",
            mime="application/json",
            use_container_width=True,
        )

    with e3:
        telemetry = {
            "doc_id": final_state.get("doc_id"),
            "node_timestamps": final_state.get("node_timestamps"),
            "processing_time_ms": final_state.get("processing_time_ms"),
            "retry_count": final_state.get("retry_count"),
            "needs_human_review": final_state.get("needs_human_review"),
        }
        st.download_button(
            "📥 Telemetry (.json)",
            data=json.dumps(telemetry, indent=2),
            file_name=f"{stem}_telemetry_{ts}.json",
            mime="application/json",
            use_container_width=True,
        )

