"""
odometry_fusion.launch.py

Launches the robot_localization EKF node to fuse visual-inertial odometry
from up to 3 ZED Mini cameras into a single /odom topic and odom→base_link TF.

Arguments:
  num_cameras    How many cameras are active (1, 2, or 3).  Default: 3
                 Only the first num_cameras odometry sources are enabled.
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_ekf(context, *args, **kwargs):
    num_cameras = int(LaunchConfiguration('num_cameras').perform(context))

    pkg = get_package_share_directory('wheelchair_slam')
    ekf_params = os.path.join(pkg, 'config', 'ekf_params.yaml')

    # When fewer than 3 cameras are active, override the unused odometry
    # sources with empty strings so robot_localization ignores them.
    # Disable unused odometry sources by pointing them to non-existent topics.
    # robot_localization will simply never receive data on those topics.
    param_overrides = {}
    if num_cameras < 2:
        param_overrides['odom1'] = '/disabled/cam1/odom'
    if num_cameras < 3:
        param_overrides['odom2'] = '/disabled/cam2/odom'

    return [
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            output='screen',
            parameters=[
                ekf_params,
                param_overrides,
            ],
            remappings=[
                ('odometry/filtered', '/odom'),
            ],
        )
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'num_cameras', default_value='3',
            description='Number of active ZED cameras (1, 2, or 3)'
        ),
        OpaqueFunction(function=launch_ekf),
    ])
