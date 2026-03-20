# Multiple Robots

A multipe (swerve) robots in Gazebo and Rviz with Nav2. Every node/topic/controller are linked to a robot by namespace.

## Dependencies

The configurations in this repository assume you have the following prerequisites installed on the
device on which you want to run this code.

1. [ROS Jazzy](https://docs.ros.org/en/jazzy/Installation.html) with the following packages: robot state publisher, joint state broadcaster, robot localization, Nav2, Rviz2 and (GazeboSim Harmonic)

2. A working [ROS workspace](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.html).

## Usage

This package can be launched by using the command:

    ros2 launch multiple_robots robots.launch.py

You can start with goal planning if the Nav2 plugin in Rviz2 shows Navigation and Localization as active

## Acknowledgement

This project incorporates code from ROBOTIS AI Worker

The swerve drive controller: [ffw_swerve_drive_controller](https://github.com/ROBOTIS-GIT/ai_worker/tree/main/ffw_swerve_drive_controller) is used with the adaptation that the 
tf are relative and not global (/tf) so that every node/topic is namespace for every robot.
