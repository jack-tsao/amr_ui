# Advantech AMR UI

A Streamlit control panel for the Advantech AMR (Autonomous Mobile Robot).
One web UI to start/stop the LIDAR, drive the camera pipeline, launch
navigation, trigger text-to-speech, and read hardware telemetry from SUSI.

## Background

This application is a refactor of the original single-file prototype
`streamlit_distance.py` (now kept for reference under
`script/archive/streamlit_distance.py`). That file was a ~1000+ line script
that mixed ROS orchestration, UI, i18n, styling, and subprocess handling. It
has been split into the `amr_ui/` package:

- `models/`, ROS node, YOLO detector, TTS player, JSON status writers.
- `views/`, one file per page in the sidebar.
- `ui/`, header, sidebar, router, health strip, styles.
- `config/`, session defaults and locale loader.
- `locales/`, zh_TW / ja / ko / en JSON.
- `utils/`, small helpers (health probes, file loaders, math).

Behavior is the same; the goal was readability and so individual pieces can
be worked on without touching the rest.

---

## ⚠️ Watch the tutorial videos first

Two walkthrough videos sit next to this README:

- **`AMR Tutorial.mp4`**, the **terminal-based** workflow: every step run
  by hand in a shell. Watch this if you prefer not to use this Streamlit
  UI, or when you need to debug what the UI is doing under the hood.
- **`AMR demo English　George.mp4`**, the **UI walkthrough** in English,
  covering the same flow driven through this application.

If you don't want to use this Streamlit app at all, that's fine: follow
`AMR Tutorial.mp4` and run each command directly in a terminal. The UI is
just a convenience layer over those same commands.

**Please watch both before touching anything, and mimic every step exactly as
shown.** The videos cover hardware quirks, launch order, and recovery steps
that aren't written down anywhere else. If the UI behaves unexpectedly,
re-watch the relevant section before escalating, almost every answer is in
the video.

The `.mp4` files are too large for git and are listed in `.gitignore`, they
stay on the robot as local reference material.

---

## Starting the application

You are not pulling this from git, the project already lives at
`/home/amr/Desktop/robot_code/ros2_openvino_toolkit/script/amr_ui/`. On the AMR robot
To run it, open a terminal and:

```bash
cd /home/amr/Desktop/robot_code/ros2_openvino_toolkit/script
streamlit run amr_ui/main.py
```

