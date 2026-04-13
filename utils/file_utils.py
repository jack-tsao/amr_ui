import json
import math
import os


_SUSI_PATH = "/home/amr/Desktop/robot_code/susi/susi_data.json"


def load_susi_json():
    """Read susi_data.json fresh from disk every call.

    No caching: the file is rewritten by ``susi.py`` every ~120s and the UI
    needs to pick up the new snapshot on the next rerun.
    """
    if not os.path.exists(_SUSI_PATH):
        return {"error": f"file not found: {_SUSI_PATH}"}
    try:
        with open(_SUSI_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return {"error": str(e)}


def euler2quat(roll, pitch, yaw):
    """Convert Euler angles to quaternion."""
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)

    qw = cr * cp * cy + sr * sp * sy
    qx = sr * cp * cy - cr * sp * sy
    qy = cr * sp * cy + sr * cp * sy
    qz = cr * cp * sy - sr * sp * cy

    return [qw, qx, qy, qz]
