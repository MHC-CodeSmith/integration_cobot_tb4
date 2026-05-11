#!/usr/bin/env python3
import argparse
import json
import socket

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class JointStateUdpExporter(Node):
    def __init__(self, topic, host, port):
        super().__init__("mycobot_joint_udp_exporter")
        self._target = (host, port)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.create_subscription(JointState, topic, self._callback, 10)
        self.get_logger().info(f"Exportando {topic} -> udp://{host}:{port}")

    def _callback(self, msg):
        payload = {
            "name": list(msg.name),
            "position": [float(v) for v in msg.position],
            "velocity": [float(v) for v in msg.velocity],
            "effort": [float(v) for v in msg.effort],
            "frame_id": msg.header.frame_id,
        }
        self._sock.sendto(json.dumps(payload).encode("utf-8"), self._target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="/joint_states")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=30242)
    args = parser.parse_args()

    rclpy.init()
    node = JointStateUdpExporter(args.topic, args.host, args.port)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
