# Multiple Robots ROS2 

Multipe robots (3 swerve drive and 3 diff drive) in Gazebo and Rviz with Nav2. Every node/topic/controller are linked to a robot by namespace.

![alt text](https://github.com/mpzwier/multiple_robots/blob/Jazzy/Gazebo.png?raw=true)

## Dependencies

The configurations in this repository assume you have the following prerequisites installed on the
device on which you want to run this code.

1. [ROS Jazzy](https://docs.ros.org/en/jazzy/Installation.html) with the following packages: robot state publisher, joint state broadcaster, robot localization, Nav2, Rviz2 and (GazeboSim Harmonic)

2. A working [ROS workspace](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.html).

## Usage

This package can be launched by using the command:

    ros2 launch multiple_robots robots.launch.py

You can start with goal planning if the Nav2 plugin in Rviz2 shows Navigation and Localization as active. Sometimes due to the large number of nodes to be launched, a single robot fails to launch, try to launch again, most of the time this will help.  

## Acknowledgement

This project incorporates code from ROBOTIS AI Worker and ROS2 control

The swerve drive controller: [ffw_swerve_drive_controller](https://github.com/ROBOTIS-GIT/ai_worker/tree/main/ffw_swerve_drive_controller) is used with the adaptation that the tf are relative and not global (/tf) so that every node/topic is namespace for each robot.

The differential controller is a copy of the ROS2 control diff drive controller, adapted so that the namenspace works properly and tf's are disabled (using tf_dummy) in order for ekf filter to publish the tf's.

## TO DO
- Make the launch a bit more stable, not always all robots will launch properly
- Make changes to Nav params file to have a better collision detection (correct footprints)
- Changes some speed setting so robots drive at different speeds
- Combine some of the config files, not all are really robot specific
- Make the bt_navigator of the swerve drive robots with a dual controller, general (more diff drive) and last part (more omni drive)

