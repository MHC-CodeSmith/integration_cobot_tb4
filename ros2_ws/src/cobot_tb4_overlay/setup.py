from setuptools import setup

package_name = "cobot_tb4_overlay"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/integrated_scene.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="mhc",
    maintainer_email="mhc@todo.todo",
    description="Visualization overlay for anchoring MyCobot in the TurtleBot4 map.",
    license="TODO",
    entry_points={
        "console_scripts": [
            "static_cobot_joint_state_publisher = cobot_tb4_overlay.static_cobot_joint_state_publisher:main",
            "table_marker_node = cobot_tb4_overlay.table_marker_node:main",
            "udp_joint_state_importer = cobot_tb4_overlay.udp_joint_state_importer:main",
        ],
    },
)
