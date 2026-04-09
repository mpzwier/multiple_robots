from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():

    config = PathJoinSubstitution([
        FindPackageShare('scan_mask_filter'),
        'config',
        'scan_mask.yaml'
    ])

    return LaunchDescription([

        Node(
            package='scan_mask_filter',
            executable='scan_mask_node',
            name='scan_mask_node',
            parameters=[config],
            output='screen'
        )

    ])