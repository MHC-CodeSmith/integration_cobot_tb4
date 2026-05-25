from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


ROOT_DIR = Path("/home/mhc/Germany/cobot_tb4_integration")
MYCOBOT_DESCRIPTION_DIR = Path(
    "/home/mhc/Germany/Cobot/mycobot_docker/custom_ws/src/mycobot_description"
)
DEFAULT_XACRO = (
    MYCOBOT_DESCRIPTION_DIR
    / "urdf"
    / "mycobot_280_jn"
    / "mycobot_280_jn.urdf.xacro"
)


def _robot_description_text(xacro_path: Path) -> str:
    text = xacro_path.read_text()
    # Host overlay is intentionally build-free. Use absolute mesh URIs so RViz
    # can load MyCobot visuals without installing mycobot_description on Jazzy.
    return text.replace("package://mycobot_description", MYCOBOT_DESCRIPTION_DIR.as_uri())


def _launch_nodes(context):
    x = LaunchConfiguration("x").perform(context)
    y = LaunchConfiguration("y").perform(context)
    z = LaunchConfiguration("z").perform(context)
    yaw = LaunchConfiguration("yaw").perform(context)
    xacro_path = Path(LaunchConfiguration("mycobot_xacro").perform(context))

    static_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="mycobot_anchor_publisher",
        arguments=[
            "--x", x,
            "--y", y,
            "--z", z,
            "--yaw", yaw,
            "--pitch", "0.0",
            "--roll", "0.0",
            "--frame-id", "map",
            "--child-frame-id", "mycobot_base_link",
        ],
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="mycobot_robot_state_publisher",
        namespace="mycobot",
        output="screen",
        parameters=[{
            "robot_description": _robot_description_text(xacro_path),
            "publish_frequency": 30.0,
        }],
        remappings=[
            ("joint_states", "/mycobot/joint_states"),
            ("tf", "/tf"),
            ("tf_static", "/tf_static"),
        ],
    )

    table_z = float(z) / 2.0
    marker_yaml = (
        "{markers: ["
        "{header: {frame_id: 'map'}, ns: 'mycobot_table', id: 1, type: 1, action: 0, "
        f"pose: {{position: {{x: {x}, y: {y}, z: {table_z}}}, orientation: {{w: 1.0}}}}, "
        "scale: {x: 0.90, y: 0.70, z: 0.80}, "
        "color: {r: 0.55, g: 0.58, b: 0.62, a: 0.55}}, "
        "{header: {frame_id: 'map'}, ns: 'mycobot_base_plate', id: 2, type: 3, action: 0, "
        f"pose: {{position: {{x: {x}, y: {y}, z: {float(z) + 0.02}}}, orientation: {{w: 1.0}}}}, "
        "scale: {x: 0.26, y: 0.26, z: 0.04}, "
        "color: {r: 0.1, g: 0.1, b: 0.12, a: 0.85}}"
        "]}"
    )

    table_markers = ExecuteProcess(
        cmd=[
            "ros2",
            "topic",
            "pub",
            "-r",
            "1",
            "/cobot_tb4_overlay/markers",
            "visualization_msgs/msg/MarkerArray",
            marker_yaml,
        ],
        output="screen",
    )

    return [static_tf, robot_state_publisher, table_markers]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("x", default_value="-0.338416188955307"),
        DeclareLaunchArgument("y", default_value="1.1060110330581665"),
        DeclareLaunchArgument("z", default_value="0.80"),
        DeclareLaunchArgument("yaw", default_value="0.0"),
        DeclareLaunchArgument("mycobot_xacro", default_value=str(DEFAULT_XACRO)),
        OpaqueFunction(function=_launch_nodes),
    ])
