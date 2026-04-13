import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from amr_ui.config.session import init_session_state, get_text
from amr_ui.ui.auth import render_auth_controls
from amr_ui.ui.header import render_header
from amr_ui.ui.health import render_health_strip
from amr_ui.ui.router import route
from amr_ui.ui.sidebar import render_sidebar
from amr_ui.ui.styles import inject_global_styles

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Advantech AMR Control", layout="wide")

# ── Session + styles ──────────────────────────────────────────────────────────
init_session_state()
inject_global_styles()
t = get_text()

# ── Layout ────────────────────────────────────────────────────────────────────
render_header()
render_health_strip()
page = render_sidebar(t)
render_auth_controls(t)

# ── Auth guard ────────────────────────────────────────────────────────────────
# Login requirement disabled — all pages are accessible without login.
# if page != t["sidebar_pages"][0] and not st.session_state.get("is_logged_in", False):
#     st.error("⚠️ " + t["error_login_required"])
#     page = t["sidebar_pages"][0]

# ── Page routing ──────────────────────────────────────────────────────────────
route(page, t)
