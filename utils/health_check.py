"""Lightweight runtime health probes for the AMR UI status strip.

Each probe returns a (status, detail) tuple where status is one of:
    "ok"   — component is reachable / alive
    "warn" — reachable but degraded or unknown
    "fail" — component is unreachable or errored

Probes must be cheap and non-blocking; they run on every Streamlit rerun.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List

_LIDAR_DEVICE = "/dev/ttyUSB0"
_VIDEO_DEVICE = "/dev/video0"
_UI_STATUS_JSON = Path("/home/amr/Desktop/robot_code/ui_status/ui_status.json")


@dataclass(frozen=True)
class HealthStatus:
    name: str
    status: str   # "ok" | "warn" | "fail"
    detail: str


def check_lidar() -> HealthStatus:
    if not os.path.exists(_LIDAR_DEVICE):
        return HealthStatus("LIDAR", "fail", "device missing")
    if not os.access(_LIDAR_DEVICE, os.R_OK):
        return HealthStatus("LIDAR", "warn", "no read permission")
    return HealthStatus("LIDAR", "ok", _LIDAR_DEVICE)


def check_camera() -> HealthStatus:
    if not os.path.exists(_VIDEO_DEVICE):
        return HealthStatus("Camera", "fail", "no /dev/video0")
    return HealthStatus("Camera", "ok", _VIDEO_DEVICE)


def check_display() -> HealthStatus:
    display = os.environ.get("DISPLAY")
    if not display:
        return HealthStatus("Display", "warn", "DISPLAY unset")
    return HealthStatus("Display", "ok", display)


def check_ros() -> HealthStatus:
    """Detect whether any ROS2 daemon is running. Cheap — just checks the CLI."""
    if shutil.which("ros2") is None:
        return HealthStatus("ROS2", "fail", "ros2 CLI not found")
    try:
        result = subprocess.run(
            ["pgrep", "-f", "ros2"],
            capture_output=True,
            text=True,
            timeout=0.5,
        )
        if result.returncode == 0:
            return HealthStatus("ROS2", "ok", "active")
        return HealthStatus("ROS2", "warn", "no processes")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return HealthStatus("ROS2", "warn", "probe timeout")


def check_nav_status() -> HealthStatus:
    """Check whether the nav status JSON file is recent (written by SmartNavNode)."""
    if not _UI_STATUS_JSON.exists():
        return HealthStatus("Nav", "warn", "no status file")
    try:
        import time
        age = time.time() - _UI_STATUS_JSON.stat().st_mtime
    except OSError as e:
        return HealthStatus("Nav", "fail", f"stat error: {e}")
    if age > 10:
        return HealthStatus("Nav", "warn", f"stale ({int(age)}s)")
    return HealthStatus("Nav", "ok", f"{int(age)}s ago")


def run_all_probes() -> List[HealthStatus]:
    return [
        check_ros(),
        check_lidar(),
        check_camera(),
        check_display(),
        check_nav_status(),
    ]
