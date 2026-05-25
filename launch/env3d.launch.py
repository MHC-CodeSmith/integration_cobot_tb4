import os
from pathlib import Path

from launch import LaunchDescription
from launch.actions import ExecuteProcess, OpaqueFunction, SetEnvironmentVariable, UnsetEnvironmentVariable


ROOT_DIR = Path(__file__).resolve().parents[1]
FLOOR_URDF = ROOT_DIR / "generated" / "map_floor_3d.urdf"
OBSTACLES_URDF = ROOT_DIR / "generated" / "map_obstacles_3d.urdf"
FURNITURE_URDF = ROOT_DIR / "generated" / "room_furniture_3d.urdf"
MARKER_PUBLISHER = ROOT_DIR / "tools_urdf_marker_publisher.py"


def _marker_publisher(topic, marker_namespace, urdf_path):
    return ExecuteProcess(
        cmd=[
            "python3",
            str(MARKER_PUBLISHER),
            "--topic",
            topic,
            "--namespace",
            marker_namespace,
            "--file",
            str(urdf_path),
        ],
        output="screen",
    )


def _nodes(_context):
    return [
        _marker_publisher("/env3d/floor_markers", "floor", FLOOR_URDF),
        _marker_publisher("/env3d/wall_markers", "walls", OBSTACLES_URDF),
        _marker_publisher("/env3d/furniture_markers", "furniture", FURNITURE_URDF),
    ]


def generate_launch_description():
    actions = [
        SetEnvironmentVariable("ROS_DOMAIN_ID", "0"),
        SetEnvironmentVariable("ROS_AUTOMATIC_DISCOVERY_RANGE", "SUBNET"),
        SetEnvironmentVariable("RMW_IMPLEMENTATION", "rmw_fastrtps_cpp"),
        OpaqueFunction(function=_nodes),
    ]

    discovery_mode = os.environ.get("COBOT_TB4_DISCOVERY_MODE", "auto").lower()
    discovery_server = os.environ.get("ROS_DISCOVERY_SERVER")
    if discovery_mode == "local" or not discovery_server:
        actions.insert(0, UnsetEnvironmentVariable("ROS_DISCOVERY_SERVER"))
        actions.insert(1, SetEnvironmentVariable("ROS_SUPER_CLIENT", "False"))
    else:
        actions.insert(0, SetEnvironmentVariable("ROS_DISCOVERY_SERVER", discovery_server))
        actions.insert(1, SetEnvironmentVariable("ROS_SUPER_CLIENT", os.environ.get("ROS_SUPER_CLIENT", "True")))

    return LaunchDescription(actions)
