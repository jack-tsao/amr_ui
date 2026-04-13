import os
import base64
import time
import streamlit as st
from streamlit_chat import message
from openai import OpenAI


def render(t):
    st.subheader(t["hardware_title"])
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"""
            <style>
            .custom-table {{
            border-collapse: collapse;
            width: 90%;
            font-size: 15px;
            table-layout: fixed;
            }}
            .custom-table th, .custom-table td {{
            border: 1px solid #555;
            padding: 10px;
            text-align: left;
            vertical-align: top;
            word-break: break-word;
            }}
            .custom-table th {{
            background-color: #444;
            color: white;
            }}
            .custom-table td {{
            background-color: #2e2e2e;
            color: #f0f0f0;
            }}
            .custom-table tr:nth-child(even) td {{
            background-color: #3a3a3a;
            }}
            </style>

            <table class="custom-table">
            <tr>
                <th>{t["hardware_spec_item"]}</th>
                <th>{t["hardware_spec_description"]}</th>
                <th>{t["hardware_spec_local"]}</th>
            </tr>
            <tr>
                <td>{t["hardware_cpu"]}</td>
                <td>{t["hardware_cpu_desc"]}</td>
                <td>Intel Core i7-13700E</td>
            </tr>
            <tr>
                <td>{t["hardware_gpu"]}</td>
                <td>{t["hardware_gpu_desc"]}</td>
                <td>Intel UHD Graphics 770 (Raptor Lake)</td>
            </tr>
            <tr>
                <td>{t["hardware_ram"]}</td>
                <td>{t["hardware_ram_desc"]}</td>
                <td>32GB DDR4 </td>
            </tr>
            <tr>
                <td>{t["hardware_storage"]}</td>
                <td>{t["hardware_storage_desc"]}</td>
                <td>512GB NVMe SSD</td>
            </tr>
            <tr>
                <td>{t["hardware_network"]}</td>
                <td>{t["hardware_network_desc"]}</td>
                <td>4x GbE (eno1, eno2, enp4s0, enp5s0) + Wi-Fi (wlp3s0) + CAN Bus (can0)</td>
            </tr>
            <tr>
                <td>{t["hardware_io"]}</td>
                <td>{t["hardware_io_desc"]}</td>
                <td>4x USB 3.2, HDMI, DP, 4x GbE, Wi-Fi, CAN Bus</td>
            </tr>
            <tr>
                <td>{t["hardware_temp"]}</td>
                <td>{t["hardware_temp_desc"]}</td>
                <td></td>
            </tr>
            <tr>
                <td>{t["hardware_expansion"]}</td>
                <td>{t["hardware_expansion_desc"]}</td>
                <td>{t["hardware_expansion_local"]}</td>
            </tr>
            </table>
            """, unsafe_allow_html=True)
    
        with col2:
            st.image("/home/amr/Desktop/robot_code/ros2_openvino_toolkit/script/amr.png", caption="",  use_container_width=True)

    st.subheader(t["chatbot_title"])
    client = OpenAI(api_key="not implemented yet")  # Replace with your actual API key
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "input_key_id" not in st.session_state:
        st.session_state.input_key_id = 0

    input_key = f"user_input_{st.session_state.input_key_id}"
    user_input = st.text_input(t["chatbot_input"], key=input_key)

    chat_container = st.container()

    def get_bot_reply(user_message):
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": t["chatbot_system_prompt"]},
                    *st.session_state.chat_history,
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"{t['chatbot_error']}{e}"

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        reply = get_bot_reply(user_input)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})

    if st.button(t["chatbot_clear"]):
        st.session_state.chat_history.clear()
        st.session_state.input_key_id += 1 

    with chat_container:
        for i, chat in enumerate(st.session_state.chat_history[-12:]):
            is_user = chat["role"] == "user"
            message(chat["content"], is_user=is_user, key=f"chat_{i}")
    # user_input = st.text_input("💬 What would you like to say?", key="user_input")

    # def get_bot_reply(user_message):
    #     user_message = user_message.lower()
    #     if "hello" in user_message:
    #         return "Hello! How can I help you?"
    #     elif "battery" in user_message:
    #         return "Battery is at 30%, please return to the charging station soon 🔋"
    #     elif "navigation" in user_message:
    #         return "Planning navigation route, please wait..."
    #     else:
    #         return "Sorry, I don't understand that yet 😅"

    # if user_input:
    #     st.session_state.chat_history.append({"role": "user", "content": user_input})
    #     bot_reply = get_bot_reply(user_input)
    #     st.session_state.chat_history.append({"role": "bot", "content": bot_reply})

    # latest_chats = st.session_state.chat_history[-6:]

    # for i, chat in enumerate(latest_chats):
    #     is_user = chat["role"] == "user"
    #     message(chat["content"], is_user=is_user, key=f"chat_{i}")


