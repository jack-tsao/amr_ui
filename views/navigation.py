import os
import json
import time
import math
import threading
import subprocess
import zmq
import cv2
import streamlit as st
import streamlit.components.v1 as components
from streamlit_javascript import st_javascript
from PIL import Image

from amr_ui.utils.ros_utils import initialize_ros_node, publish_initial_pose


def render(t):
    nav_mode = st.session_state.get("nav_mode_selector", t["nav_modes"][0])
    if nav_mode == t["nav_modes"][0]:
        st.subheader(t["env_init_title"])
        st.info(t["env_init_info"])
        st.code("""
        cd ~/Documents/ros2_amr/AMR_script && ./run_navigation.sh
        """, language="bash")
        command_input = st.text_input(t["input_command"], key="build_nav_environment")
        if st.button(t["execute_button"], key="run_nav_command"):
            if command_input.strip() == "":
                st.warning(t["input_warning"])
            else:
                try:
                    process = subprocess.Popen(
                        command_input,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        preexec_fn=os.setsid
                    )
                    st.session_state["nav_proc"] = process
                    st.success(t["execute_success"].format(process.pid))
                except Exception as e:
                    st.error(t["execute_error"].format(str(e)))

        st.subheader(t["nav_task_title"])
        if "goal_points" not in st.session_state:
            st.session_state.goal_points = [{"x": 0.0, "y": 0.0, "yaw": 0.0}]

        if st.button(t["start_nav_node"], key="start_navigation_node"):
            if initialize_ros_node():
                st.success(t["nav_node_success"])
            else:
                st.info(t["nav_node_info"])


        #st.markdown("---")

        @st.dialog(t["nav_dialog_title"])
        def show_navigation_dialog():
            with st.form("navigation_form_in_dialog"):
                st.markdown(f"#### {t['start_coord_title']}")
                col1, col2, col3 = st.columns(3)
                with col1:
                    start_x = st.number_input(t["start_x"], key="start_x", format="%.2f")
                with col2:
                    start_y = st.number_input(t["start_y"], key="start_y", format="%.2f")
                with col3:
                    start_yaw = st.number_input(t["start_yaw"], key="start_yaw", format="%.2f")

                set_start_clicked = st.form_submit_button(t["set_start_button"])
                if set_start_clicked:
                    st.session_state.start_pose = {
                        "x": start_x,
                        "y": start_y,
                        "yaw": start_yaw
                    }
                    if "ros_node" in st.session_state:
                        publish_initial_pose(
                            node=st.session_state.ros_node,
                            x=start_x,
                            y=start_y,
                            yaw_deg=start_yaw
                        )
                        st.success(t["start_set_success"].format(start_x, start_y, start_yaw))
                    else:
                        st.warning(t["ros_node_warning"])
                    
                st.markdown("---")


                st.markdown(f"#### {t['goal_coord_title']}")
                for i, point in enumerate(st.session_state.goal_points):
                    st.markdown(f"#### {t['goal_group'].format(i+1)}")
                    col4, col5, col6 = st.columns(3)
                    with col4:
                        st.session_state.goal_points[i]["x"] = st.number_input(
                            t["goal_x"].format(i+1), key=f"goal_x_{i}", value=point["x"], format="%.2f")
                    with col5:
                        st.session_state.goal_points[i]["y"] = st.number_input(
                            t["goal_y"].format(i+1), key=f"goal_y_{i}", value=point["y"], format="%.2f")
                    with col6:
                        st.session_state.goal_points[i]["yaw"] = st.number_input(
                            t["goal_yaw"].format(i+1), key=f"goal_yaw_{i}", value=point["yaw"], format="%.2f")

                col_add, col_send = st.columns([1, 1])
                with col_add:
                    add_clicked = st.form_submit_button(t["add_goal_button"])
                with col_send:
                    send_clicked = st.form_submit_button(t["send_nav_button"])

                if add_clicked:
                    st.session_state.goal_points.append({"x": 0.0, "y": 0.0, "yaw": 0.0})

                if send_clicked:
                    if "ros_node" not in st.session_state:
                        st.error(t["ros_node_error"])
                        return

                    goals = [
                        (point["x"], point["y"], point["yaw"])
                        for point in st.session_state.goal_points
                    ]
                    ros_node = st.session_state.ros_node
                    ros_node.set_goal_queue(goals)
                    ros_node.start_navigation()
                    st.success(t["nav_task_success"])
                    st.session_state.show_dialog = False
                    st.rerun()

        st.markdown("""
            <style>
            div[data-testid="stButton"] > button {
                border: none;
                background: none;
                color: #1f77b4;
                padding: 0;
                font-size: 16px;
                cursor: pointer;
            }
            </style>
            """, unsafe_allow_html=True)
        if st.button(t["open_nav_dialog"]):
            show_navigation_dialog()

        st.subheader(t["nav_status_title"])
    
        status_container = st.container()
    
        @st.fragment(run_every=1)  
        def update_navigation_status():
            def load_ui_status():
                try:
                    with open("/home/amr/Desktop/robot_code/ui_status/ui_status.json", "r") as f:
                        return json.load(f)
                except:
                    return {
                        "total_goals": 0,
                        "current_goal_index": 0,
                        "navigation_status": t["status_paused"]
                    }
            def load_yolo_status():
                try:
                    with open("/home/amr/Desktop/robot_code/ui_status/yolo_status.json", "r") as f:
                        return json.load(f)
                except:
                    return {"yolo_detection_result": []}

            data = load_ui_status()
            total_goals = data["total_goals"]
            current_goal_index = data["current_goal_index"]
            navigation_status = data["navigation_status"]
            status_color = {
                "In Progress": "#28a745",
                "Avoiding Obstacle": "#b8860b",
                "Paused": "#595959"
            }
            color = status_color.get(navigation_status, "#ffffff")

            col1, col2, col3 = st.columns(3)

            with col1:
                actual_total = total_goals - 1 if total_goals > 0 else 0
                st.success(t["total_goals"].format(actual_total))

            with col2:
                actual_total = total_goals - 1 if total_goals > 0 else 0
    
                if current_goal_index == 0:
                    st.success(t["current_goal_ready"])
                elif current_goal_index <= actual_total:
                    st.success(t["current_goal_progress"].format(current_goal_index, actual_total))
                else:
                    st.success(t["current_goal_return"])

            with col3:
                st.markdown(
                    f"<div style='background-color:{color}; padding:10px; border-radius:8px; color:white; height:55px; display:flex;align-items:center;left:10px'>"
                    f"<strong>{t['nav_status_label']} {navigation_status}</div>",
                    unsafe_allow_html=True
                )

            yolo_data = load_yolo_status().get("yolo_detection_result", [])

            if yolo_data:
                st.subheader(t["yolo_title"])
                st.table(yolo_data)
            else:
                st.info(t["yolo_no_detection"])
    
        update_navigation_status()

        st.subheader(t["seg_title"])
        image_placeholder = st.empty()
        if "ros_node" in st.session_state and st.session_state["ros_node"] is not None:
            nav_node = st.session_state["ros_node"]

            @st.fragment(run_every=1)
            def update_segmentation_image():
                with nav_node.segmentation_lock:
                    seg_image = nav_node.latest_segmented_image

                if seg_image is not None:
                    seg_rgb = cv2.cvtColor(seg_image, cv2.COLOR_BGR2RGB)
                    seg_pil = Image.fromarray(seg_rgb)
                    image_placeholder.image(seg_pil, caption=t["semantic_caption"], use_container_width=True)
                else:
                    image_placeholder.info(t["waiting_seg"])

            update_segmentation_image()

        else:
            st.warning(t["ros_not_ready"])


        st.subheader(t["end_task_title"])
        if st.button(t["close_nav_button"], key="run_close_command"):
            try:
                try:
                    nav_node.stop_loop_speech() 
                    nav_node.warning_speech_active = False  
                    if nav_node.warning_speech_thread is not None:
                        nav_node.warning_speech_thread.join(timeout=1.0)
                        nav_node.warning_speech_thread = None

                    nav_node.stop_camera_subscription()
                    nav_node.get_logger().info("🔇 All voice announcements stopped")
                except Exception as e:
                    print(f"⚠️ Failed to stop voice: {e}")
                stop_command = "cd ~/Documents/ros2_amr/AMR_script && ./stop_navigation.sh"
                result1 = subprocess.run(stop_command, shell=True, capture_output=True, text=True)

                kill_command = "pkill -f smart_nav_node.py"
                result2 = subprocess.run(kill_command, shell=True, capture_output=True, text=True)

                st.success(t["close_nav_success"])
                st.code(result1.stdout + "\n" + result2.stdout or t["no_output"])
                if result1.stderr or result2.stderr:
                    st.error(t["error_output"].format(result1.stderr, result2.stderr))
            except Exception as e:
                st.error(t["execute_failed"].format(str(e)))

    elif nav_mode == t["nav_modes"][1]:
        col_a, col_b = st.columns([1.2, 1.8])

        with col_a:
            st.text(t["control_panel"])
            st.markdown("---")

            # ---- Step 1 ----
            st.text(t["nav_step1_title"])
            if st.button(t["nav_step1_button"], use_container_width=True):
                with st.spinner(t["nav_step1_loading"]):
                    try:
                        rviz_proc = subprocess.Popen(
                            "cd ~/Documents/ros2_amr/AMR_script && ./run_navigation.sh",
                            shell=True, executable="/bin/bash",
                        )
                        st.session_state["rviz_pid"] = rviz_proc.pid
                        time.sleep(8)
                        st.success(t["nav_step1_success"])
                    except Exception as e:
                        st.error(t["nav_step1_error"].format(error=e))

            # ---- Step 2 ----
            st.text(t["nav_step2_title"])
            if st.button(t["nav_step2_button"], use_container_width=True):
                with st.spinner(t["nav_step2_loading"]):
                    try:
                        cmd = (
                            "cd /home/amr/Desktop/robot_code/ros2_openvino_toolkit/script && "
                            "nohup python3 testgranitenav.py > /home/amr/Desktop/robot_code/semantic_nav.log 2>&1 &"
                        )
                        subprocess.Popen(cmd, shell=True, executable="/bin/bash")

                        log_path = "/home/amr/Desktop/robot_code/semantic_nav.log"
                        start_time = time.time()
                        success_flag = False
                        progress_placeholder = st.empty()

                        while time.time() - start_time < 20:  
                            if os.path.exists(log_path):
                                with open(log_path, "r") as f:
                                    lines = f.readlines()
                                    for line in lines[-10:]:  
                                        if "Loading checkpoint shards: 100%" in line or "ZeroMQ receiver started" in line:
                                            st.success(t["nav_step2_success"])
                                            #st.info("📄 Detailed logs can be viewed in the terminal: tail -f /home/amr/Desktop/robot_code/semantic_nav.log")
                                            success_flag = True
                                            break
                                    if success_flag:
                                        break
                            time.sleep(1)

                        if not success_flag:
                            st.warning(t["nav_step2_warning"])

                    except Exception as e:
                        st.error(t["nav_step2_error"])


            # ---- Step 3 ----
            st.text(t["nav_step3_title"])
            if st.button(t["nav_step3_button"], use_container_width=True):
                with st.spinner(t["nav_step3_loading"]):
                    try:
                        subprocess.Popen(
                            "python3 /home/amr/Desktop/robot_code/ros2_openvino_toolkit/script/set_initial_pose.py",
                            shell=True, executable="/bin/bash",
                        )
                        st.success(t["nav_step3_success"])
                    except Exception as e:
                        st.error(t["nav_step3_error"])

            # ---- Step 4 ----
            st.text(t["nav_step4_title"])
            model = st.selectbox(
                " ",
                [t["nav_step4_select"], "BLIP（CV Model）", "Granite（NLP Model）", "BLIP + Granite（Hybrid）"],
                index=0,
            )
            if model != t["nav_step4_select"]:
                st.success(t["nav_step4_success"].format(model=model))

            # ---- Step 5 ----
            st.text(t["nav_step5_title"])
            task = st.text_area("Enter task content", placeholder=t["nav_step5_placeholder"], label_visibility="collapsed")
            if st.button(t["nav_step5_button"], use_container_width=True):
                if task.strip():
                    try:
                        context = zmq.Context()
                        socket = context.socket(zmq.PUSH)
                        socket.connect("tcp://127.0.0.1:5555")
                        socket.send_string(f"Model selection: {model}")
                        time.sleep(0.2)
                        socket.send_string(task)
                        socket.close()
                        st.success(t["nav_step5_success"].format(task=task))
                    except Exception as e:
                        st.error(t["nav_step5_error"].format(error=e))
                else:
                    st.warning(t["nav_step5_warning"])

            # ---- Step 6 ----
            st.text(t["nav_step6_title"])
            if st.button(t["nav_step6_button"], use_container_width=True):
                with st.spinner(t["nav_step6_loading"]):
                    try:
                        success_msgs = []
                        # 🧩 1️⃣ Shut down Rviz2 and startup scripts
                        stop_nav_cmd = "cd ~/Documents/ros2_amr/AMR_script && ./stop_navigation.sh"
                        result = subprocess.run(stop_nav_cmd, shell=True, capture_output=True, text=True)

                        # 🧩 2️⃣ Shut down semantic navigation backend (Granite + YOLO)
                        subprocess.run("pkill -f testgranitenav.py", shell=True)


                        if result.returncode == 0:
                            st.success(t["nav_step6_success"])
                        else:
                            st.warning(t["nav_step6_warning"].format(warn=result.stderr))

                        log_path = "/home/amr/Desktop/robot_code/semantic_nav.log"
                        if os.path.exists(log_path):
                            os.remove(log_path)
                            success_msgs.append("🧹 Cleaned up temporary log file /home/amr/Desktop/robot_code/semantic_nav.log")
                    except Exception as e:
                        st.error(t["nav_step6_error"])

        with col_b:
            st.text(t["nav_task_order"])
            vue_html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Vue Timeline</title>
                    <!-- Element Plus CSS -->
                    <link rel="stylesheet" href="https://unpkg.com/element-plus/dist/index.css">
                    <!-- Vue 3 + Element Plus -->
                    <script src="https://unpkg.com/vue@3"></script>
                    <script src="https://unpkg.com/element-plus"></script>
                    <style>
                        body {
                            background-color: transparent;
                            color: #e5e7eb;
                            font-family: "Inter", "Noto Sans TC", sans-serif;
                            margin-top: 35px;
                        }
                        .el-timeline {
                            padding-left: 10px;
                            color: #e5e7eb;
                        }
                        .el-timeline-item__node {
                            background-color: #8b5cf6/* Default purple */
                            transition: background-color 0.4s;
                        }
                        .el-timeline-item__node.active {
                            background-color: #22c55e !important; /* Current step turns green */
                        }
                        .el-timeline-item__content {
                            color: #e5e7eb;
                        }
                        .process {
                            background-color: #2b2b3c !important;
                            border: none !important;
                            border-radius: 10px;
                            color: #e5e7eb;
                            transition: all 0.3s ease;
                            padding: 10px;
                        }
                        .process:hover {
                            transform: translateY(-3px);
                            box-shadow: 0 4px 10px rgba(0,0,0,0.4);
                        }
                        .detect-box {
                            margin-top: 25px;
                            text-align: left;
                            font-size: 16px;
                            color: #a5b4fc;
                            font-weight: 500;
                            transition: all 0.3s ease;
                        }
                    </style>
                </head>
                <body>
                    <div id="app">
                        <el-timeline v-if="steps.length > 0" class="timeline-container">
                            <el-timeline-item
                                v-for="(item, idx) in steps"
                                :key="idx"
                                :timestamp="item.type"
                                placement="top"
                                :color="idx === currentStep ? '#22c55e' : '#8b5cf6'"
                            >
                                {{ item.detail }}
                            </el-timeline-item>
                        </el-timeline>

                        <div v-else class="process">
                            <span>🚩 No task data yet or navigation has ended</span>
                        </div>

                        <div v-if="detect_result" class="detect-box">
                            {{ detect_result }}
                        </div>
                        <div v-else class="detect-box" style="opacity:0.5;">
                        
                        </div>
                    </div>

                    <script>
                    const { createApp, ref, onMounted } = Vue

                    createApp({
                        setup() {
                            const steps = ref([])
                            const detect_result = ref(null)
                            const currentStep = ref(null)

                            async function fetchTimeline() {
                                try {
                                    const res = await fetch("http://127.0.0.1:5000/timeline?nocache=" + Date.now())
                                    const data = await res.json()
                                    if (data.status === "ok") {
                                        steps.value = data.steps || []
                                        detect_result.value = data.detect_result
                                        currentStep.value = data.current_step ?? null
                                    } else if (data.status === "finished" || data.status === "no_log") {
                                        steps.value = []
                                        detect_result.value = null
                                    }
                                } catch (e) {
                                    console.log("⏳ Waiting for Flask to return data...")
                                }
                            }

                            onMounted(() => {
                                fetchTimeline()
                                setInterval(fetchTimeline, 2000)
                            })

                            return { steps, detect_result, currentStep }
                        }
                    }).use(ElementPlus).mount('#app')
                    </script>
                </body>
                </html>
                """
            components.html(vue_html, height=600, scrolling=True)
    
        st.markdown('')
        st.markdown('')

        st.text(t["model_response"])
        json_path = "/home/amr/Desktop/robot_code/granite_picture/summary.json"
        latest_data = None
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data = [data]  
                if isinstance(data, list) and data:
                    latest_data = data
        except Exception as e:
            pass
            #st.warning(f"Unable to load JSON: {e}")

        latest_json = json.dumps(latest_data, ensure_ascii=False) if latest_data else "[]"

        vue_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        <title>Latest Navigation Results</title>
        <link rel="stylesheet" href="https://unpkg.com/element-plus/dist/index.css">
        <script src="https://unpkg.com/vue@3"></script>
        <script src="https://unpkg.com/element-plus"></script>

        <style>
            body {{
            background-color: transparent;
            color: #e5e7eb;
            font-family: "Inter", "Noto Sans TC", sans-serif;
            margin: 0;
            padding: 10px;
            }}
            ::-webkit-scrollbar {{
            width: 0px;
            background: transparent;
            }}
            .flex {{
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            justify-content: flex-start;
            }}
            .el-card {{
            background-color: #2b2b3c !important;
            border: none !important;
            border-radius: 10px;
            color: #e5e7eb;
            width: 520px;
            transition: all 0.3s ease;
            }}
            .el-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 4px 10px rgba(0,0,0,0.4);
            }}
            .preview-image {{
                width: 100%;
                height: 230px;              /* Fixed height, uniform ratio */
                object-fit: cover;          /* No distortion */
                border-radius: 10px;
                background-color: #0f0f0f;  /* Background fill color */
                box-shadow: 0 3px 10px rgba(0, 0, 0, 0.3);
                margin-bottom: 12px;
            }}
            .time{{
                font-weight: 600;
                font-size: 15px;
                color: #c7d2fe;
                margin-bottom: 10px;
            }}
            .caption {{
            font-weight: 600;
            font-size: 15px;
            color: #c7d2fe;
            margin-top: 10px;
            }}
            .description {{
            font-weight: 600;
            font-size: 15px;
            color: #c7d2fe;
            line-height: 1.6;
            margin-top: 8px;
            text-align: justify;
            }}
        </style>
        </head>

        <body>
        <div id="app">
            <div class="flex">
            <template v-if="results.length > 0">
                <el-card
                    v-for="(item, idx) in results"
                    :key="idx"
                    shadow="always"
                >
                    <div class="time">⏰ Generated time: {{{{ item.generated_time }}}}</div>
                    <img
                        v-if="item.filename"
                        :src="'http://127.0.0.1:5000/images/' + item.filename"
                        alt="Captured image"
                        class="preview-image"
                    />
                    <div class="caption">🪶 BLIP caption: {{{{ item.blip_caption }}}}</div>
                    <div class="description">📘 Granite generated: {{{{ item.description }}}}</div>
                </el-card>
            </template>
            <el-card shadow="never" v-else>
                <p style="color:gray;text-align: center;">No response received yet</p>
            </el-card>
            </div>
        </div>

        <script>
            const {{ createApp, ref, onMounted }} = Vue
            createApp({{
            setup() {{
                const results = ref([])
                onMounted(() => {{
                    setInterval(async () => {{
                        try {{
                        const res = await fetch("http://127.0.0.1:5000/data?nocache=" + Date.now())
                        if (!res.ok) return
                        const data = await res.json()
                        const list = data.model_results || []
                        if (Array.isArray(list) && list.length > 0) {{
                            const now = new Date()
                            const valid = list.filter(item => {{
                            if (!item.generated_time) return false
                            const genTime = new Date(item.generated_time)
                            const diffHours = (now - genTime) / (1000 * 60 * 60)
                            return diffHours <= 2 
                            }})

                            results.value = valid.reverse()
                        }}
                        }} catch (e) {{
                        console.log("⏳ Waiting for Flask to return data...")
                        }}
                    }}, 2000)
                }})
                return {{ results }}
            }}
            }}).use(ElementPlus).mount('#app')
        </script>
        </body>
        </html>
        """

        components.html(vue_html, height=500, scrolling=True)


