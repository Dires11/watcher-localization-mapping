"""
rtabmap.launch.py

Launches the ICP odometry node and RTAB-Map SLAM node.

ICP odometry consumes:
  - cam0 3D point cloud → estimates heading-accurate /icp_odom

RTAB-Map consumes:
  - cam0 RGB-D (primary camera, front-facing)
  - /icp_odom from icp_odometry (replaces ZED VIO to fix heading drift)
  - /scan from pointcloud_to_laserscan (proximity loop closure)

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

    # ICP odometry node: estimates frame-to-frame pose from the ZED 3D point
    # cloud using Iterative Closest Point.  This replaces ZED's visual-inertial
    # odometry (which lacks IMU data in SVO files and drifts in heading) with
    # scan-based odometry that is far more accurate for heading estimation.
    # publish_tf=false avoids conflicting with the ZED/EKF TF publishers.
    icp_odom_node = Node(
        package='rtabmap_odom',
        executable='icp_odometry',
        name='icp_odometry',
        output='screen',
        parameters=[{
            'frame_id':                      'cam0_camera_link',
            'odom_frame_id':                 'odom',
            'publish_tf':                    False,
            'wait_for_transform':            1.0,
            # PointToPlane is disabled: in flat outdoor scenes (pavement + open sky)
            # the structural complexity check fires and constrains translation to the
            # floor-normal direction only, wiping out horizontal (X/Y) motion entirely.
            # PointToPoint ICP does unconstrained matching and works correctly outdoors.
            'Icp/PointToPlane':              'false',
            'Icp/Iterations':                '30',
            'Icp/VoxelSize':                 '0.1',   # 10 cm voxels — speed vs. accuracy
            'Icp/MaxCorrespondenceDistance': '1.0',   # metres
            'Icp/MaxTranslation':            '2.0',   # allow large inter-frame motion
            'Icp/MaxRotation':               '1.57',  # allow up to 90°
            # Frame-to-Frame: each cloud matches only the previous frame.
            # Avoids the large pose jumps (high variance) that Frame-to-Map
            # produces when its growing local map drifts and misaligns.
            'Odom/Strategy':                 '0',
            # BEST_EFFORT QoS — ZED publishes with SensorDataQoS
            'qos_scan_cloud':                2,
        }],
        remappings=[
            ('scan_cloud', '/cam0/cam0/point_cloud/cloud_registered'),
            # Remap scan to a dead topic — icp_odometry auto-subscribes to both
            # scan and scan_cloud; with scan_cloud active, scan must be suppressed
            # to avoid the "both subscribers cannot be used" error.
            ('scan',       '/disabled/icp_scan'),
            ('odom',       '/icp_odom'),
        ],
    )

    # Override SLAM vs. localisation mode and DB path from launch args.
    # rtabmap_ros ROS2 uses "database_path" (not "Mem/DBPath") as the ROS
    # parameter name for the database file location.
    overrides = {
        'Mem/IncrementalMemory': 'false' if localization_only else 'true',
        'database_path': rtabmap_db,
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
            # ICP odometry replaces ZED's VIO — eliminates heading drift from
            # missing IMU data in SVO recordings
            ('odom',            '/icp_odom'),
            # Laser scan for proximity loop closure detection
            ('scan',            '/scan'),
            # Map output
            ('grid_map',        '/map'),
        ],
    )

    return [icp_odom_node, rtabmap_node]


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
