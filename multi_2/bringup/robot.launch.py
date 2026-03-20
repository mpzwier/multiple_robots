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
    pkg_share = get_package_share_directory('multi_2')
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')
    nav2_share = get_package_share_directory('nav2_bringup')


    # File paths
    world_path = os.path.join(pkg_share, 'world', 'simple_world.sdf')
    nav2_map_path = os.path.join(pkg_share, 'config', 'map.yaml')
    remappings = [('/tf', 'tf'), ('/tf_static', 'tf_static')]

    # Robots information

    robots = [
        {
            'name': 'swerve_bot1',
            'x': '0.0',
            'y': '0.0',
            'model': os.path.join(pkg_share, 'description', 'swerve_bot.urdf'),
            'controller': os.path.join(pkg_share, 'config', 'swerve_drive_controllers_params.yaml'),
            'nav2': os.path.join(pkg_share, 'config', 'nav2_params_simple.yaml'),
            'ekf': os.path.join(pkg_share, 'config', 'ekf.yaml'),
            'bridge': os.path.join(pkg_share, 'config', 'bridge_config.yaml'),
            'rviz': os.path.join(pkg_share, 'rviz', 'config_nav2.rviz'), #changed!
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
        tf_prefix=namespace+'/'

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
                    #'frame_prefix': tf_prefix,
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
                    '-y', robot['y']],
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
                            'map': nav2_map_path,
                            'params_file': robot["nav2"],
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
