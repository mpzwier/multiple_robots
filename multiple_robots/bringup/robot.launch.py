import os
import tempfile

from launch import LaunchDescription
from launch.actions import GroupAction, IncludeLaunchDescription
from launch_ros.actions import Node, PushRosNamespace
from launch.launch_description_sources import PythonLaunchDescriptionSource

from nav2_common.launch import RewrittenYaml
from ament_index_python.packages import get_package_share_directory


def generate_rviz_config(robot_name, base_config_path):
    # Read the base RViz config
    with open(base_config_path, 'r') as f:
        config = f.read()

    # Replace placeholders
    config = config.replace('<ROBOT_NAME>', robot_name)

    # Use system temp directory
    temp_dir = tempfile.gettempdir()
    output_config_path = os.path.join(temp_dir, f'{robot_name}_rviz_config.rviz')

    with open(output_config_path, 'w') as f:
        f.write(config)

    return output_config_path

def generate_launch_description():

    pkg_share = get_package_share_directory('multiple_robots')
    gazebo_pkg = get_package_share_directory('gazebo_ros')
    nav2_pkg = get_package_share_directory('nav2_bringup')

    robots = [
        {
            'name': 'robot1',
            'x': '0.0',
            'y': '0.0',
        },
        {
            'name': 'robot2',
            'x': '3.0',
            'y': '0.0',
        }
    ]

    ld = LaunchDescription()

    # Start Gazebo
    ld.add_action(
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(gazebo_pkg, 'launch', 'gazebo.launch.py')
            )
        )
    )

    for robot in robots:

        name = robot['name']

        urdf_file = os.path.join(pkg_share, 'urdf', f'{name}.urdf')
        nav2_params = os.path.join(pkg_share, 'config', f'{name}_nav2.yaml')
        ekf_params = os.path.join(pkg_share, 'config', f'{name}_ekf.yaml')
        default_rviz_config_path = os.path.join(pkg_share, 'rviz', 'config_nav2.rviz')
        rviz_config = generate_rviz_config(f'{name}', default_rviz_config_path)

        configured_nav2_params = RewrittenYaml(
            source_file=nav2_params,
            root_key=name,
            param_rewrites={},
            convert_types=True
        )

        robot_group = GroupAction([

            PushRosNamespace(name),

            # Spawn robot in Gazebo
            Node(
                package='gazebo_ros',
                executable='spawn_entity.py',
                arguments=[
                    '-entity', name,
                    '-file', urdf_file,
                    '-x', robot['x'],
                    '-y', robot['y']
                ],
                output='screen'
            ),

            # Robot State Publisher
            Node(
                package='robot_state_publisher',
                executable='robot_state_publisher',
                parameters=[{
                    'robot_description': open(urdf_file).read(),
                    'use_sim_time': True
                }],
                output='screen'
            ),

            # -----------------------------
            # ros2_control Controller Manager
            # -----------------------------
            Node(
                package='controller_manager',
                executable='ros2_control_node',
                parameters=[urdf_file],
                output='screen'
            ),

            # Spawner: Joint State Broadcaster
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=[
                    'joint_state_broadcaster',
                    '--controller-manager',
                    f'/{name}/controller_manager'
                ],
                output='screen'
            ),

            # Spawner: Diff Drive Controller (example)
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=[
                    'diff_drive_controller',
                    '--controller-manager',
                    f'/{name}/controller_manager'
                ],
                output='screen'
            ),

            # -----------------------------
            # Robot Localization (EKF)
            # -----------------------------
            Node(
                package='robot_localization',
                executable='ekf_node',
                name='ekf_filter_node',
                parameters=[ekf_params, {'use_sim_time': True}],
                output='screen'
            ),

            # -----------------------------
            # LiDAR Bridge
            # -----------------------------
            Node(
                package='ros_gz_bridge',
                executable='parameter_bridge',
                arguments=[
                    f'/world/default/model/{name}/link/lidar_link/sensor/lidar/scan'
                    '@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan'
                ],
                remappings=[
                    (f'/world/default/model/{name}/link/lidar_link/sensor/lidar/scan', 'scan')
                ],
                output='screen'
            ),

            # -----------------------------
            # IMU Bridge
            # -----------------------------
            Node(
                package='ros_gz_bridge',
                executable='parameter_bridge',
                arguments=[
                    f'/world/default/model/{name}/link/imu_link/sensor/imu/imu'
                    '@sensor_msgs/msg/Imu[gz.msgs.IMU'
                ],
                remappings=[
                    (f'/world/default/model/{name}/link/imu_link/sensor/imu/imu', 'imu')
                ],
                output='screen'
            ),

            # -----------------------------
            # Nav2 Bringup
            # -----------------------------
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(nav2_pkg, 'launch', 'bringup_launch.py')
                ),
                launch_arguments={
                    'namespace': name,
                    'use_sim_time': 'True',
                    'params_file': configured_nav2_params
                }.items()
            ),

            # -----------------------------
            # RViz
            # -----------------------------
            Node(
                package='rviz2',
                executable='rviz2',
                arguments=['-d', rviz_config],
                parameters=[{'use_sim_time': True}],
                output='screen'
            ),
        ])

        ld.add_action(robot_group)

    return ld
