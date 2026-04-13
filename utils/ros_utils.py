import math
import time
import threading

import rclpy
import streamlit as st
from geometry_msgs.msg import PoseWithCovarianceStamped

from amr_ui.utils.file_utils import euler2quat
from amr_ui.models.smart_nav_node import SmartNavNode


def publish_initial_pose(node, x=0.0, y=0.0, yaw_deg=0.0):
    """Publish an initial pose to /initialpose."""
    pub = node.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
    q = euler2quat(0, 0, math.radians(yaw_deg))
    pose_msg = PoseWithCovarianceStamped()
    pose_msg.header.frame_id = 'map'
    pose_msg.pose.pose.position.x = x
    pose_msg.pose.pose.position.y = y
    pose_msg.pose.pose.orientation.x = q[1]
    pose_msg.pose.pose.orientation.y = q[2]
    pose_msg.pose.pose.orientation.z = q[3]
    pose_msg.pose.pose.orientation.w = q[0]
    pose_msg.pose.covariance[0] = 0.25
    pose_msg.pose.covariance[7] = 0.25
    pose_msg.pose.covariance[35] = math.radians(10) ** 2
    time.sleep(1.0)
    pub.publish(pose_msg)
    node.get_logger().info(f"📍 Initial pose set to ({x}, {y}, {yaw_deg}°)")
    return {'x': q[1], 'y': q[2], 'z': q[3], 'w': q[0]}


def initialize_ros_node():
    if "ros_node" not in st.session_state or st.session_state["ros_node"] is None:
        try:
            if not rclpy.ok():
                rclpy.init()

            node = SmartNavNode()
            st.session_state["ros_node"] = node

            def spin_node():
                try:
                    rclpy.spin(node)
                except Exception as e:
                    print(f"ROS node error: {str(e)}")

            ros_thread = threading.Thread(target=spin_node, daemon=True)
            ros_thread.start()
            st.session_state["ros_thread"] = ros_thread

            return True
        except Exception as e:
            st.error(f"ROS node initialization failed: {str(e)}")
            return False
    return True
