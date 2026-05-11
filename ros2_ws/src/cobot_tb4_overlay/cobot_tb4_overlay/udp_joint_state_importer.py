#!/usr/bin/env python3
import json
import socket
import threading

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class UdpJointStateImporter(Node):
    def __init__(self):
        super().__init__("udp_joint_state_importer")

        self.declare_parameter("bind_host", "127.0.0.1")
        self.declare_parameter("bind_port", 30242)
        self.declare_parameter("joint_topic", "/mycobot/joint_states")

        host = self.get_parameter("bind_host").value
        port = int(self.get_parameter("bind_port").value)
        topic = self.get_parameter("joint_topic").value

        self._pub = self.create_publisher(JointState, topic, 10)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((host, port))
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

        self.get_logger().info(f"Recebendo joint states UDP em {host}:{port} -> {topic}")

    def _recv_loop(self):
        while not self._stop.is_set():
            try:
                data, _addr = self._sock.recvfrom(8192)
                payload = json.loads(data.decode("utf-8"))
                names = payload.get("name", [])
                positions = payload.get("position", [])
                if len(names) != len(positions) or not names:
                    continue

                msg = JointState()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.name = [str(name) for name in names]
                msg.position = [float(value) for value in positions]
                msg.velocity = [0.0] * len(msg.name)
                msg.effort = [0.0] * len(msg.name)
                self._pub.publish(msg)
            except OSError:
                return
            except Exception as exc:
                self.get_logger().warn(f"Pacote UDP ignorado: {exc}", throttle_duration_sec=2.0)

    def destroy_node(self):
        self._stop.set()
        try:
            self._sock.close()
        except OSError:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = UdpJointStateImporter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