Streamlit prints a local URL (usually <http://localhost:8501>), open it in
a browser.

### When do I need to source ROS2?

**Not on every new terminal.** Sourcing is only required when:

- A ROS message definition has changed and the `adv_msgs` / `edge-data-client`
  workspaces were rebuilt.
- You just opened a completely fresh shell without the `.bashrc` env.

If you're reusing the same terminal you started the robot from, you're already
sourced. When you do need to re-source, run:

```bash
source /opt/ros/foxy/setup.bash
source /usr/local/Advantech/ros/foxy/include/edge-converter-ros2/adv_msgs/install/local_setup.bash
source /usr/local/Advantech/ros/foxy/sample_code/edge-data-client/install/local_setup.bash
```

## UI walkthrough

Each item in the left sidebar corresponds to a file in `amr_ui/views/`.

### 🏠 Home
Landing page with a short project summary. Also contains a **chatbot
section that is not functional**, it's wired to OpenAI's GPT-3.5 with a
placeholder key. If you want an LLM assistant here, replace the `OpenAI`
client setup in [`views/home.py`](views/home.py) with your own key / endpoint
(or swap in a local model). As-is, expect that panel to error out, that's
expected until someone implements it.

### 📡 Radar (LIDAR)
Launches the RPLIDAR driver via a shell command and displays the live scan.
Use this page to confirm the LIDAR is publishing before attempting
navigation.

> ⚠️ **Always stop the scan when you're done.** If you leave the radar /
> scanning process running, it holds `/dev/ttyUSB0` and blocks every other
> application that needs the LIDAR (navigation, SLAM, etc.). Press the stop
> button on this page before moving on to Navigation or Camera.

### 🗺️ Navigation
The operational core of the app. Follow this order every time:

1. **Run the navigation launch command** shown at the top of the page.
2. **Wait for RViz to fully load**, do not click anything in the UI until
   the RViz window appears and the map/robot model are visible.
3. **Press the "Start navigation node" button** in the UI. This spins up
   `SmartNavNode` and hooks it into the running Nav2 stack.
4. **Set the robot's initial pose** before sending goals. Either:
   - Open the navigation dialog in the UI and send a starting position, **or**
   - Use **"2D Pose Estimate"** in RViz to drop the pose directly on the map.
5. Only then send goals via the dialog or rviz

Skipping step 2 or 4 is the most common cause of "Fixed Frame [map] does not
exist" and goals being silently rejected.

- **Open navigation dialog**, select goals from the saved goal table and
  push them to the queue.
- **Status strip**, total-goals / current-goal / status pills. Data comes
  from the JSON handshake at
  `/home/amr/Desktop/robot_code/ui_status/ui_status.json`, written by
  `SmartNavNode` and refreshed every second.
- **YOLO detections table**, populated from `ui_status/yolo_status.json`
  when the camera pipeline is running.
- **Semantic segmentation preview**, latest annotated frame from the YOLO
  node.
- **End task**, runs `stop_navigation.sh` and stops all TTS.

### 📷 Camera
Starts the camera ROS node and shows the live JPEG stream
(`/home/amr/Desktop/robot_code/camera/frame.jpg`). The bottom half is a
simple WASD-style tele-op that publishes on `/cmd_vel`.

### 📟 Status (SUSI)
Starts `susi.py` (`script/susi.py`), which subscribes to `/adv/susicontrol`,
filters for 10 target sensors (voltages, temperatures, fan RPM, disk,
case-open), and snapshots them every ~120 s into
`/home/amr/Desktop/robot_code/susi/susi_data.json`. The view re-reads that
file on a 2-second autorefresh and renders color-coded cards. Data older
than 5 minutes is flagged as stale.

### 📝 Logs
Displays `ui_status/goal_log.json` and `ui_status/yolo_log.json` so you can
audit recent navigation goals and object detections.

### ⚙️ Settings
- **Power / Reboot**, `sudo poweroff`, `sudo reboot`.
- **Language**, 繁體中文 / 日本語 / 한국어 / English. Strings live in
  `amr_ui/locales/*.json`.
- **Theme**, Dark (default) / Light. Light mode injects a CSS override on
  top of the base stylesheet.
- **Contact cards**, project owners.
- **Logout**, clears `st.session_state` (auth is currently bypassed in
  `main.py`).

---

## Health strip

Across the top of every page, colored dots show the live status of:

- **ROS2**, via `pgrep -f ros2`.
- **LIDAR**, `/dev/ttyUSB0` presence + readability.
- **Camera**, `/dev/video0` presence.
- **Display**, `$DISPLAY` env var.
- **Nav**, freshness of `ui_status.json` (< 10 s = ok).

Green / yellow / red = ok / warn / fail. Probes are non-blocking, see
[`utils/health_check.py`](utils/health_check.py).

---

## System dependencies

- `espeak-ng`, English TTS engine used for loop / warning / arrival /
  goodbye announcements. Install with `sudo apt install espeak-ng`.
- `alsa-utils`, provides `aplay` to play synthesized wavs.

---

## Questions

**Anything robot-related** (hardware, Nav2, SLAM, Cartographer, launch
scripts, network/DDS setup), ask **Ryan**.

For UI-layer issues, start with the troubleshooting list below; if it's not
covered, re-watch the tutorial before escalating.

### Troubleshooting

- **Streamlit page looks stale**, hit `R` to rerun, or restart the
  `streamlit run` process.
- **No SUSI data on Status page**, confirm `susi.py` is running,
  `/adv/susicontrol` is publishing (`ros2 topic hz /adv/susicontrol`), and
  `susi_data.json` exists and is < 5 min old.
- **Navigation not working / goals rejected / robot not moving**, first ask
  yourself: did you follow **every** step in the Navigation section exactly,
  in order? Wait for RViz, press "Start navigation node", set the initial
  pose, *then* send goals. Skipping or reordering any step will break it.
- **LIDAR not detected / `/dev/ttyUSB0` busy**, same question: did you follow
  every step in the Radar section exactly? Also check you stopped any
  previous scan before starting a new one, a lingering scan process locks
  the device.
- **RViz: "Fixed Frame [map] does not exist"**, Cartographer is down or not
  receiving scans. Restart the SLAM stack.
- **TTS garbled / "laggy"**, verify `espeak-ng` is installed (not the old
  Japanese `open_jtalk` engine).
- **Chatbot on Home page errors out**, expected; LLM integration is not
  implemented. Wire up your own key in `views/home.py`.
