import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, RegisterEventHandler, TimerAction, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution, FindExecutable
from launch_ros.actions import Node, SetRemap, PushRosNamespace
from ros_gz_bridge.actions import RosGzBridge
from ros_gz_sim.actions import GzServer
from launch_ros.parameter_descriptions import ParameterValue
from launch.event_handlers import OnProcessExit



def generate_launch_description():
    # Package paths
    pkg_share = get_package_share_directory('multiple_robots')
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')
    nav2_share = get_package_share_directory('nav2_bringup')


    # File paths
    world_path = os.path.join(pkg_share, 'world', 'simple_world.sdf')
    remappings = [('/tf', 'tf'), ('/tf_static', 'tf_static')]

    # Robots information

    robots = [
        {
            'name': 'robot1',
            'x': '-7.5',
            'y': '-8.5',
            'yaw': '0.0',
            'model': os.path.join(pkg_share, 'description', 'robot1_swerve_bot.urdf'),
            'controller': os.path.join(pkg_share, 'config', 'robot1_swerve_drive_controllers_params.yaml'),
            'nav2': os.path.join(pkg_share, 'config', 'robot1_nav2_params.yaml'),
            'ekf': os.path.join(pkg_share, 'config', 'robot1_ekf.yaml'),
            'bridge': os.path.join(pkg_share, 'config', 'robot1_bridge_config.yaml'),
            'rviz': os.path.join(pkg_share, 'rviz', 'robot1_config.rviz'), 
            'map': os.path.join(pkg_share, 'config', 'robots_map.yaml')
        },
        {
            'name': 'robot2',
            'x': '-5.5',
            'y': '-8.5',
            'yaw': '0.0',
            'model': os.path.join(pkg_share, 'description', 'robot2_swerve_bot.urdf'),
            'controller': os.path.join(pkg_share, 'config', 'robot2_swerve_drive_controllers_params.yaml'),
            'nav2': os.path.join(pkg_share, 'config', 'robot2_nav2_params.yaml'),
            'ekf': os.path.join(pkg_share, 'config', 'robot2_ekf.yaml'),
            'bridge': os.path.join(pkg_share, 'config', 'robot2_bridge_config.yaml'),
            'rviz': os.path.join(pkg_share, 'rviz', 'robot2_config.rviz'), 
            'map': os.path.join(pkg_share, 'config', 'robots_map.yaml')           
        },
        {
            'name': 'robot3',
            'x': '-3.5',
            'y': '-8.5',
            'yaw': '0.0',
            'model': os.path.join(pkg_share, 'description', 'robot3_swerve_bot.urdf'),
            'controller': os.path.join(pkg_share, 'config', 'robot3_swerve_drive_controllers_params.yaml'),
            'nav2': os.path.join(pkg_share, 'config', 'robot3_nav2_params.yaml'),
            'ekf': os.path.join(pkg_share, 'config', 'robot3_ekf.yaml'),
            'bridge': os.path.join(pkg_share, 'config', 'robot3_bridge_config.yaml'),
            'rviz': os.path.join(pkg_share, 'rviz', 'robot3_config.rviz'), 
            'map': os.path.join(pkg_share, 'config', 'robots_map.yaml')           
        }
    ]

    # Gazebo

    start_gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')),
        launch_arguments={
            'gz_args': f"-r {world_path}"
        }.items(),      
    )

    clock = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
    )

    # Multi robot launch

    robot_groups=[]
    for robot in robots:

        namespace=robot['name']

        robot_group=GroupAction([

            # GZ-ROS bridge
            Node(
                package='ros_gz_bridge',
                executable='parameter_bridge',
                namespace=namespace,
                parameters=[{
                    'config_file': robot['bridge'],
                    'expand_gz_topic_names': True,
                    'use_sim_time': True,
                }],
            ),

            # Robot state publisher
            Node(
                package='robot_state_publisher',
                executable='robot_state_publisher',
                output='screen',
                namespace=namespace,
                parameters=[{
                    'robot_description': ParameterValue(Command([PathJoinSubstitution([FindExecutable(name='xacro')]),' ',robot['model'],]),value_type=str),
                    'use_sim_time': True,
                }],
                remappings=remappings,
            ),

            # Load model in GZ
            Node(
                package='ros_gz_sim',
                executable='create',
                output='screen',
                arguments=[
                    '-topic', f'{namespace}/robot_description', 
                    '-name', robot['name'],
                    '-x', robot['x'],
                    '-y', robot['y'],
                    '-Y', robot['yaw']],
            ),
           
            # Localization
            Node(
                package='robot_localization',
                executable='ekf_node',
                name='ekf_filter_node',
                output='screen',
                namespace=namespace,
                parameters=[
                    'params', robot['ekf'],
                    {'use_sim_time': True},
                ],
                remappings=remappings
            ),

            # Controllers
            Node(
                package="controller_manager",
                executable="spawner",
                output="screen",
                namespace=namespace,
                arguments=[
                    'joint_state_broadcaster',
                    '--controller-manager',
                    f'/{namespace}/controller_manager',
                    ],
            ),
            Node(
                package='controller_manager',
                executable='spawner',
                output="screen",
                namespace=namespace,
                arguments=[
                    'swerve_drive_controller',
                    '--controller-manager',
                    f'/{namespace}/controller_manager',
                    '--param-file',
                    robot['controller'],
                ],
            ),

            # Rivz
            Node(
                package='rviz2',
                executable='rviz2',
                output='screen',
                namespace=namespace,
                arguments=['-d', robot['rviz']],
                parameters=[{'use_sim_time': True}],
                remappings=[
                    ('/map', 'map'),
                    ('/tf', 'tf'),
                    ('/tf_static', 'tf_static'),
                    ('/goal_pose', 'goal_pose'),
                    ('/clicked_point', 'clicked_point'),
                    ('/initialpose', 'initialpose'),
                ],  
            ),

            # Nav2 delayed
            TimerAction(
                period=2.0,  
                actions=[
                    IncludeLaunchDescription(
                        PythonLaunchDescriptionSource(
                            os.path.join(nav2_share, 'launch', 'bringup_launch.py')
                        ),
                        launch_arguments={
                            'use_sim_time': 'True',
                            'autostart': 'True',
                            'map': robot['map'],
                            'params_file': robot['nav2'],
                            'namespace': namespace,
                            'use_namespace': 'True',
                        }.items(),
                    )
                ]
            ),

         
        ])
        robot_groups.append(robot_group)


  
    return LaunchDescription([
            

        #Launching Description Nodes, Rviz and Gazebo
        start_gazebo,
        clock,
        *robot_groups,
        
    ])
