import os
import yaml
import tempfile

from launch import LaunchDescription
from launch.actions import (
    GroupAction,
    IncludeLaunchDescription,
    DeclareLaunchArgument,
    ExecuteProcess,
)
from launch.conditions import IfCondition
from launch.substitutions import (
    LaunchConfiguration,
    Command,
    PythonExpression
)
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.parameter_descriptions import ParameterValue
from launch.launch_description_sources import PythonLaunchDescriptionSource

from ament_index_python.packages import get_package_share_directory
from ros_gz_sim.actions import GzServer
from ros_gz_bridge.actions import RosGzBridge


# ---------------------------------------------------------
# Dynamic bridge generator
# ---------------------------------------------------------
def generate_bridge_yaml(robots):

    bridge_entries = []

    # Global clock (only once)
    bridge_entries.append({
        "ros_topic_name": "/clock",
        "gz_topic_name": "/clock",
        "ros_type_name": "rosgraph_msgs/msg/Clock",
        "gz_type_name": "gz.msgs.Clock",
        "direction": "GZ_TO_ROS"
    })

    for robot in robots:
        name = robot["name"]

        bridge_entries.append({
            "ros_topic_name": f"/{name}/scan",
            "gz_topic_name": f"/model/{name}/link/lidar_link/sensor/lidar/scan",
            "ros_type_name": "sensor_msgs/msg/LaserScan",
            "gz_type_name": "gz.msgs.LaserScan",
            "direction": "GZ_TO_ROS"
        })

        bridge_entries.append({
            "ros_topic_name": f"/{name}/imu",
            "gz_topic_name": f"/model/{name}/link/imu_link/sensor/imu/imu",
            "ros_type_name": "sensor_msgs/msg/Imu",
            "gz_type_name": "gz.msgs.IMU",
            "direction": "GZ_TO_ROS"
        })

    tmp = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml')
    yaml.dump(bridge_entries, tmp)
    tmp.close()

    return tmp.name


# ---------------------------------------------------------
# Main launch
# ---------------------------------------------------------
def generate_launch_description():

    pkg_share = get_package_share_directory('multiple_robots')
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')
    nav2_share = get_package_share_directory('nav2_bringup')

    world_path = os.path.join(pkg_share, 'world', 'simple_world.sdf')
    shared_rviz_config = os.path.join(pkg_share, 'rviz', 'config_nav2.rviz')

    robots = [
        {
            "name": "robot1",
            "x": "0.0",
            "y": "0.0",
            "urdf": os.path.join(pkg_share, "description", "robot1.urdf"),
            "controller": os.path.join(pkg_share, "config", "robot1_controllers.yaml"),
            "nav2": os.path.join(pkg_share, "config", "robot1_nav2.yaml"),
            "ekf": os.path.join(pkg_share, "config", "robot1_ekf.yaml"),
        },
        {
            "name": "robot2",
            "x": "3.0",
            "y": "1.0",
            "urdf": os.path.join(pkg_share, "description", "robot2.xacro"),
            "controller": os.path.join(pkg_share, "config", "robot2_controllers.yaml"),
            "nav2": os.path.join(pkg_share, "config", "robot2_nav2.yaml"),
            "ekf": os.path.join(pkg_share, "config", "robot2_ekf.yaml"),
        },
    ]

    bridge_config = generate_bridge_yaml(robots)

    ld = LaunchDescription()

    # -----------------------------------------------------
    # Launch argument: rviz_mode
    # -----------------------------------------------------
    ld.add_action(
        DeclareLaunchArgument(
            "rviz_mode",
            default_value="shared",
            description="RViz mode: 'shared' or 'per_robot'"
        )
    )

    rviz_mode = LaunchConfiguration("rviz_mode")

    # -----------------------------------------------------
    # Gazebo
    # -----------------------------------------------------
    gz_server = GzServer(
        world_sdf_file=world_path,
        container_name='ros_gz_container',
        create_own_container=True,
        use_composition=True,
    )
    ld.add_action(gz_server)
    ld.add_action(ExecuteProcess(cmd=['gz', 'sim', '-g'], output='screen'),)

    # -----------------------------------------------------
    # Bridge (clock + sensors)
    # -----------------------------------------------------
    ros_gz_bridge = RosGzBridge(
        bridge_name='ros_gz_bridge',
        config_file=bridge_config,
        container_name='ros_gz_container',
        create_own_container=False,
        use_composition=True,
    )
    ld.add_action(ros_gz_bridge)

    # -----------------------------------------------------
    # Robots
    # -----------------------------------------------------
    for robot in robots:

        name = robot["name"]

        robot_group = GroupAction([

            PushRosNamespace(name),

            Node(
                package='robot_state_publisher',
                executable='robot_state_publisher',
                parameters=[
                    {
                        'robot_description':
                            ParameterValue(
                                Command(['xacro ', robot["urdf"]]),
                                value_type=str
                            )
                    },
                    {'use_sim_time': True}
                ],
            ),

            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(
                        ros_gz_sim_share,
                        'launch',
                        'gz_spawn_model.launch.py'
                    )
                ),
                launch_arguments={
                    'world': 'simple_world',
                    'topic': f'/{name}/robot_description',
                    'entity_name': name,
                    'x': robot["x"],
                    'y': robot["y"],
                    'z': '0.0',
                }.items(),
            ),

            Node(
                package='controller_manager',
                executable='ros2_control_node',
                parameters=[
                    {
                        'robot_description':
                            ParameterValue(
                                Command(['xacro ', robot["urdf"]]),
                                value_type=str
                            )
                    },
                    robot["controller"]
                ],
            ),

            Node(
                package="controller_manager",
                executable="spawner",
                arguments=[
                    "joint_state_broadcaster",
                    "--controller-manager",
                    f"/{name}/controller_manager"
                ],
            ),

            Node(
                package="controller_manager",
                executable="spawner",
                arguments=[
                    "drive_controller",
                    "--controller-manager",
                    f"/{name}/controller_manager"
                ],
            ),

            Node(
                package='robot_localization',
                executable='ekf_node',
                name='ekf_filter_node',
                parameters=[robot["ekf"],
                            {'use_sim_time': True}],
            ),

            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(nav2_share, 'launch', 'bringup_launch.py')
                ),
                launch_arguments={
                    'namespace': name,
                    'use_namespace': 'True',
                    'use_sim_time': 'True',
                    'autostart': 'True',
                    'params_file': robot["nav2"],
                }.items(),
            ),

            # -------------------------------------------------
            # RViz per robot (conditional)
            # -------------------------------------------------
            Node(
                package='rviz2',
                executable='rviz2',
                arguments=['-d', shared_rviz_config],
                parameters=[{'use_sim_time': True}],
                condition=IfCondition(
                    PythonExpression(
                        [rviz_mode, " == 'per_robot'"]
                    )
                )
            ),
        ])

        ld.add_action(robot_group)

    # -----------------------------------------------------
    # Shared RViz (conditional)
    # -----------------------------------------------------
    ld.add_action(
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', shared_rviz_config],
            parameters=[{'use_sim_time': True}],
            condition=IfCondition(
                PythonExpression(
                    [rviz_mode, " == 'shared'"]
                )
            )
        )
    )

    return ld
