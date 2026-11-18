"""ROS2 launch file for ArduPilot SITL simulation with the full NLP-to-flight pipeline."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    num_drones = LaunchConfiguration("num_drones", default="3")
    home_lat = LaunchConfiguration("home_lat", default="47.397742")
    home_lon = LaunchConfiguration("home_lon", default="8.545594")

    # ArduPilot SITL instances
    sitl_processes = []
    for i in range(3):
        lat_offset = i * 0.0001
        sitl_processes.append(
            ExecuteProcess(
                cmd=[
                    "sim_vehicle.py",
                    "-v", "ArduCopter",
                    "--instance", str(i),
                    "-l", f"47.397742,{8.545594 + lat_offset},488,0",
                    "--out", f"udp:127.0.0.1:{14550 + i * 10}",
                    "--no-rebuild",
                ],
                name=f"ardupilot_sitl_{i}",
                output="screen",
            )
        )

    # ros_gz_bridge for sensor data (cameras, lidar)
    gz_bridge = ExecuteProcess(
        cmd=[
            "ros2", "run", "ros_gz_bridge", "parameter_bridge",
            "/camera@sensor_msgs/msg/Image@gz.msgs.Image",
            "/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo",
        ],
        name="ros_gz_bridge",
        output="screen",
    )

    # Application nodes (delayed to let SITL boot)
    stt_node = Node(
        package="drone_vla",
        executable="stt_node",
        name="stt_node",
        output="screen",
    )

    intent_node = Node(
        package="drone_vla",
        executable="intent_parser_node",
        name="intent_parser_node",
        output="screen",
    )

    orchestrator_node = Node(
        package="drone_vla",
        executable="orchestrator_node",
        name="orchestrator_node",
        output="screen",
    )

    delayed_nodes = TimerAction(
        period=15.0,
        actions=[stt_node, intent_node, orchestrator_node],
    )

    return LaunchDescription([
        DeclareLaunchArgument("num_drones", default_value="3"),
        DeclareLaunchArgument("home_lat", default_value="47.397742"),
        DeclareLaunchArgument("home_lon", default_value="8.545594"),
        *sitl_processes,
        gz_bridge,
        delayed_nodes,
    ])
