"""
DataShuddi -- Streamlit Page 5: Live Human Review Queue Inspector & Resolution.

Reads real JSON records from data/human_review/queue.jsonl, provides threshold
override controls, implements actual quarantine (atomic JSONL rewrite), and
exports escalation audit logs.
"""
import json
import time
from pathlib import Path

import streamlit as st

from streamlit_app.ui_components import status_badge


def _load_queue() -> list[dict]:
    """Load human review queue records from disk.

    Returns:
        List of queue record dicts.
    """
    queue_file = Path("data/human_review/queue.jsonl")
    records: list[dict] = []
    if not queue_file.exists():
        return records

    with open(queue_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line.strip()))
                except (json.JSONDecodeError, ValueError):
                    pass
    return records


def _remove_from_queue(doc_id: str) -> bool:
    """Atomically remove a record from the queue by rewriting the JSONL file.

    Args:
        doc_id: Document ID to remove.

    Returns:
        True if the record was found and removed.
    """
    queue_file = Path("data/human_review/queue.jsonl")
    if not queue_file.exists():
        return False

    records = _load_queue()
    filtered = [r for r in records if r.get("doc_id") != doc_id]

    if len(filtered) == len(records):
        return False

    # Atomic write: write to temp file then rename.
    tmp_file = queue_file.with_suffix(".tmp")
    with open(tmp_file, "w", encoding="utf-8") as f:
        for record in filtered:
            f.write(json.dumps(record) + "\n")
    tmp_file.replace(queue_file)

    return True


def render() -> None:
    """Render Page 5: Human Review Queue Inspector & Resolution Workstation."""
    st.markdown("# 🚨 Human Review Queue")
    st.caption("Inspect and resolve documents escalated due to retry exhaustion (≥3) or high PII density (>50).")

    records = _load_queue()

    if not records:
        st.info("🎉 Queue is empty — all documents passed validation.")
        st.markdown(
            status_badge("ALL CLEAR", "pass"),
            unsafe_allow_html=True,
        )
        return

    # Queue summary.
    st.markdown(f"### 📋 Escalated Queue ({len(records)} pending)")

    # Build table data.
    table_data = []
    for r in records[:50]:
        ts_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r.get("timestamp", time.time())))
        pii_count = r.get("pii_count", 0)
        retry_count = r.get("retry_count", 0)

        # Severity based on PII density and retries.
        if pii_count > 50 or retry_count >= 3:
            severity = "HIGH"
        elif pii_count > 20 or retry_count >= 2:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        table_data.append({
            "Doc ID": str(r.get("doc_id", "UNKNOWN"))[:24],
            "Source": r.get("source_system", "local"),
            "PII Count": pii_count,
            "Retries": retry_count,
            "Severity": severity,
            "Errors": "; ".join(r.get("validation_errors", []))[:80],
            "Timestamp": ts_str,
        })

    st.dataframe(table_data, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Action workstation.
    st.markdown("### 🛠️ Resolution Workstation")

    doc_ids = [r.get("doc_id", "UNKNOWN") for r in records]
    display_ids = [f"{did[:24]}..." for did in doc_ids]
    selected_idx = st.selectbox("Select document:", range(len(display_ids)), format_func=lambda i: display_ids[i])

    selected_record = records[selected_idx]
    selected_doc_id = selected_record.get("doc_id", "UNKNOWN")

    # Record details in expander.
    with st.expander("📄 Record Details", expanded=False):
        st.json(selected_record)

    override_threshold = st.slider(
        "Human Override H/F Threshold:",
        min_value=0.10,
        max_value=0.50,
        value=0.30,
        step=0.05,
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Approve & Reprocess", type="primary", use_container_width=True):
            doc_path = Path(selected_record.get("doc_path", ""))
            if not doc_path.exists():
                st.error(f"Source file not found at `{doc_path}`")
            else:
                _reprocess_document(selected_record, doc_path, override_threshold)

    with col2:
        # Confirmation before quarantine.
        if "confirm_quarantine" not in st.session_state:
            st.session_state["confirm_quarantine"] = None

        if st.session_state.get("confirm_quarantine") == selected_doc_id:
            st.warning(f"⚠️ Confirm quarantine of `{selected_doc_id[:16]}...`?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Yes, Quarantine", use_container_width=True):
                    removed = _remove_from_queue(selected_doc_id)
                    if removed:
                        st.success("✅ Document quarantined and removed from queue.")
                        st.session_state["confirm_quarantine"] = None
                        st.rerun()
                    else:
                        st.error("Failed to remove record from queue.")
            with c2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state["confirm_quarantine"] = None
                    st.rerun()
        else:
            if st.button("❌ Quarantine & Remove", use_container_width=True):
                st.session_state["confirm_quarantine"] = selected_doc_id
                st.rerun()

    # Export.
    st.markdown("---")
    st.markdown("### 📥 Export Queue Log")
    ts = time.strftime("%Y%m%d_%H%M%S")
    st.download_button(
        "📥 Export Audit Log (.json)",
        data=json.dumps(records, indent=2),
        file_name=f"human_review_queue_{ts}.json",
        mime="application/json",
        use_container_width=True,
    )


def _reprocess_document(record: dict, doc_path: Path, override_threshold: float) -> None:
    """Reprocess a document from the human review queue with overridden threshold.

    Args:
        record: Original queue record dict.
        doc_path: Path to the source document.
        override_threshold: Human-overridden H/F detection threshold.
    """
    from src.utils.doc_utils import detect_mime_type

    st.info(f"Reprocessing `{doc_path.name}` with hf_threshold={override_threshold:.2f}...")

    try:
        from src.agent.graph import build_graph
        from src.agent.state import create_initial_state

        graph = build_graph(use_checkpointer=False)

        initial_state = create_initial_state(
            doc_id=record.get("doc_id", "reprocess_001"),
            doc_path=str(doc_path),
            source_system=record.get("source_system", "local"),
            mime_type=detect_mime_type(doc_path),
            hf_threshold=override_threshold,
        )

        config = {"configurable": {"thread_id": record.get("doc_id", "reprocess_001")}}
        final_state = graph.invoke(initial_state, config=config)

        if final_state.get("validation_passed"):
            st.success("🎉 Reprocessed successfully — upserted to Qdrant!")
            # Remove from queue on successful reprocess.
            _remove_from_queue(record.get("doc_id", ""))
        else:
            st.warning("⚠️ Reprocessing completed but validation still failed.")

    except Exception as exc:
        st.error(f"Reprocessing failed: {exc}")
