from pathlib import Path

from launch import LaunchDescription
from launch.actions import OpaqueFunction
from launch_ros.actions import Node


OBSTACLES_URDF = Path("/home/mhc/Germany/cobot_tb4_integration/generated/map_obstacles_3d.urdf")


def _nodes(_context):
    return [
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="map_obstacles_3d_state_publisher",
            namespace="env3d",
            output="screen",
            parameters=[{
                "robot_description": OBSTACLES_URDF.read_text(),
                "publish_frequency": 1.0,
            }],
        )
    ]


def generate_launch_description():
    return LaunchDescription([OpaqueFunction(function=_nodes)])
