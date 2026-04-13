import streamlit as st
from streamlit_modal import Modal

# Hardcoded demo credentials. Replace with a proper auth backend before production.
_DEMO_USER = "amazon"
_DEMO_PASS = "amazon"


def render_auth_controls(t: dict) -> None:
    """Render sidebar login/register buttons and their modals.

    Uses st.toast() for success feedback and triggers st.rerun() to close the
    modal, so the UI never blocks on time.sleep().
    """
    col1, col2 = st.sidebar.columns(2)
    with col1:
        login_clicked = st.button(
            t["login"], disabled=st.session_state.get("is_logged_in", False)
        )
    with col2:
        register_clicked = st.button(t["register"])

    modal_login = Modal("User Login", key="modal_login")
    modal_register = Modal("Register Account", key="modal_register")

    if login_clicked:
        modal_login.open()
        st.session_state.login_modal = True
        st.session_state.register_modal = False
    if register_clicked:
        modal_register.open()
        st.session_state.register_modal = True
        st.session_state.login_modal = False

    if modal_login.is_open():
        with modal_login.container():
            username = st.text_input(t["login_account"], key="login_user")
            password = st.text_input(
                t["login_password"], type="password", key="login_pass"
            )
            if st.button(t["login_button"], key="login"):
                if username == _DEMO_USER and password == _DEMO_PASS:
                    st.session_state.is_logged_in = True
                    st.session_state.username = username
                    st.session_state.login_modal = False
                    st.toast(f"{t['login_success']}{username}", icon="✅")
                    modal_login.close()
                    st.rerun()
                else:
                    st.error(t["login_error"])

    if modal_register.is_open():
        with modal_register.container():
            st.text_input(t["register_account"])
            st.text_input(t["register_password"], type="password")
            st.text_input(t["register_password2"], type="password")
            if st.button(t["register_button"], key="register"):
                st.session_state.register_modal = False
                st.toast(t["register_success"], icon="✅")
                modal_register.close()
                st.rerun()
