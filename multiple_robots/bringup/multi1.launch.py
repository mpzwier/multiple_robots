import os
import yaml
import tempfile

from launch import LaunchDescription
from launch.actions import GroupAction, IncludeLaunchDescription, DeclareLaunchArgument, OpaqueFunction, ExecuteProcess
from launch.conditions import IfCondition, LaunchConfigurationEquals
from launch.substitutions import LaunchConfiguration, Command, PythonExpression, EqualsSubstitution, PathJoinSubstitution, FindExecutable
from launch_ros.actions import Node, PushRosNamespace, ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
from launch_ros.parameter_descriptions import ParameterValue
from launch.launch_description_sources import PythonLaunchDescriptionSource

from ament_index_python.packages import get_package_share_directory
from ros_gz_sim.actions import GzServer
from ros_gz_bridge.actions import RosGzBridge

# ---------------------------------------------------------
# Launch description
# ---------------------------------------------------------
def generate_launch_description():

    #Package paths
    pkg_share = get_package_share_directory('multiple_robots')
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')
    nav2_share = get_package_share_directory('nav2_bringup')

    #File paths
    nav2_map_path = os.path.join(pkg_share, 'config', 'map.yaml')
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
            "bridge": os.path.join(pkg_share, "config", "robot1_bridge.yaml"),
        },
        {
            "name": "robot2",
            "x": "-2.0",
            "y": "0.0",
            "urdf": os.path.join(pkg_share, "description", "robot2.urdf"),
            "controller": os.path.join(pkg_share, "config", "robot2_controllers.yaml"),
            "nav2": os.path.join(pkg_share, "config", "robot2_nav2.yaml"),
            "ekf": os.path.join(pkg_share, "config", "robot2_ekf.yaml"),
            "bridge": os.path.join(pkg_share, "config", "robot2_bridge.yaml"),
        },
    ]

    ld = LaunchDescription()

    # -----------------------------------------------------
    # Launch argument: rviz_mode
    # -----------------------------------------------------
    ld.add_action(DeclareLaunchArgument(
        "rviz_mode",
        default_value="per_robot",
        description="RViz mode: 'shared' or 'per_robot'"
    ))

    # -----------------------------------------------------
    # Gazebo
    # -----------------------------------------------------
   
    ld.add_action(IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')
    ),
    launch_arguments={
        'gz_args': f"-r {world_path}"
    }.items(),      
    ))

    # -----------------------------------------------------
    # Multi-robot launch
    # -----------------------------------------------------
    for robot in robots:

        name = robot["name"]
        robot_group = GroupAction([

            PushRosNamespace(name),
           
            Node(
                package='ros_gz_bridge',
                executable='parameter_bridge',
                parameters=[{
                    'config_file': robot["bridge"],
                    'expand_gz_topic_names': True,
                    'use_sim_time': True,
                }]
            ),

            Node(
                package='robot_state_publisher',
                executable='robot_state_publisher',
                output='screen',
                parameters=[
                    {'robot_description': ParameterValue(Command([PathJoinSubstitution([FindExecutable(name='xacro')]),' ',robot["urdf"],' ',f'namespace:={name}']),value_type=str)},
                    {'use_sim_time': True}
                ],
                remappings=[('/tf', 'tf'),('/tf_static', 'tf_static')],
            ),

            Node(
                package='ros_gz_sim',
                executable='create',
                output='screen',
                arguments=[
                    '-topic', 'robot_description', 
                    '-name', robot["name"],
                    '-x', robot["x"],
                    '-y', robot["y"],
                    ],
            ),


            Node(
                package="controller_manager",
                executable="spawner",
                arguments=[
                    "joint_state_broadcaster",
                    "--controller-manager",
                    f'/{name}/controller_manager',
                ],
                output="screen",
            ),

            Node(
                package='controller_manager',
                executable='spawner',
                arguments=[
                    'swerve_drive_controller',
                    '--controller-manager',
                    f'/{name}/controller_manager',
                    '--param-file',
                    robot["controller"],
                ],
                output="screen",
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
                    os.path.join(nav2_share, 'launch', 'bringup_launch.py')),
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
                condition=IfCondition(EqualsSubstitution(LaunchConfiguration("rviz_mode"),"per_robot")),
                ),
        ])

        ld.add_action(robot_group)

    # -----------------------------------------------------
    # Shared RViz
    # -----------------------------------------------------
    ld.add_action(Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', shared_rviz_config],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(EqualsSubstitution(LaunchConfiguration("rviz_mode"),"shared")),

    ))

    return ld
