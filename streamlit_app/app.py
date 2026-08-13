"""
DataShuddi -- Streamlit Dashboard Application.

Multi-page Streamlit monitoring UI for real-time document processing,
metrics, diff viewing, self-correction logs, and human review queue.
"""
import sys
from pathlib import Path

# Ensure project root and .venv site-packages are on sys.path for Streamlit imports
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

venv_site_pkgs = ROOT_DIR / ".venv" / "Lib" / "site-packages"
if venv_site_pkgs.exists() and str(venv_site_pkgs) not in sys.path:
    sys.path.insert(0, str(venv_site_pkgs))

import streamlit as st  # noqa: E402

from streamlit_app.ui_components import (  # noqa: E402
    app_footer,
    load_css,
    render_hardware_widget,
    render_sidebar_header,
)

st.set_page_config(
    page_title="DataShuddi — PII Scrubbing Monitor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject custom CSS theme.
st.markdown(load_css(), unsafe_allow_html=True)


def _get_queue_count() -> int:
    """Helper to check queue items count for navigation badge."""
    q = Path("data/human_review/queue.jsonl")
    if not q.exists():
        return 0
    try:
        with open(q, encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def _init_session_state() -> None:
    """Initialize session state keys with safe defaults on first run."""
    defaults = {
        "last_result": None,
        "processing": False,
        "processed_count": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main() -> None:
    """Streamlit dashboard entry point with page navigation."""
    _init_session_state()

    # Dynamic queue badge calculation
    queue_count = _get_queue_count()
    queue_label = f"🚨 Human Review Queue ({queue_count})" if queue_count > 0 else "🚨 Human Review Queue"

    # Page registry — maps display label to module name.
    pages: dict[str, str] = {
        "⚡ Live Monitor": "page_01_live_monitor",
        "📊 Metrics Dashboard": "page_02_metrics",
        "🔍 Before/After Diff": "page_03_diff_viewer",
        "⚙️ Self-Correction Log": "page_04_self_correction",
        queue_label: "page_05_human_review",
    }

    # World-Class Sidebar Branding Header
    st.sidebar.markdown(render_sidebar_header(), unsafe_allow_html=True)

    choice = st.sidebar.radio("Navigation", list(pages.keys()), label_visibility="collapsed")

    # Hardware Telemetry Widget
    st.sidebar.markdown(render_hardware_widget(), unsafe_allow_html=True)

    # Dynamic page dispatch.
    import importlib

    module_name = pages[choice]
    module = importlib.import_module(f"streamlit_app.app_pages.{module_name}")
    module.render()

    # Footer.
    st.markdown(app_footer(), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
