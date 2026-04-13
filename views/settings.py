import subprocess
import time
import streamlit as st


def render(t):

    with st.expander(t["power_title"]):
        st.caption(t["power_caption"])
        if st.button(t["power_button"]):
            st.warning(t["power_warning"])
            try:
                subprocess.run(["sudo", "poweroff"])
            except Exception as e:
                st.error(t["power_error"] + str(e))

    with st.expander(t["reboot_title"]):
        st.caption(t["reboot_caption"])
        if st.button(t["reboot_button"]):
            st.warning(t["reboot_warning"])
            try:
                subprocess.run(["sudo", "reboot"])
            except Exception as e:
                st.error(t["reboot_error"] + str(e))


    with st.expander(t["language_title"]):
        st.caption(t["language_caption"])
        language_options = ["繁體中文", "日本語", "한국어", "English"]

        language = st.radio(
            t["language_radio"],
            options=language_options,
            index=language_options.index(st.session_state.language)
            if st.session_state.language in language_options else 0
        )

        if language != st.session_state.language:
            st.session_state.language = language
            st.rerun()

        st.success(t["language_success"] + language)


    with st.expander(t["theme_title"]):
        st.caption(t["theme_caption"])
        if "theme" not in st.session_state:
            st.session_state.theme = "Dark"
        theme = st.radio(
            t["theme_radio"],
            options=["Dark", "Light"],
            index=0 if st.session_state.theme == "Dark" else 1
        )
        if theme != st.session_state.theme:
            st.session_state.theme = theme
            st.rerun()
        st.success(t["theme_success"] + theme)


    with st.expander(t["contact_title"]):
        st.caption(t["contact_caption"])
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            <div style="border: 1px solid #ccc; border-radius: 10px; padding: 15px; background-color: #1e1e1e; line-height: 2.0;">
                <h4>👨‍💼 Steve Chang</h4>
                <p>
                    💼  AVP (Associate Vice President)<br>
                    🏷️ ACL_Embedded_Embedded Sector<br>
                    📧 <a href="mailto:Steve.Chang@advantech.com.tw" style="color: #4EA8DE;">Steve.Chang@advantech.com.tw</a><br>
                    ☎️ VOIP: 511 EXT: 9279<br>
                    🏢 Advantech ACL<br>
                    📍 No. 27-3, Wende Rd., Leshan Village, Guishan Dist., Taoyuan City, Taiwan
                </p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div style="border: 1px solid #555; border-radius: 12px; padding: 15px;
                        background-color: #1e1e1e; color: #eee;
                        box-shadow: 2px 2px 5px #000; line-height: 2.0;">
                <h4>🧑‍💼 Jack Tsao</h4>
                <p>
                    💼 Director<br>
                    🏷️ FAE<br>
                    📧 <a href="mailto:Jack.Tsao@advantech.com" style="color: #4EA8DE;">Jack.Tsao@advantech.com.tw</a><br>
                    ☎️ VOIP:516 EXT:4260<br>
                    🏢 Advantech AJP<br>
                    📍 6-16-3 Asakusa, Taito-ku, Tokyo, Japan
                </p>
            </div>
            """, unsafe_allow_html=True)


        with col3:
            st.markdown("""
            <div style="border: 1px solid #555; border-radius: 12px; padding: 15px;
                        background-color: #1e1e1e; color: #eee;
                        box-shadow: 2px 2px 5px #000; line-height: 2.0;">
                <h4>👨‍💻 Ray Zheng</h4>
                <p>
                    🧪 Lv1 Engineer<br />
                    🏷️ ACL_Embedded_Linux Service<br />
                    📧 <a href="mailto:Ray.Zheng@advantech.com.tw" style="color: #4EA8DE;">Ray.Zheng@advantech.com.tw</a><br />
                    ☎️ VOIP:511 EXT:9490<br />
                    🏢 Advantech ACL<br>
                    📍 No. 27-3, Wende Rd., Leshan Village, Guishan Dist., Taoyuan City, Taiwan
                </p>
            </div>
            """, unsafe_allow_html=True)

    with st.expander(t["logout_title"]):
        st.caption(t["logout_caption"])
        if st.button(t["logout_button"]):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success(t["logout_success"])

