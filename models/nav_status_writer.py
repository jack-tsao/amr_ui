"""JSON status writers and path plotting helpers.

These functions used to live on :class:`SmartNavNode`. They've been
pulled out as module-level free functions so they can be called from
the node without dragging rclpy into this file.

IMPORTANT: The JSON keys ``yolo_detection_result`` and ``save_time`` are
consumed by ``views/logs.py`` and ``views/navigation.py`` — do NOT rename
them. File paths must also remain identical to what the old monolithic
node wrote.
"""

import os
import json
import csv
from datetime import datetime

import matplotlib.pyplot as plt


UI_STATUS_PATH = "/home/amr/Desktop/robot_code/ui_status/ui_status.json"
YOLO_STATUS_PATH = "/home/amr/Desktop/robot_code/ui_status/yolo_status.json"
YOLO_FULL_LOG_PATH = "/home/amr/Desktop/robot_code/ui_status/yolo_full_log.json"


def update_ui_status(logger, total_goals, current_goal_index,
                     navigation_active, is_avoiding_obstacle):
    """Write the ``ui_status.json`` file that the Streamlit UI reads."""
    status = "Avoiding Obstacle" if is_avoiding_obstacle else (
        "In Progress" if navigation_active else "Paused")

    ui_data = {
        "total_goals": total_goals,
        "current_goal_index": current_goal_index,
        "navigation_status": status
    }

    try:
        with open(UI_STATUS_PATH, "w") as f:
            json.dump(ui_data, f, ensure_ascii=False, indent=2)
        logger.debug("✅ UI JSON status updated")
    except Exception as e:
        logger.warn(f"❗ Failed to write ui_status.json: {e}")


def save_yolo_detections_to_json(logger, detections_for_ui):
    """Write the current frame's detections and append to the rolling log."""
    try:
        detection_data = {
            "yolo_detection_result": detections_for_ui
        }
        with open(YOLO_STATUS_PATH, "w") as f:
            json.dump(detection_data, f, ensure_ascii=False, indent=2)
        logger.debug("✅ YOLO JSON status updated")

        log_path = YOLO_FULL_LOG_PATH

        if os.path.exists(log_path):
            file_size = os.path.getsize(log_path)
            if file_size > 10 * 1024 * 1024:
                logger.info("📁 YOLO log file too large, starting a new log")
                data = []
            else:
                try:
                    with open(log_path, "r") as f:
                        data = json.load(f)
                    if not isinstance(data, list):
                        data = []
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON file corrupted, starting a new log: {e}")
                    data = []
                except Exception as e:
                    logger.error(f"❌ Failed to read JSON file, starting a new log: {e}")
                    data = []
        else:
            data = []

        data.append(detection_data)

        if len(data) > 1000:
            data = data[-1000:]

        with open(log_path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug("✅ YOLO detection results appended")
    except Exception as e:
        logger.warn(f"❗ Failed to write yolo_status.json: {e}")


def append_save_time_to_yolo_log(logger):
    """Append a timestamp marker to the rolling YOLO log."""
    try:
        log_path = YOLO_FULL_LOG_PATH

        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                data = json.load(f)
            if not isinstance(data, list):
                data = []
        else:
            data = []

        data.append({
            "save_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        with open(log_path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info("🕒 Save time appended to the end of the YOLO log")

    except Exception as e:
        logger.error(f"❗ Failed to write save time: {e}")


def plot_path(logger, path_history, goal_path):
    """Plot the actual vs planned path and dump a CSV for Streamlit."""
    if not path_history:
        logger.warn("⚠️ No path data available to plot")
        return

    actual_x, actual_y = zip(*path_history)

    plan_x, plan_y = [], []
    if goal_path and len(goal_path) > 0:
        plan_x, plan_y = zip(*goal_path)

    plt.figure()
    plt.plot(actual_x, actual_y, marker='o', linestyle='-', color='blue', label='Real Route')
    if plan_x and plan_y:
        plt.plot(plan_x, plan_y, marker='x', linestyle='--', color='red', label='Plan Route')

    plt.title("Robot Navigation Path")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.grid(True)
    plt.axis('equal')
    plt.legend()

    plot_path_out = os.path.expanduser("~/Desktop/robot_code/picture_record/path_plot.png")
    plt.savefig(plot_path_out)
    plt.show()
    plt.close()
    logger.info(f"📈 Robot path saved to: {plot_path_out}")

    csv_path = os.path.expanduser("~/Desktop/robot_code/picture_record/path_data_for_streamlit.csv")
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        max_len = max(len(actual_x), len(plan_x) if plan_x else 0)
        rows = []
        for i in range(max_len):
            row = {
                "Real_X": actual_x[i] if i < len(actual_x) else None,
                "Real_Y": actual_y[i] if i < len(actual_y) else None,
                "Plan_X": plan_x[i] if plan_x and i < len(plan_x) else None,
                "Plan_Y": plan_y[i] if plan_y and i < len(plan_y) else None,
            }
            rows.append(row)
        time_row = {
            "Real_X": "GeneratedTime",
            "Real_Y": current_time,
            "Plan_X": None,
            "Plan_Y": None
        }
        rows.append(time_row)

        with open(csv_path, mode='w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Real_X", "Real_Y", "Plan_X", "Plan_Y"])
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"📄 Robot path data saved to: {csv_path}")
    except Exception as e:
        logger.error(f"❌ Failed to save CSV: {e}")


def save_goal_log(logger, pose, obstacle_detected):
    """Append a goal completion row to ``goal_log.csv``.

    Returns the ``(x, y, yaw_deg)`` written so the caller can log further.
    """
    import math

    log_dir = os.path.expanduser("~/Desktop/robot_code/record")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "goal_log.csv")

    q = pose.pose.orientation
    yaw_rad = math.atan2(
        2.0 * (q.w * q.z + q.x * q.y),
        1.0 - 2.0 * (q.y ** 2 + q.z ** 2)
    )
    yaw_deg = math.degrees(yaw_rad)

    x = pose.pose.position.x
    y = pose.pose.position.y
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    goal_status = "success"
    wait_time = 22.0
    obstacle_flag = "yes" if obstacle_detected else "no"

    write_header = not os.path.exists(log_path)
    with open(log_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if write_header:
            writer.writerow(["x", "y", "orientation_yaw", "timestamp", "goal_status", "wait_time", "obstacle_encountered"])
        writer.writerow([x, y, yaw_deg, timestamp, goal_status, wait_time, obstacle_flag])

    logger.info(f"📝 Navigation log: ({x:.2f}, {y:.2f}) | heading {yaw_deg:.1f}° | obstacle: {obstacle_flag}")
    return (x, y, yaw_deg)
