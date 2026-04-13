"""Thin orchestration layer for the SmartNavNode.

This module used to be a ~1055-line monolith that mixed YOLO, TTS,
status writing and path plotting. Those concerns now live in:

- :mod:`amr_ui.models.yolo_detector`
- :mod:`amr_ui.models.tts_player`
- :mod:`amr_ui.models.nav_status_writer`

``SmartNavNode`` keeps all rclpy subscriptions, timers, callbacks and
the navigation state machine, delegating the heavy lifting to the
helpers. The public name and module path are unchanged so that
``from amr_ui.models.smart_nav_node import SmartNavNode`` in
``amr_ui/utils/ros_utils.py`` keeps working.
"""

import time
import math
import threading

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import Twist, PoseWithCovarianceStamped, PoseStamped
from sensor_msgs.msg import Image as RosImage
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import String  # noqa: F401 (kept for parity with prior imports)
from cv_bridge import CvBridge

from amr_ui.utils.file_utils import euler2quat
from amr_ui.models.yolo_detector import YoloDetector
from amr_ui.models.tts_player import TtsPlayer
from amr_ui.models.nav_status_writer import (
    update_ui_status as _write_ui_status,
    save_yolo_detections_to_json as _write_yolo_detections,
    append_save_time_to_yolo_log as _append_yolo_save_time,
    plot_path as _plot_path,
    save_goal_log as _save_goal_log,
)


