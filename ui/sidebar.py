import streamlit as st


def render_sidebar(t: dict) -> str:
    """Render the sidebar and return the selected page label."""
    st.sidebar.title(t["sidebar_title"])

    if st.session_state.get("is_logged_in"):
        st.sidebar.caption(
            f"{t['welcome_user']}{st.session_state.get('username', '')}{t['honorific']}"
        )

    page = st.sidebar.radio(" ", t["sidebar_pages"])

    if page == t["sidebar_pages"][2]:
        st.sidebar.markdown("---")
        nav_mode = st.sidebar.selectbox(
            "Navigation Mode",
            t["nav_modes"],
            key="nav_mode_selector",
            label_visibility="collapsed",
        )
        st.session_state["nav_mode"] = nav_mode
        st.sidebar.markdown("---")

    st.sidebar.markdown("<br>" * 11, unsafe_allow_html=True)

    return page
