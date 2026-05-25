#!/usr/bin/env python3
import argparse
import math
import re
import xml.etree.ElementTree as ET

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from visualization_msgs.msg import Marker, MarkerArray


def quat_from_rpy(roll, pitch, yaw):
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    return (
        sr * cp * cy - cr * sp * sy,
        cr * sp * cy + sr * cp * sy,
        cr * cp * sy - sr * sp * cy,
        cr * cp * cy + sr * sp * sy,
    )


def floats(value, count=None):
    vals = [float(part) for part in value.split()]
    if count is not None and len(vals) != count:
        raise ValueError(f"Expected {count} floats, got {len(vals)} from {value!r}")
    return vals


def parse_origin(origin):
    if origin is None:
        return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    xyz = floats(origin.attrib.get("xyz", "0 0 0"), 3)
    rpy = floats(origin.attrib.get("rpy", "0 0 0"), 3)
    return xyz, rpy


def marker_array_from_urdf(path, marker_ns):
    root = ET.parse(path).getroot()
    materials = {}
    for mat in root.findall("material"):
        color = mat.find("color")
        if color is not None and "rgba" in color.attrib:
            materials[mat.attrib["name"]] = floats(color.attrib["rgba"], 4)

    joints_by_child = {}
    for joint in root.findall("joint"):
        child = joint.find("child")
        origin = joint.find("origin")
        if child is not None:
            joints_by_child[child.attrib["link"]] = parse_origin(origin)

    markers = []
    clear = Marker()
    clear.header.frame_id = "map"
    clear.ns = marker_ns
    clear.id = 0
    clear.action = Marker.DELETEALL
    markers.append(clear)

    marker_id = 1
    for link in root.findall("link"):
        link_name = link.attrib.get("name", "")
        if link_name == "map":
            continue
        xyz, rpy = joints_by_child.get(link_name, ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))
        qx, qy, qz, qw = quat_from_rpy(*rpy)

        for visual in link.findall("visual"):
            geometry = visual.find("geometry")
            if geometry is None:
                continue
            box = geometry.find("box")
            cylinder = geometry.find("cylinder")
            if box is None and cylinder is None:
                continue

            color = [0.55, 0.55, 0.55, 1.0]
            mat = visual.find("material")
            if mat is not None:
                inline = mat.find("color")
                if inline is not None and "rgba" in inline.attrib:
                    color = floats(inline.attrib["rgba"], 4)
                elif "name" in mat.attrib and mat.attrib["name"] in materials:
                    color = materials[mat.attrib["name"]]

            marker = Marker()
            marker.header.frame_id = "map"
            marker.ns = marker_ns
            marker.id = marker_id
            marker_id += 1
            marker.action = Marker.ADD
            marker.pose.position.x = xyz[0]
            marker.pose.position.y = xyz[1]
            marker.pose.position.z = xyz[2]
            marker.pose.orientation.x = qx
            marker.pose.orientation.y = qy
            marker.pose.orientation.z = qz
            marker.pose.orientation.w = qw
            marker.color.r = color[0]
            marker.color.g = color[1]
            marker.color.b = color[2]
            marker.color.a = color[3]

            if box is not None:
                sx, sy, sz = floats(box.attrib["size"], 3)
                marker.type = Marker.CUBE
                marker.scale.x = sx
                marker.scale.y = sy
                marker.scale.z = sz
            else:
                radius = float(cylinder.attrib["radius"])
                length = float(cylinder.attrib["length"])
                marker.type = Marker.CYLINDER
                marker.scale.x = radius * 2.0
                marker.scale.y = radius * 2.0
                marker.scale.z = length

            markers.append(marker)

    return MarkerArray(markers=markers)


class UrdfMarkerPublisher(Node):
    def __init__(self, topic, urdf_path, marker_ns, period):
        node_name = "urdf_marker_publisher_" + re.sub(r"[^a-zA-Z0-9_]+", "_", topic).strip("_")
        super().__init__(node_name[:255])
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self._markers = marker_array_from_urdf(urdf_path, marker_ns)
        self._pub = self.create_publisher(MarkerArray, topic, qos)
        self._timer = self.create_timer(period, self._publish)
        self._publish()
        self.get_logger().info(f"Publishing {len(self._markers.markers) - 1} markers on {topic}")

    def _publish(self):
        now = self.get_clock().now().to_msg()
        for marker in self._markers.markers:
            marker.header.stamp = now
        self._pub.publish(self._markers)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--period", type=float, default=5.0)
    args = parser.parse_args()

    rclpy.init()
    node = UrdfMarkerPublisher(args.topic, args.file, args.namespace, args.period)
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
