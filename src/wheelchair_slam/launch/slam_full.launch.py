"""
slam_full.launch.py  —  Master launch file for the wheelchair SLAM pipeline.

Brings up the complete localization and mapping stack in dependency order:
  1. robot_description   — URDF + static camera TFs
  2. zed_cameras         — ZED wrapper nodes (live or SVO)
  3. odometry_fusion     — EKF: multi-camera odom → /odom + odom→base_link TF
  4. pointcloud_merge    — PCL concat + laser scan → /merged_cloud + /scan
  5. rtabmap             — SLAM: RGB-D + odom + scan → /map + map→odom TF

Arguments:
  num_cameras        Number of ZED Mini cameras  (default: 3)
  use_svo            Use SVO file instead of live cameras  (default: false)
  svo_file           Absolute path to .svo recording
  svo_loop           Loop SVO playback  (default: false)
  localization_only  RTAB-Map localisation mode, no new mapping  (default: false)
  rtabmap_db         Path to RTAB-Map database  (default: /root/ros2_ws/maps/rtabmap.db)

Quick-start with the test recording:
  ros2 launch wheelchair_slam slam_full.launch.py \\
    use_svo:=true \\
    svo_file:=/root/ros2_ws/recordings/CSUN-outside-iii.svo \\
    num_cameras:=1
"""

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetParameter
from ament_index_python.packages import get_package_share_directory
import os


def get_launch_file(pkg, name):
    return PythonLaunchDescriptionSource(
        os.path.join(get_package_share_directory(pkg), 'launch', name)
    )


def launch_all(context, *args, **kwargs):
    num_cameras       = LaunchConfiguration('num_cameras').perform(context)
    use_svo           = LaunchConfiguration('use_svo').perform(context)
    svo_file          = LaunchConfiguration('svo_file').perform(context)
    svo_loop          = LaunchConfiguration('svo_loop').perform(context)
    localization_only = LaunchConfiguration('localization_only').perform(context)
    rtabmap_db        = LaunchConfiguration('rtabmap_db').perform(context)

    pkg = 'wheelchair_slam'

    actions = []

    # When replaying an SVO the message timestamps come from the recording
    # (~2024).  Without sim time every TF lookup against current wall-clock
    # (~2026) will fail.  publish_svo_clock (in zed_cameras.launch.py) already
    # publishes /clock with SVO time; we just need all nodes to consume it.
    if use_svo.lower() == 'true':
        actions.append(SetParameter(name='use_sim_time', value=True))

    actions.extend([
        # 1. Robot description + static TF tree
        IncludeLaunchDescription(
            get_launch_file(pkg, 'robot_description.launch.py'),
            launch_arguments={'num_cameras': num_cameras}.items(),
        ),

        # 2. ZED camera drivers
        IncludeLaunchDescription(
            get_launch_file(pkg, 'zed_cameras.launch.py'),
            launch_arguments={
                'num_cameras': num_cameras,
                'use_svo':     use_svo,
                'svo_file':    svo_file,
                'svo_loop':    svo_loop,
            }.items(),
        ),

        # 3. EKF odometry fusion
        IncludeLaunchDescription(
            get_launch_file(pkg, 'odometry_fusion.launch.py'),
            launch_arguments={'num_cameras': num_cameras}.items(),
        ),

        # 4. Point cloud merge + laser scan
        IncludeLaunchDescription(
            get_launch_file(pkg, 'pointcloud_merge.launch.py'),
            launch_arguments={'num_cameras': num_cameras}.items(),
        ),

        # 5. RTAB-Map SLAM
        IncludeLaunchDescription(
            get_launch_file(pkg, 'rtabmap.launch.py'),
            launch_arguments={
                'localization_only': localization_only,
                'rtabmap_db':        rtabmap_db,
            }.items(),
        ),

        # 6. RViz2 for visualisation
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', os.path.join(
                get_package_share_directory('wheelchair_slam'),
                'rviz', 'slam_debug.rviz'
            )],
        ),
    ])

    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'num_cameras', default_value='3',
            description='Number of ZED Mini cameras (1, 2, or 3)'
        ),
        DeclareLaunchArgument(
            'use_svo', default_value='false',
            description='Replay an SVO file instead of live cameras'
        ),
        DeclareLaunchArgument(
            'svo_file', default_value='',
            description='Absolute path to the .svo recording'
        ),
        DeclareLaunchArgument(
            'svo_loop', default_value='false',
            description='Loop SVO playback'
        ),
        DeclareLaunchArgument(
            'localization_only', default_value='false',
            description='RTAB-Map localisation-only mode (no new mapping)'
        ),
        DeclareLaunchArgument(
            'rtabmap_db', default_value='/root/ros2_ws/maps/rtabmap.db',
            description='Path to RTAB-Map SQLite database'
        ),
        OpaqueFunction(function=launch_all),
    ])
