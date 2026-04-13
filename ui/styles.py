from pathlib import Path

import streamlit as st

_CSS_PATH = Path(__file__).parent.parent / "static" / "styles.css"

_LIGHT_OVERRIDE = """
.stApp { background-color: #FFFFFF !important; color: #111111 !important; }
[data-testid="stSidebar"] { background-color: #F5F5F5 !important; }
[data-testid="stSidebar"] * { color: #111111 !important; }
.stApp p, .stApp span, .stApp label, .stApp div { color: #111111; }
.stMarkdown, .stText { color: #111111 !important; }
"""


def inject_global_styles() -> None:
    """Load the project's global stylesheet and inject it into the Streamlit page."""
    css = _CSS_PATH.read_text(encoding="utf-8")
    if st.session_state.get("theme") == "Light":
        css += _LIGHT_OVERRIDE
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
