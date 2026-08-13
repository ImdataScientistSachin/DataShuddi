"""
DataShuddi -- Streamlit Page 4: Self-Correction Log.

Displays reflector node history from session state and any available
processing logs. Shows threshold revision timeline and safeguard status.
"""
import json
import time
from pathlib import Path

import streamlit as st

from streamlit_app.ui_components import glass_card, status_badge


def _load_reflector_history() -> list[dict]:
    """Load reflector revision history from session and queue data.

    Returns:
        List of reflector event dicts sorted by timestamp.
    """
    history: list[dict] = []

    # Pull from session state last result if available.
    last_result = st.session_state.get("last_result")
    if last_result and last_result.get("reflection_text"):
        history.append({
            "version": len(history) + 1,
            "hf_threshold": last_result.get("hf_threshold", 0.30),
            "confidence": last_result.get("reflector_confidence", 0.0),
            "timestamp": time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(last_result.get("node_timestamps", {}).get("reflector", time.time())),
            ),
            "reason": last_result.get("reflection_text", "Session-based threshold adjustment"),
            "retry_count": last_result.get("retry_count", 0),
        })

    # Pull from human review queue for additional history.
    queue_file = Path("data/human_review/queue.jsonl")
    if queue_file.exists():
        with open(queue_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line.strip())
                    history.append({
                        "version": len(history) + 1,
                        "hf_threshold": 0.30,
                        "confidence": 0.0,
                        "timestamp": time.strftime(
                            "%Y-%m-%d %H:%M:%S",
                            time.localtime(record.get("timestamp", time.time())),
                        ),
                        "reason": f"Escalated: {'; '.join(record.get('validation_errors', [])[:2])}",
                        "retry_count": record.get("retry_count", 0),
                    })
                except (json.JSONDecodeError, ValueError):
                    pass

    return history


def render() -> None:
    """Render Page 4: Reflector Self-Correction Log & Store History."""
    st.markdown("# ⚙️ Self-Correction & Policy Store")
    st.caption("Track dynamic threshold adjustments made by Qwen14b Reflector Node (Node 6).")

    # Safeguards status row.
    st.markdown("### 🛡️ Reflector Safeguards")
    c1, c2, c3 = st.columns(3)

    c1.metric("Confidence Gate", "≥ 0.70")
    c1.markdown(status_badge("ACTIVE", "pass"), unsafe_allow_html=True)

    c2.metric("Max Delta Cap", "± 0.05")
    c2.markdown(status_badge("ENFORCED", "pass"), unsafe_allow_html=True)

    # Count rollbacks from queue.
    queue_file = Path("data/human_review/queue.jsonl")
    escalation_count = 0
    if queue_file.exists():
        with open(queue_file, encoding="utf-8") as f:
            escalation_count = sum(1 for line in f if line.strip())

    c3.metric("Human Escalations", str(escalation_count))
    variant = "pass" if escalation_count == 0 else "warn"
    c3.markdown(status_badge(f"{'READY' if escalation_count == 0 else 'TRIGGERED'}", variant), unsafe_allow_html=True)

    st.markdown("---")

    # Revision history timeline.
    st.markdown("### 📜 Revision History")

    history = _load_reflector_history()

    if not history:
        st.info(
            "📝 No self-correction events recorded yet. "
            "Process a document through the Live Monitor to generate reflector activity."
        )

        # Show the default initial threshold state.
        st.markdown(
            glass_card(
                "<p style='margin:0;color:var(--text-secondary);'>"
                "Initial H/F Threshold: <strong>0.30</strong> · "
                "Status: <strong>Default</strong> · "
                "No adjustments made"
                "</p>",
                title="Current Threshold State",
            ),
            unsafe_allow_html=True,
        )
        return

    # Display revision records.
    for entry in reversed(history):
        confidence = entry.get("confidence", 0.0)
        badge = status_badge("HIGH CONF", "pass") if confidence >= 0.70 else status_badge("LOW CONF", "warn")

        st.markdown(
            glass_card(
                f"<p style='margin:0;'>"
                f"<strong>Threshold:</strong> {entry.get('hf_threshold', 0.30):.2f} · "
                f"<strong>Confidence:</strong> {confidence:.2f} {badge} · "
                f"<strong>Retries:</strong> {entry.get('retry_count', 0)}"
                f"</p>"
                f"<p style='margin:0.3rem 0 0;color:var(--text-secondary);font-size:0.85rem;'>"
                f"📝 {entry.get('reason', 'N/A')}"
                f"</p>"
                f"<p style='margin:0.2rem 0 0;color:var(--text-muted);font-size:0.75rem;'>"
                f"🕐 {entry.get('timestamp', 'Unknown')}"
                f"</p>",
                title=f"Revision v{entry.get('version', '?')}",
            ),
            unsafe_allow_html=True,
        )
        st.markdown("")

    # Current state summary.
    st.markdown("---")
    st.markdown("### 📊 Current Threshold State")
    last_result = st.session_state.get("last_result")
    if last_result:
        current_threshold = last_result.get("hf_threshold", 0.30)
        st.metric("Active H/F Threshold", f"{current_threshold:.2f}")
    else:
        st.metric("Active H/F Threshold", "0.30 (default)")
