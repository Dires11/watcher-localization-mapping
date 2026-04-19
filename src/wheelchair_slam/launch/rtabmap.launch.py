"""
rtabmap.launch.py

Launches the RTAB-Map SLAM node.

RTAB-Map consumes:
  - cam0 RGB-D (primary camera, front-facing)
  - /odom from the EKF
  - /scan from pointcloud_to_laserscan

And produces:
  - /map          nav_msgs/OccupancyGrid   (for Nav2)
  - map → odom TF (RTAB-Map is sole owner of this transform)

Arguments:
  localization_only   Set 'true' to disable mapping (use existing db).  Default: false
  rtabmap_db          Path to the RTAB-Map SQLite database.
                      Default: /root/ros2_ws/maps/rtabmap.db
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_rtabmap(context, *args, **kwargs):
    localization_only = (
        LaunchConfiguration('localization_only').perform(context).lower() == 'true'
    )
    rtabmap_db = LaunchConfiguration('rtabmap_db').perform(context)

    pkg = get_package_share_directory('wheelchair_slam')
    rtabmap_params = os.path.join(pkg, 'config', 'rtabmap_params.yaml')

    # Override SLAM vs. localisation mode and DB path from launch args
    overrides = {
        'Mem/IncrementalMemory': 'false' if localization_only else 'true',
        'Mem/DBPath': rtabmap_db,
    }

    rtabmap_node = Node(
        package='rtabmap_slam',
        executable='rtabmap',
        name='rtabmap',
        output='screen',
        parameters=[
            rtabmap_params,
            overrides,
        ],
        remappings=[
            # RGB-D input from cam0.
            # ZED topic path: /<namespace>/<camera_name>/...
            # namespace=cam0, camera_name=cam0 → /cam0/cam0/...
            ('rgb/image',       '/cam0/cam0/rgb/color/rect/image'),
            ('rgb/camera_info', '/cam0/cam0/rgb/color/rect/image/camera_info'),
            ('depth/image',     '/cam0/cam0/depth/depth_registered'),
            # Odometry — use ZED's VIO directly (EKF handles multi-cam fusion later)
            ('odom',            '/cam0/cam0/odom'),
            # Map output
            ('grid_map',        '/map'),
        ],
    )

    return [rtabmap_node]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'localization_only', default_value='false',
            description='Run in localisation-only mode (no new mapping)'
        ),
        DeclareLaunchArgument(
            'rtabmap_db', default_value='/root/ros2_ws/maps/rtabmap.db',
            description='Path to RTAB-Map SQLite database'
        ),
        OpaqueFunction(function=launch_rtabmap),
    ])
