from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    x = LaunchConfiguration("x")
    y = LaunchConfiguration("y")
    z = LaunchConfiguration("z")
    yaw = LaunchConfiguration("yaw")
    joint_source = LaunchConfiguration("joint_source")
    mycobot_xacro = LaunchConfiguration("mycobot_xacro")

    robot_description = {
        "robot_description": ParameterValue(
            Command([FindExecutable(name="xacro"), " ", mycobot_xacro]),
            value_type=str,
        ),
        "publish_frequency": 30.0,
    }

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
        parameters=[robot_description],
        remappings=[
            ("joint_states", "/mycobot/joint_states"),
            ("/tf", "/tf"),
            ("/tf_static", "/tf_static"),
        ],
    )

    static_joints = Node(
        package="cobot_tb4_overlay",
        executable="static_cobot_joint_state_publisher",
        name="static_cobot_joint_state_publisher",
        output="screen",
        condition=IfCondition(PythonExpression(["'", joint_source, "' == 'static'"])),
    )

    udp_importer = Node(
        package="cobot_tb4_overlay",
        executable="udp_joint_state_importer",
        name="udp_joint_state_importer",
        output="screen",
        condition=IfCondition(PythonExpression(["'", joint_source, "' == 'udp'"])),
    )

    table_markers = Node(
        package="cobot_tb4_overlay",
        executable="table_marker_node",
        name="table_marker_node",
        output="screen",
        parameters=[{
            "x": x,
            "y": y,
            "z": z,
            "yaw": yaw,
            "table_height": z,
        }],
    )

    return LaunchDescription([
        DeclareLaunchArgument("x", default_value="-2.9394"),
        DeclareLaunchArgument("y", default_value="4.1843"),
        DeclareLaunchArgument("z", default_value="0.80"),
        DeclareLaunchArgument("yaw", default_value="0.0"),
        DeclareLaunchArgument(
            "joint_source",
            default_value="static",
            description="Use 'static' for neutral MyCobot pose or 'udp' for live mirrored joints.",
        ),
        DeclareLaunchArgument(
            "mycobot_xacro",
            default_value=PathJoinSubstitution([
                FindPackageShare("mycobot_description"),
                "urdf",
                "mycobot_280_jn",
                "mycobot_280_jn.urdf.xacro",
            ]),
        ),
        static_tf,
        robot_state_publisher,
        static_joints,
        udp_importer,
        table_markers,
    ])
