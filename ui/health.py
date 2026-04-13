import streamlit as st

from amr_ui.utils.health_check import run_all_probes


def render_health_strip() -> None:
    """Render a single-row status strip showing ROS / LIDAR / camera / display / nav health.

    The styling (`.health-strip`, `.health-item`, `.health-dot.*`) is defined in
    :mod:`amr_ui.ui.styles` via ``static/styles.css``.
    """
    probes = run_all_probes()
    items_html = "".join(
        (
            f'<div class="health-item" title="{p.detail}">'
            f'<span class="health-dot {p.status}"></span>'
            f'<span class="health-label">{p.name}</span>'
            f"</div>"
        )
        for p in probes
    )
    st.markdown(f'<div class="health-strip">{items_html}</div>', unsafe_allow_html=True)
