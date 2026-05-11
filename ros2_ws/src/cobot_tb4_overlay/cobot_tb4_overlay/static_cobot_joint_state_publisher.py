#!/usr/bin/env python3
import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


JOINT_NAMES = [
    "joint2_to_joint1",
    "joint3_to_joint2",
    "joint4_to_joint3",
    "joint5_to_joint4",
    "joint6_to_joint5",
    "joint6output_to_joint6",
]


class StaticCobotJointStatePublisher(Node):
    def __init__(self):
        super().__init__("static_cobot_joint_state_publisher")

        self.declare_parameter("joint_topic", "/mycobot/joint_states")
        self.declare_parameter("rate_hz", 20.0)
        self.declare_parameter("joint_positions_deg", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

        topic = self.get_parameter("joint_topic").value
        rate_hz = float(self.get_parameter("rate_hz").value)
        positions_deg = list(self.get_parameter("joint_positions_deg").value)
        if len(positions_deg) != len(JOINT_NAMES):
            self.get_logger().warn("joint_positions_deg invalido; usando pose zero")
            positions_deg = [0.0] * len(JOINT_NAMES)

        self._positions_rad = [math.radians(float(v)) for v in positions_deg]
        self._pub = self.create_publisher(JointState, topic, 10)
        self._timer = self.create_timer(1.0 / rate_hz, self._publish)

        self.get_logger().info(f"Publicando pose estatica do MyCobot em {topic}")

    def _publish(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = JOINT_NAMES
        msg.position = self._positions_rad
        msg.velocity = [0.0] * len(JOINT_NAMES)
        msg.effort = [0.0] * len(JOINT_NAMES)
        self._pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = StaticCobotJointStatePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
