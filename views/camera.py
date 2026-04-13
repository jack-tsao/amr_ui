import os
import time
import signal
import threading
import subprocess
from PIL import Image, UnidentifiedImageError
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


def render(t):
    st.subheader(f"🔧 1. {t['camera_env_init']}")
    st.info(t["camera_env_info"])
    st.code("""
    cd ~/Downloads/Adv_AMR_installer_v1.0.0/AMR_script/sh && ./open_camera.sh && ./open_tracer_mini.sh
    """, language="bash")
    if "camera_proc" not in st.session_state:
        st.session_state.camera_proc = None
    command_close = st.text_input(f"{t['camera_input_command']}:", key="close")
    if st.button(f"🚀 {t['camera_execute']}", key="run_camera"):
        try:
            process = subprocess.Popen(
            command_close,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid
            )
            st.success(f"✅ {t['camera_command_success']}{process.pid}")
        except Exception as e:
            st.error(f"❌ {t['camera_error']}{str(e)}")

    st.code("""
    python3 /home/amr/Desktop/robot_code/ros2_openvino_toolkit/script/robotCamera.py
    """, language="bash")

    if "python_proc" not in st.session_state:
        st.session_state.python_proc = None

    command_py = st.text_input(f"{t['camera_input_python']}:", key="py_command")

    if st.button(f"🚀 {t['camera_execute']}", key="run_python"):
        try:
            process_py = subprocess.Popen(
                command_py,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid
            )
            st.session_state.python_proc = process_py
            st.success(f"✅ {t['camera_python_success']}{process_py.pid}")
        except Exception as e:
            st.error(f"❌ {t['camera_error']}{str(e)}")

    st.subheader(f"📷 2. {t['camera_view_title']}")
    camera_image_path = "/home/amr/Desktop/robot_code/camera/frame.jpg"
    st.caption(t["camera_view_caption"])

    if "camera_on" not in st.session_state:
        st.session_state.camera_on = False

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button(f"▶️ {t['camera_start']}"):
            st.session_state.camera_on = True
    with col2:
        if st.button(f"⏹️ {t['camera_stop']}"):
            st.session_state.camera_on = False

            try:
                os.killpg(os.getpgid(st.session_state.camera_proc.pid), signal.SIGTERM)
                st.success(f"🛑 {t['camera_script_closed']}")
            except Exception as e:
                st.warning(f"⚠️ {t['camera_script_close_error']}{e}")
            st.session_state.camera_proc = None

            try:
                os.killpg(os.getpgid(st.session_state.python_proc.pid), signal.SIGTERM)
                st.success(f"🛑 {t['camera_python_closed']}")
            except Exception as e:
                st.warning(f"⚠️ {t['camera_python_close_error']}{e}")
            st.session_state.python_proc = None

    st.markdown(
        f"**{t['camera_status']}** {'🟢 ' + t['camera_status_on'] if st.session_state.camera_on else '🔴 ' + t['camera_status_off']}"
    )


    frame_container = st.empty()
    if st.session_state.camera_on:
        st_autorefresh(interval=2000, key="camera-refresh")

        if os.path.exists(camera_image_path):
            img = Image.open(camera_image_path)
            frame_container.image(img, caption=t["camera_image_caption"], use_container_width=True)
        else:
            frame_container.warning(f"❗ {t['camera_no_image']}")
    else:
        frame_container.empty()

    st.subheader(f"🕹️ {t['camera_control_title']}")
    st.caption(t["camera_control_caption"])

    if "ros_initialized" not in st.session_state:
        if not rclpy.ok(): 
            rclpy.init()
        st.session_state.ros_initialized = True

    if "twist_pub" not in st.session_state:
        class WebTeleop(Node):
            def __init__(self):
                super().__init__('web_teleop')
                self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)

            def send_cmd(self, linear_x, angular_z):
                msg = Twist()
                msg.linear.x = linear_x
                msg.angular.z = angular_z
                self.publisher.publish(msg)
                print(f"✅ {t['camera_send_command']} linear={linear_x:.2f}, angular={angular_z:.2f}")

        st.session_state.node = WebTeleop()
        st.session_state.twist_pub = st.session_state.node.send_cmd

    if "ros_spin_started" not in st.session_state:
        node = st.session_state.node

        def ros_spin(node=node):
            rclpy.spin(node)

        spin_thread = threading.Thread(target=ros_spin, daemon=True)
        spin_thread.start()
        st.session_state.ros_spin_started = True

    st.caption(f"⚙️ {t['camera_speed_setting']}")
    speed = st.slider(t["camera_linear_speed"], 0.0, 1.0, 0.2, 0.05)
    turn = st.slider(t["camera_angular_speed"], 0.0, 1.0, 0.5, 0.05)

    st.caption(f"🎮 {t['camera_keyboard_control']}")
    col_w, _, _ = st.columns([1, 1, 1])
    with col_w:
        if st.button(f"⬆️ {t['camera_forward']}"):
            st.session_state.twist_pub(speed, 0.0)

    col_a, col_s, col_d = st.columns(3)
    with col_a:
        if st.button(f"⬅️ {t['camera_left']}"):
            st.session_state.twist_pub(0.0, turn)
    with col_s:
        if st.button(f"⬇️ {t['camera_backward']}"):
            st.session_state.twist_pub(-speed, 0.0)
    with col_d:
        if st.button(f"➡️ {t['camera_right']}"):
            st.session_state.twist_pub(0.0, -turn)

    st.markdown(f"### ⛔ {t['camera_emergency_stop']}")
    if st.button(f"⏹ {t['camera_stop_robot']}"):
        st.session_state.twist_pub(0.0, 0.0)
        st.info(f"✅ {t['camera_stop_sent']}")



