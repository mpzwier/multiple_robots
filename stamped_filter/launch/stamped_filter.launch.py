from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():

    config = PathJoinSubstitution([
        FindPackageShare('stamped_filter'),
        'config',
        'stamped_filter.yaml'
    ])

    return LaunchDescription([

        Node(
            package='stamped_filter',
            executable='stamped_filter_node',
            name='stamped_filter_node',
            parameters=[config],
            output='screen'
        )

    ])