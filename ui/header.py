import base64
from pathlib import Path
from typing import Optional

import streamlit as st

_REDHAT_LOGO = Path("/home/amr/Desktop/redhat.png")
_INTEL_LOGO = Path("/home/amr/Desktop/Intel.png")


def _load_logo_b64(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return base64.b64encode(path.read_bytes()).decode()


def render_header() -> None:
    """Render the page header: animated title on the left, partner logos on the right."""
    col1, col2 = st.columns([4, 1])

    with col1:
        st.markdown('<h1 class="title-glow">AMR Advantech</h1>', unsafe_allow_html=True)

    with col2:
        redhat_b64 = _load_logo_b64(_REDHAT_LOGO)
        intel_b64 = _load_logo_b64(_INTEL_LOGO)

        if not (redhat_b64 and intel_b64):
            return

        st.markdown(
            f"""
            <div style="
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100px;
                margin-top: 0px;
            ">
                <img src="data:image/png;base64,{redhat_b64}" width="120">
                <span style="font-size: 28px; margin: 0 15px;">|</span>
                <img src="data:image/png;base64,{intel_b64}" width="120">
            </div>
            """,
            unsafe_allow_html=True,
        )
