import streamlit as st
from amr_ui.config.text import TEXT


def init_session_state():
    if "language" not in st.session_state:
        st.session_state.language = "English"
    if "login_modal" not in st.session_state:
        st.session_state.login_modal = False
    if "register_modal" not in st.session_state:
        st.session_state.register_modal = False
    if "is_logged_in" not in st.session_state:
        st.session_state.is_logged_in = False
    if "node" not in st.session_state:
        st.session_state.node = None
    if "rviz_pid" not in st.session_state:
        st.session_state.rviz_pid = None
    if "semantic_nav_pid" not in st.session_state:
        st.session_state.semantic_nav_pid = None


def get_text():
    """Return the localized text dict for the current language."""
    return TEXT[st.session_state.language]