class SmartNavNode(Node):
    def __init__(self):
        super().__init__('smart_nav_node')

        self.bridge = CvBridge()

        self.rgb_subscription = None
        self.depth_subscription = None

        self.pose_subscription = self.create_subscription(
            PoseWithCovarianceStamped,
            '/amcl_pose',
            self.pose_callback,
            10
        )

        self.cmd_vel_publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        self.nav_action_client = ActionClient(self, NavigateToPose, '/navigate_to_pose')

        # --- YOLO detector + segmentation --------------------------------
        self.yolo = YoloDetector(self.get_logger())
        # Back-compat shims so callers that used node.model / node.seg_model still work.
        self.model = self.yolo.model
        self.seg_model = self.yolo.seg_model
        self.seg_colors = self.yolo.seg_colors

        self.latest_segmented_image = None
        self.latest_rgb_image = None
        self.segmentation_lock = threading.Lock()
        self.current_detections = []
        self.current_segmentation_results = []

        # --- Depth / obstacle-avoidance state ----------------------------
        self.latest_depth_image = None
        self.avoidance_mode = False
        self.distance_threshold = 1.0
        self.ui_obstacle_threshold = 0.5
        self.safe_counter = 0
        self.safe_threshold = 20

        # --- Navigation state --------------------------------------------
        self.home_position = None
        self.home_orientation = None
        self.home_position_saved = False

        self.goal_queue = []
        self.original_goal_count = 0
        self.returning_home = False
        self.current_goal_pose = None
        self.wait_timer = None
        self.path_history = []
        self.goal_path = []
        self.navigation_resumed = False
        self.is_waiting = False
        self.obstacle_detected_during_this_goal = False
        self.home_position = None
        self.home_orientation = {'x': 0.0, 'y': 0.0, 'z': 0.0, 'w': 1.0}
        self.is_navigating = False
        self.current_goal_index = 0
        self.total_goals = 0
        self.navigation_active = False
        self.is_avoiding_obstacle = False

        # --- TTS player ---------------------------------------------------
        self.tts = TtsPlayer(
            self.get_logger(),
            navigation_state=lambda: (self.navigation_active, self.is_avoiding_obstacle),
        )

        self.camera_initialized = False
        self.max_log_size = 10 * 1024 * 1024  # 10MB
        self.max_log_entries = 1000

        self.get_logger().info("🟢 Smart navigation node started")
        self.ui_timer = self.create_timer(1.0, self.update_ui_status)
        self.detections_for_ui = []
        self.detection_timer = self.create_timer(1.0, self.save_yolo_detections_to_json)

        self.get_logger().info("⏳ Camera will be initialized in 2 seconds...")
        self.camera_init_timer = self.create_timer(2.0, self.delayed_camera_initialization)

    # ------------------------------------------------------------------
    # Back-compat properties for speech state (preserve old attribute API)
    # ------------------------------------------------------------------
    @property
    def keep_speaking(self):
        return self.tts.keep_speaking

    @keep_speaking.setter
    def keep_speaking(self, value):
        self.tts.keep_speaking = value

    @property
    def speech_thread(self):
        return self.tts.speech_thread

    @property
    def warning_speech_active(self):
        return self.tts.warning_speech_active

    @warning_speech_active.setter
    def warning_speech_active(self, value):
        self.tts.warning_speech_active = value

    @property
    def warning_speech_thread(self):
        return self.tts.warning_speech_thread

    @warning_speech_thread.setter
    def warning_speech_thread(self, value):
        self.tts.warning_speech_thread = value

    @property
    def normal_speech_paused(self):
        return self.tts.normal_speech_paused

    @property
    def current_audio_process(self):
        return self.tts.current_audio_process

    # ------------------------------------------------------------------
    # Camera initialization
    # ------------------------------------------------------------------
    def delayed_camera_initialization(self):
        """Delayed initialization of camera subscriptions"""
        try:
            self.get_logger().info("🎥 Starting camera subscription initialization...")

            self.rgb_subscription = self.create_subscription(
                RosImage,
                '/camera/color/image_raw',
                self.image_callback,
                10
            )

            self.depth_subscription = self.create_subscription(
                RosImage,
                '/camera/aligned_depth_to_color/image_raw',
                self.depth_callback,
                10
            )

            self.camera_initialized = True

            self.get_logger().info("✅ Camera subscription initialization complete")

            if self.camera_init_timer is not None:
                self.camera_init_timer.cancel()
                self.camera_init_timer = None

        except Exception as e:
            self.get_logger().error(f"❌ Camera initialization failed: {e}")
            self.get_logger().info("🔄 Retrying camera initialization in 5 seconds...")
            if self.camera_init_timer is not None:
                self.camera_init_timer.cancel()
            self.camera_init_timer = self.create_timer(5.0, self.delayed_camera_initialization)

    # ------------------------------------------------------------------
    # Status writing (delegates to nav_status_writer)
    # ------------------------------------------------------------------
    def update_ui_status(self):
        _write_ui_status(
            self.get_logger(),
            total_goals=self.total_goals,
            current_goal_index=self.current_goal_index,
            navigation_active=self.navigation_active,
            is_avoiding_obstacle=self.is_avoiding_obstacle,
        )

    def save_yolo_detections_to_json(self):
        _write_yolo_detections(self.get_logger(), self.detections_for_ui)

    def append_save_time_to_yolo_log(self):
        _append_yolo_save_time(self.get_logger())

    def plot_path(self):
        _plot_path(self.get_logger(), self.path_history, self.goal_path)

    # ------------------------------------------------------------------
    # TTS pass-throughs (preserve the original method names used by views)
    # ------------------------------------------------------------------
    def pause_normal_speech(self):
        self.tts.pause_normal_speech()

    def resume_normal_speech(self):
        self.tts.resume_normal_speech()

    def play_warning_speech(self):
        self.tts.play_warning_speech()

    def start_loop_speech(self):
        self.tts.start_loop_speech()
        # Starting loop speech means we're no longer actively avoiding an obstacle.
        self.is_avoiding_obstacle = False

    def stop_loop_speech(self):
        self.tts.stop_loop_speech()

    def stop_all_speech(self):
        self.tts.stop_all_speech()
        self.is_avoiding_obstacle = False

    def play_arrival_speech(self):
        self.tts.play_arrival_speech(self.returning_home)

    def play_goodbye_speech(self):
        def _on_done():
            if hasattr(self, 'goodbye_timer') and self.goodbye_timer is not None:
                self.goodbye_timer.cancel()
                self.goodbye_timer = None
        self.tts.play_goodbye_speech(on_done=_on_done)

    # ------------------------------------------------------------------
    # Navigation orchestration
    # ------------------------------------------------------------------
    def start_navigation(self):
        if not self.goal_queue:
            self.get_logger().warn("⚠️ Goal list is empty, cannot start navigation")
            return

        if not self.camera_initialized:
            self.get_logger().info("🎥 Camera not yet started, beginning reinitialization...")
            self.delayed_camera_initialization()

        self.start_loop_speech()

        self.get_logger().info("🚦 Starting to process navigation queue")
        self.process_next_goal()

    def pose_callback(self, msg):
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y

        if not self.home_position_saved:
            self.home_position = (x, y)
            self.home_orientation = {
                'x': msg.pose.pose.orientation.x,
                'y': msg.pose.pose.orientation.y,
                'z': msg.pose.pose.orientation.z,
                'w': msg.pose.pose.orientation.w
            }
            self.home_position_saved = True
            self.get_logger().info(f"🏠 Home position recorded: ({x:.3f}, {y:.3f})")

        if not self.path_history or math.hypot(x - self.path_history[-1][0], y - self.path_history[-1][1]) > 0.05:
            self.path_history.append((x, y))

    def set_goal_queue(self, goals):
        self.goal_queue = goals.copy()
        self.original_goal_count = len(goals)
        self.goal_path = []
        self.total_goals = len(goals) + 1
        self.update_ui_status()
        for i, goal in enumerate(goals):
            x, y, yaw_deg = goal
            self.get_logger().info(f"📋 Goal {i+1}: ({x:.2f}, {y:.2f}) angle: {yaw_deg:.1f}°")
        self.get_logger().info(f"📋 Set {len(goals)} navigation goals + 1 home point")

    def navigate_to_pose(self, pose_msg):
        self.current_goal_pose = pose_msg
        if not self.nav_action_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error("❌ Navigation server not ready")
            return
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = pose_msg
        self.get_logger().info("🚀 Sending navigation command...")
        send_goal_future = self.nav_action_client.send_goal_async(goal_msg)
        send_goal_future.add_done_callback(self.goal_done_callback)

    def goal_done_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn("⚠️ Navigation goal was rejected")
            return
        self.get_logger().info("🟢 Navigation goal accepted, executing...")
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.navigation_result_callback)

    def navigation_result_callback(self, future):
        """Navigation result callback - fixed version"""
        self.get_logger().info("📬 Received navigation completion callback")
        result = future.result().result
        self.get_logger().info(f'🌟 Navigation complete, result: {result}')

        self.get_logger().info("🚫 Robot has stopped")

        self.stop_all_speech()

        time.sleep(0.3)

        self.play_arrival_speech()

        if self.returning_home:
            self.get_logger().info("🏠 Arrived at home point")
        else:
            self.get_logger().info("🎯 Arrived at goal point")

        self.get_logger().info("⏳ Waiting for 22 seconds...")

        self.save_goal_log(self.current_goal_pose)
        self.navigation_resumed = False
        self.navigation_active = False
        self.is_waiting = True
        self.update_ui_status()

        if self.wait_timer is not None:
            self.wait_timer.cancel()
        self.wait_timer = self.create_timer(22.0, self.wait_completed_callback)

        if not self.returning_home:
            self.goodbye_timer = self.create_timer(20.0, self.play_goodbye_speech)

    def save_goal_log(self, pose):
        _save_goal_log(
            self.get_logger(),
            pose,
            obstacle_detected=self.obstacle_detected_during_this_goal,
        )
        self.obstacle_detected_during_this_goal = False

    def wait_completed_callback(self):
        if self.wait_timer is not None:
            self.wait_timer.cancel()
            self.wait_timer = None

        if hasattr(self, 'goodbye_timer') and self.goodbye_timer is not None:
            self.goodbye_timer.cancel()
            self.goodbye_timer = None

        self.is_waiting = False
        self.update_ui_status()
        self.get_logger().info("⌛ Wait time finished")

        if self.returning_home:
            self.plot_path()
            self.append_save_time_to_yolo_log()
            self.get_logger().info("✅ Returned to home, all tasks complete, waiting for new goals...")

            self.returning_home = False
            self.navigation_active = False
            self.goal_queue = []
            self.current_goal_index = 0
            self.total_goals = 0
            self.navigation_resumed = False
            self.update_ui_status()

        else:
            self.process_next_goal()

    def process_next_goal(self):
        """Process next goal - fixed version"""
        self.navigation_resumed = False

        completed_goals = self.original_goal_count - len(self.goal_queue)

        if len(self.goal_queue) == 0 and completed_goals >= self.original_goal_count:
            if self.home_position is None:
                self.get_logger().warn("⚠️ Home position not recorded, cannot return home")
                self.plot_path()
                self.append_save_time_to_yolo_log()
                self.get_logger().info("✅ All goals completed, waiting for new tasks...")

                self.returning_home = False
                self.navigation_active = False
                self.goal_queue = []
                self.current_goal_index = 0
                self.total_goals = 0
                self.navigation_resumed = False
                self.update_ui_status()

                return

            self.stop_all_speech()
            time.sleep(0.5)

            self.start_loop_speech()
            self.get_logger().info("🔊 Starting to return home, restarting loop speech playback")

            self.returning_home = True
            self.current_goal_index += 1
            self.navigation_active = True
            self.update_ui_status()

            goal = PoseStamped()
            goal.header.frame_id = 'map'
            goal.pose.position.x = self.home_position[0]
            goal.pose.position.y = self.home_position[1]
            goal.pose.position.z = 0.0
            goal.pose.orientation.x = self.home_orientation['x']
            goal.pose.orientation.y = self.home_orientation['y']
            goal.pose.orientation.z = self.home_orientation['z']
            goal.pose.orientation.w = self.home_orientation['w']

            self.get_logger().info(f"🏠 Returning to home point: ({self.home_position[0]:.2f}, {self.home_position[1]:.2f})")
            self.navigate_to_pose(goal)
            return

        if self.goal_queue:
            next_goal = self.goal_queue.pop(0)
            x, y, yaw_deg = next_goal

            self.goal_path.append((x, y))

            self.current_goal_index += 1
            self.navigation_active = True
            self.update_ui_status()

            self.stop_all_speech()
            time.sleep(0.5)

            self.start_loop_speech()
            self.get_logger().info("🔊 Heading to next goal, restarting loop speech playback")

            goal = PoseStamped()
            goal.header.frame_id = 'map'
            goal.pose.position.x = x
            goal.pose.position.y = y
            goal.pose.position.z = 0.0

            yaw_rad = math.radians(yaw_deg)
            quat = euler2quat(0.0, 0.0, yaw_rad)

            goal.pose.orientation.w = quat[0]
            goal.pose.orientation.x = quat[1]
            goal.pose.orientation.y = quat[2]
            goal.pose.orientation.z = quat[3]

            self.get_logger().info(f"🎯 Heading to next goal: ({x:.2f}, {y:.2f}) angle: {yaw_deg:.1f}°")
            self.navigate_to_pose(goal)

    # ------------------------------------------------------------------
    # Perception callbacks
    # ------------------------------------------------------------------
    def draw_segmentation(self, image, results):
        """Back-compat wrapper around :meth:`YoloDetector.draw_segmentation`."""
        output = self.yolo.draw_segmentation(image, results)
        self.current_segmentation_results = self.yolo.current_segmentation_results
        return output

    def image_callback(self, msg):
        if not self.camera_initialized:
            self.get_logger().debug("⏳ Camera not fully initialized yet, skipping this callback")
            return

        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            results = self.yolo.detect(cv_image, conf=0.6)
            current_detections = []

            current_pose = self.path_history[-1] if self.path_history else (None, None)
            x_pose, y_pose = current_pose

            min_object_distance = float('inf')
            has_close_object = False

            for result in results.boxes.data:
                x1, y1, x2, y2, conf, cls = result.cpu().numpy()
                x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                depth = self.get_depth_at_point(cx, cy)

                obj = {
                    "object": self.yolo.model.names[int(cls)],
                    "confidence": round(float(conf), 2),
                    "distance(m)": round(float(depth), 2),
                    "x": round(float(x_pose), 2) if x_pose is not None else None,
                    "y": round(float(y_pose), 2) if y_pose is not None else None
                }
                current_detections.append(obj)

                if depth > 0 and depth < 1.0:
                    has_close_object = True
                    min_object_distance = min(min_object_distance, depth)

            self.detections_for_ui = current_detections

            if self.navigation_active and has_close_object:
                current_time = time.time()
                if (current_time - self.tts.last_warning_time > self.tts.warning_cooldown and
                        not self.tts.warning_speech_active):
                    self.play_warning_speech()
                    self.tts.last_warning_time = current_time
                    self.get_logger().warn(f"⚠️ YOLO object distance warning! Nearest object distance: {min_object_distance:.2f}m")

                    if not self.is_avoiding_obstacle:
                        self.pause_normal_speech()
                        self.is_avoiding_obstacle = True
            else:
                if self.is_avoiding_obstacle:
                    self.resume_normal_speech()
                    self.is_avoiding_obstacle = False

            seg_results = self.yolo.segment(cv_image, conf=0.5)
            segmented_image = self.draw_segmentation(cv_image, seg_results)

            with self.segmentation_lock:
                self.latest_segmented_image = segmented_image

        except Exception as e:
            self.get_logger().error(f'Image processing error: {str(e)}')

    def depth_callback(self, msg):
        if not self.camera_initialized:
            self.get_logger().debug("⏳ Camera not fully initialized yet, skipping this depth callback")
            return

        try:
            self.latest_depth_image = self.bridge.imgmsg_to_cv2(msg, 'passthrough')
        except Exception as e:
            self.get_logger().error(f'Depth image error: {str(e)}')

    def get_depth_at_point(self, x, y, kernel_size=5):
        import numpy as np
        if self.latest_depth_image is None:
            return -1

        h, w = self.latest_depth_image.shape
        x, y = int(np.clip(x, 0, w - 1)), int(np.clip(y, 0, h - 1))
        hk = kernel_size // 2
        x0, x1 = max(0, x - hk), min(w, x + hk + 1)
        y0, y1 = max(0, y - hk), min(h, y + hk + 1)
        roi = self.latest_depth_image[y0:y1, x0:x1]
        valid = roi[(roi > 0) & (~np.isnan(roi))]
        return np.mean(valid) / 1000.0 if valid.size > 0 else -1

    def stop_camera_subscription(self):
        """Stop the camera's image and depth subscriptions"""
        if self.rgb_subscription is not None:
            self.destroy_subscription(self.rgb_subscription)
            self.rgb_subscription = None
            self.get_logger().info("🛑 RGB image subscription stopped")

        if self.depth_subscription is not None:
            self.destroy_subscription(self.depth_subscription)
            self.depth_subscription = None
            self.get_logger().info("🛑 Depth image subscription stopped")

        self.camera_initialized = False
