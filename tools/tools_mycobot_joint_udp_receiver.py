#!/usr/bin/env python3
import argparse
import json
import socket
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


DEFAULT_JOINTS = [
    "joint2_to_joint1",
    "joint3_to_joint2",
    "joint4_to_joint3",
    "joint5_to_joint4",
    "joint6_to_joint5",
    "joint6output_to_joint6",
]


class JointStateUdpReceiver(Node):
    def __init__(self, bind_host, port, topic):
        super().__init__("mycobot_joint_udp_receiver")
        self._publisher = self.create_publisher(JointState, topic, 10)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((bind_host, port))
        self._sock.setblocking(False)
        self._received_count = 0
        self._last_packet_monotonic = 0.0
        self._last_warn_monotonic = 0.0
        self.create_timer(0.01, self._poll_socket)
        self.create_timer(2.0, self._warn_if_stale)
        self.get_logger().info(f"Recebendo juntas MyCobot em udp://{bind_host}:{port} -> {topic}")

    def _poll_socket(self):
        while True:
            try:
                data, _addr = self._sock.recvfrom(65535)
            except BlockingIOError:
                break

            try:
                payload = json.loads(data.decode("utf-8"))
                msg = self._message_from_payload(payload)
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
                self.get_logger().warn(f"Pacote de juntas ignorado: {exc}")
                continue

            self._publisher.publish(msg)
            self._received_count += 1
            self._last_packet_monotonic = time.monotonic()

            if self._received_count == 1:
                positions = ", ".join(f"{value:.3f}" for value in msg.position)
                self.get_logger().info(f"Primeiro JointState real recebido: [{positions}]")

    def _message_from_payload(self, payload):
        positions = [float(value) for value in payload.get("position", [])]
        if len(positions) != 6:
            raise ValueError(f"esperava 6 posicoes, recebi {len(positions)}")

        names = list(payload.get("name") or DEFAULT_JOINTS)
        if len(names) != 6:
            raise ValueError(f"esperava 6 nomes de juntas, recebi {len(names)}")

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = str(payload.get("frame_id", ""))
        msg.name = names
        msg.position = positions
        msg.velocity = [float(value) for value in payload.get("velocity", [])]
        msg.effort = [float(value) for value in payload.get("effort", [])]
        return msg

    def _warn_if_stale(self):
        now = time.monotonic()
        if self._received_count == 0:
            if now - self._last_warn_monotonic > 10.0:
                self.get_logger().warn("Ainda nao recebi juntas reais do MyCobot.")
                self._last_warn_monotonic = now
            return

        if now - self._last_packet_monotonic > 5.0 and now - self._last_warn_monotonic > 5.0:
            self.get_logger().warn("JointState do MyCobot parou de chegar ha mais de 5 s.")
            self._last_warn_monotonic = now


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=30242)
    parser.add_argument("--topic", default="/mycobot/joint_states")
    args = parser.parse_args()

    rclpy.init()
    node = JointStateUdpReceiver(args.bind, args.port, args.topic)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
