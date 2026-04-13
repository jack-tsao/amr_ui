import os
import time
import subprocess
from PIL import Image, UnidentifiedImageError
import streamlit as st


def render(t):
    st.subheader(t["radar_title_1"])
    if "radar_started" not in st.session_state:
        st.session_state["radar_started"] = False

    st.info(t["radar_info_1"])
    st.code("""
    cd ~/Documents/ros2_amr/AMR_script && ./run_2D_SLAM.sh
    """, language="bash")
    command = st.text_input(t["radar_input_command"], key="open")

    if st.button(t["radar_execute"], key="run_open_command"):
        if command.strip():
            result = subprocess.Popen(command, shell=True)
            st.session_state["radar_started"] = True
            st.code(result.stdout or t["radar_success"])
            if result.stderr:
                st.error(result.stderr)
        else:
            st.warning(t["radar_input_warning"])

    st.subheader(t["radar_title_2"])
    rviz_script_path = "/home/amr/Desktop/robot_code/ros2_openvino_toolkit/script/rviz.py"
    image_path = "/home/amr/Desktop/robot_code/rvizslam/rviz_snap.png"

    def wait_for_valid_recent_image(path, max_age=2, timeout=2, interval=0.2):
        """Wait for an image updated within the last `max_age` seconds that can be opened."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if os.path.exists(path) and os.path.getsize(path) > 1000:
                modified_time = os.path.getmtime(path)
                if time.time() - modified_time <= max_age:
                    try:
                        img = Image.open(path)
                        img.verify()
                        return Image.open(path)
                    except UnidentifiedImageError:
                        time.sleep(interval)
                else:
                    time.sleep(interval)
            else:
                time.sleep(interval)
        return None

    col1, col2 = st.columns(2)

    with col1:
        if st.session_state["radar_started"]:
            if st.button(t["radar_show_button"], key="show_rviz"):
                subprocess.Popen(["python3", rviz_script_path])
                st.success(t["radar_show_success"])
        else:
            st.button(t["radar_show_button"], key="show_rviz_disabled", disabled=True)

    with col2:
        if st.session_state["radar_started"]:
            if st.button(t["radar_stop_button"], key="stop_rviz"):
                os.system("pkill -f rviz.py")
                st.warning(t["radar_stop_success"])
        else:
            st.button(t["radar_stop_button"], key="stop_rviz", disabled=True)
    image_container = st.empty()

    img = wait_for_valid_recent_image(image_path, max_age=2, timeout=2)
    if img:
        image_container.image(img, caption=t["radar_image_caption"], use_container_width=True)
    else:
        st.warning(t["radar_no_image"])

    st.subheader(t["radar_title_3"])
    st.info(t["radar_info_3"])
    st.code("""
    cd ~/Documents/ros2_amr/AMR_script && ./save_map.sh && ./stop_2D_SLAM.sh
    """, language="bash")
    command_close = st.text_input(t["radar_input_command"], key="close")
    if st.button(t["radar_execute"], key="run_close_command"):
        if command_close.strip():
            result = subprocess.run(command_close, shell=True, capture_output=True, text=True)
            st.code(result.stdout or t["radar_no_output"])
            if result.stderr:
                st.error(result.stderr)
        else:
            st.warning(t["radar_input_warning"])


