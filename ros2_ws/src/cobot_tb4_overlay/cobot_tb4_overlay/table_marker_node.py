#!/usr/bin/env python3
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from visualization_msgs.msg import Marker, MarkerArray


def yaw_to_quaternion(yaw):
    qz = math.sin(yaw / 2.0)
    qw = math.cos(yaw / 2.0)
    return 0.0, 0.0, qz, qw


class TableMarkerNode(Node):
    def __init__(self):
        super().__init__("table_marker_node")

        self.declare_parameter("frame_id", "map")
        self.declare_parameter("x", -2.9394)
        self.declare_parameter("y", 4.1843)
        self.declare_parameter("z", 0.80)
        self.declare_parameter("yaw", 0.0)
        self.declare_parameter("table_length", 0.90)
        self.declare_parameter("table_width", 0.70)
        self.declare_parameter("table_height", 0.80)
        self.declare_parameter("publish_rate_hz", 1.0)

        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self._pub = self.create_publisher(MarkerArray, "/cobot_tb4_overlay/markers", qos)

        rate_hz = float(self.get_parameter("publish_rate_hz").value)
        self._timer = self.create_timer(1.0 / rate_hz, self._publish)
        self.get_logger().info("Publicando mesa/ancora do MyCobot em /cobot_tb4_overlay/markers")

    def _base_marker(self, marker_id, marker_type, ns):
        marker = Marker()
        marker.header.frame_id = self.get_parameter("frame_id").value
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = ns
        marker.id = marker_id
        marker.type = marker_type
        marker.action = Marker.ADD
        marker.lifetime.sec = 0
        return marker

    def _publish(self):
        x = float(self.get_parameter("x").value)
        y = float(self.get_parameter("y").value)
        z = float(self.get_parameter("z").value)
        yaw = float(self.get_parameter("yaw").value)
        length = float(self.get_parameter("table_length").value)
        width = float(self.get_parameter("table_width").value)
        height = float(self.get_parameter("table_height").value)
        qx, qy, qz, qw = yaw_to_quaternion(yaw)

        table = self._base_marker(1, Marker.CUBE, "mycobot_table")
        table.pose.position.x = x
        table.pose.position.y = y
        table.pose.position.z = height / 2.0
        table.pose.orientation.x = qx
        table.pose.orientation.y = qy
        table.pose.orientation.z = qz
        table.pose.orientation.w = qw
        table.scale.x = length
        table.scale.y = width
        table.scale.z = height
        table.color.r = 0.55
        table.color.g = 0.58
        table.color.b = 0.62
        table.color.a = 0.55

        base = self._base_marker(2, Marker.CYLINDER, "mycobot_base_plate")
        base.pose.position.x = x
        base.pose.position.y = y
        base.pose.position.z = z + 0.02
        base.pose.orientation.w = 1.0
        base.scale.x = 0.26
        base.scale.y = 0.26
        base.scale.z = 0.04
        base.color.r = 0.1
        base.color.g = 0.1
        base.color.b = 0.12
        base.color.a = 0.85

        label = self._base_marker(3, Marker.TEXT_VIEW_FACING, "mycobot_anchor_label")
        label.pose.position.x = x
        label.pose.position.y = y
        label.pose.position.z = z + 0.45
        label.pose.orientation.w = 1.0
        label.scale.z = 0.12
        label.color.r = 0.05
        label.color.g = 0.05
        label.color.b = 0.05
        label.color.a = 1.0
        label.text = "MyCobot anchor"

        self._pub.publish(MarkerArray(markers=[table, base, label]))


def main(args=None):
    rclpy.init(args=args)
    node = TableMarkerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
