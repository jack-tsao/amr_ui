import os
import json
import signal
import time
import subprocess
from datetime import datetime, timedelta
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go

from amr_ui.utils.file_utils import load_susi_json


def render(t):
    st.subheader(f"📟 {t['susi_status_title']}")
    st.info(t["susi_status_info"])
    st.code("""
    python3 /home/amr/Desktop/robot_code/ros2_openvino_toolkit/script/susi.py
    """, language="bash")

    if 'susi_status_message' not in st.session_state:
        st.session_state.susi_status_message = None
    if 'susi_status_type' not in st.session_state:
        st.session_state.susi_status_type = None

    command = st.text_input(f"{t['susi_input_command']}:", key="susienbir_cmd")
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button(f"🚀 {t['susi_start']}", key="run_environment_command"):
            if command.strip():
                try:
                    proc = subprocess.Popen(["bash", "-c", command])
                    st.session_state.susi_process = proc
                    st.session_state.susi_status_message = f"✅ {t['susi_starting']}，PID={proc.pid}"
                    st.session_state.susi_status_type = "success"
                except Exception as e:
                    st.session_state.susi_status_message = f"❌ {t['susi_exec_error']}{e}"
                    st.session_state.susi_status_type = "error"
            else:
                st.session_state.susi_status_message = f"⚠️ {t['susi_input_warning']}"
                st.session_state.susi_status_type = "warning"

    with col2:
        if st.button(f"❌ {t['susi_stop']}", key="stop_susi_button"):
            proc = st.session_state.get("susi_process", None)
            if proc is not None and proc.poll() is None:
                try:
                    os.kill(proc.pid, signal.SIGTERM)
                    st.session_state.susi_process = None
                    st.session_state.susi_status_message = f"🛑 {t['susi_stopped']}（PID={proc.pid}）"
                    st.session_state.susi_status_type = "success"
                except Exception as e:
                    st.session_state.susi_status_message = f"❌ {t['susi_stop_error']}{e}"
                    st.session_state.susi_status_type = "error"
            else:
                st.session_state.susi_status_message = f"⚠️ {t['susi_not_running']}"
                st.session_state.susi_status_type = "warning"

    if st.session_state.susi_status_message:
        if st.session_state.susi_status_type == "success":
            st.success(st.session_state.susi_status_message)
        elif st.session_state.susi_status_type == "error":
            st.error(st.session_state.susi_status_message)
        elif st.session_state.susi_status_type == "warning":
            st.warning(st.session_state.susi_status_message)


    st.divider()

    REFRESH_INTERVAL = 150 

    if 'last_update' not in st.session_state:
        st.session_state.last_update = 0
    if 'update_counter' not in st.session_state:
        st.session_state.update_counter = 0

    st_autorefresh(interval=2000, key="check_refresh")
    st.session_state.data = load_susi_json()
    st.session_state.last_update = time.time()

    st.title(f"🧠 {t['susi_monitor_title']}")
    col1, col2 = st.columns(2)
    with col1:
        manual_refresh = st.button(f"🔄 {t['susi_manual_refresh']}", type="primary")
    with col2:
        auto_refresh_enabled = st.toggle(f"🔄 {t['susi_auto_refresh']}", value=False)

    st.markdown("---")

    NOW_TIMESTAMP = time.time()
    NOW_DATETIME = datetime.now()

    seconds_since_last_update = NOW_TIMESTAMP - st.session_state.last_update

    should_update = manual_refresh

    if should_update:
        new_data = load_susi_json()
        st.session_state.data = new_data
    
        st.session_state.last_update = NOW_TIMESTAMP
        st.session_state.update_counter += 1

        st.success("✅ Data manually refreshed!", icon="🔄")

    data = st.session_state.data

    data_container = st.container()

    with data_container:
        if "error" in data:
            st.error(f"❌ {t['susi_data_error']}{data['error']}")
        elif "system_time" not in data:
            st.error(f"❌ {t['susi_missing_time']}")
        else:
            try:
                saved_dt = datetime.strptime(data["system_time"], "%Y-%m-%d %H:%M:%S")
                time_diff = NOW_DATETIME - saved_dt
                outdated = time_diff > timedelta(minutes=5)
            
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.info(f"🕒 **Last refresh** {int(seconds_since_last_update)} seconds ago | **Data time** {saved_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                with col2:
                    if outdated:
                        st.warning(f"⚠️ **{t['susi_outdated']}**")
                    else:
                        st.success(f"✅ **{t['susi_latest']}**")
                with col3:
                    st.info(f"📊 **{t['susi_monitor_items']}** {len([k for k in data.keys() if k != 'system_time']) -1 } items")
            
                st.markdown("---")

                if outdated:
                    st.warning(t['susi_data_outdated_warning'])
                else:
                    hw_data = {}
                    for key, value in data.items():
                        if key != "system_time" and isinstance(value, dict) and "value" in value:
                            hw_data[key] = value

                    if hw_data:
                        voltage_data = {k: v for k, v in hw_data.items() if "Voltage" in k}
                        if voltage_data:
                            st.markdown(f"### {t['voltage_monitor_title']}")
                            cols = st.columns(4)
                            voltage_items = list(voltage_data.items())
                            for i, (key, value) in enumerate(voltage_items):
                                with cols[i]:
                                    name = key.split("/")[-1]
                                    voltage_val = float(value['value'])

                                    if "3.3V" in key:
                                        name += t["desc_3v"]
                                    elif "5V" in key and "Standby" not in key:
                                        name += t["desc_5v"]
                                    elif "12V" in key:
                                        name += t["desc_12v"]
                                    elif "CMOS" in key:
                                        name += t["desc_cmos"]

                                    if "3.3V" in key and (voltage_val < 3.0 or voltage_val > 3.6):
                                        st.error(f"🔋 **{name}**\n\n# {value['value']} V")
                                    elif "5V" in key and (voltage_val < 4.5 or voltage_val > 5.5):
                                        st.error(f"🔋 **{name}**\n\n# {value['value']} V")
                                    elif "12V" in key and (voltage_val < 11.0 or voltage_val > 13.0):
                                        st.error(f"🔋 **{name}**\n\n# {value['value']} V")
                                    elif "CMOS" in key and voltage_val < 2.8:
                                        st.warning(f"🔋 **{name}**\n\n# {value['value']} V")
                                    else:
                                        st.success(f"🔋 **{name}**\n\n# {value['value']} V")

                            st.markdown("<br>", unsafe_allow_html=True)

                        temp_data = {k: v for k, v in hw_data.items() if "Temperature" in k}
                        fan_data = {k: v for k, v in hw_data.items() if "Fan Speed" in k}

                        col1, col2 = st.columns(2)

                        with col1:
                            if temp_data:
                                st.markdown(f"### {t['temperature_monitor_title']}")
                                for key, value in temp_data.items():
                                    name = key.split("/")[-1]
                                    temp_val = float(value['value'])

                                    if temp_val > 80:
                                        st.error(f"🌡️ **{name} {t['temperature_label']}**\n\n## {value['value']} °C")
                                    elif temp_val > 70:
                                        st.warning(f"🌡️ **{name} {t['temperature_label']}**\n\n## {value['value']} °C")
                                    else:
                                        st.info(f"🌡️ **{name} {t['temperature_label']}**\n\n## {value['value']} °C")

                        with col2:
                            if fan_data:
                                st.markdown(f"### {t['fan_monitor_title']}")
                                for key, value in fan_data.items():
                                    name = key.split("/")[-1]
                                    fan_val = float(value['value'])

                                    if fan_val == 0:
                                        if "CPU" in key.upper():
                                            st.error(f"🌀 **{name} {t['fan_label']}**\n\n## {value['value']} RPM\n**❌ {t['cpu_fan_stopped']}**")
                                        else:
                                            st.warning(f"🌀 **{name} {t['fan_label']}**\n\n## {value['value']} RPM\n**⚠️ {t['fan_not_running']}**")
                                    else:
                                        st.success(f"🌀 **{name} {t['fan_label']}**\n\n## {value['value']} RPM")

                        st.markdown("<br>", unsafe_allow_html=True)

                        current_data = {k: v for k, v in hw_data.items() if "Current" in k}
                        case_data = {k: v for k, v in hw_data.items() if "Case Open" in k}
                        disk_data = {k: v for k, v in hw_data.items() if "DiskInfo" in k}

                        col1, col2 = st.columns(2)

                        with col1:
                            if disk_data:
                                st.markdown(f"### {t['disk_monitor_title']}")
                                for key, value in disk_data.items():
                                    disk_size_mb = float(value['value'])
                                    disk_size_gb = disk_size_mb / 1024

                                    if disk_size_gb > 1024:
                                        display_size = f"{disk_size_gb/1024:.1f} TB"
                                    else:
                                        display_size = f"{disk_size_gb:.1f} GB"

                                    st.info(f" **{t['total_disk_label']}**\n\n## {display_size}")

                        with col2:
                            st.empty()
                            # if current_data:
                            #     st.markdown(f"### {t['current_monitor_title']}")
                            #     for key, value in current_data.items():
                            #         name = key.split("/")[-1]
                            #         st.info(f"⚡ **{name}**\n\n## {value['value']} A")

            except Exception as e:
                st.error(f"❌ {t['susi_time_format_error']}{str(e)}")

    if auto_refresh_enabled:
        st.markdown("---")
    
        remaining_seconds = max(0, REFRESH_INTERVAL - seconds_since_last_update)
        progress = min(1.0, seconds_since_last_update / REFRESH_INTERVAL)
    
        st.progress(progress, text=f"⏰ {t['susi_next_refresh']} {int(remaining_seconds)} {t['susi_seconds']}")
    
        if remaining_seconds <= 0:
            new_data = load_susi_json()
            st.session_state.data = new_data
            st.session_state.last_update = NOW_TIMESTAMP
            st.session_state.update_counter += 1
            st.success("✅ Data auto-refreshed!", icon="🔄")
            st.rerun() 
    
        if st.checkbox(t["debug_checkbox_label"], value=False):
            st.text(t["debug_current_time"].format(time=NOW_TIMESTAMP))
            st.text(t["debug_last_update"].format(time=st.session_state.last_update))
            st.text(t["debug_time_diff"].format(seconds=seconds_since_last_update))
            st.text(t["debug_remaining_time"].format(seconds=remaining_seconds))
            st.text(t["debug_progress"].format(progress=progress))
        
            if "system_time" in data:
                data_time = datetime.strptime(data["system_time"], "%Y-%m-%d %H:%M:%S")
                data_timestamp = data_time.timestamp()
                st.text(t["debug_data_timestamp"].format(timestamp=data_timestamp))
                st.text(t["debug_data_update_diff"].format(diff=abs(data_timestamp - st.session_state.last_update)))

