"""
pointcloud_merge.launch.py

Converts ZED depth point clouds into a /scan laser scan for RTAB-Map.

Single-camera mode (num_cameras=1):
  Feeds cam0's point cloud directly into pointcloud_to_laserscan.

Multi-camera mode (num_cameras > 1):
  Our Python merger node concatenates all clouds in base_link frame first.

Arguments:
  num_cameras    How many cameras are active (1, 2, or 3).  Default: 3
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_merge_nodes(context, *args, **kwargs):
    num_cameras = int(LaunchConfiguration('num_cameras').perform(context))

    pkg = get_package_share_directory('wheelchair_slam')
    scan_params = os.path.join(pkg, 'config', 'scan_params.yaml')

    nodes = []

    if num_cameras == 1:
        # ── Single camera: feed directly into laser scan converter ──────────
        scan_node = Node(
            package='pointcloud_to_laserscan',
            executable='pointcloud_to_laserscan_node',
            name='pointcloud_to_laserscan_node',
            output='screen',
            parameters=[scan_params],
            remappings=[
                ('cloud_in', '/cam0/cam0/point_cloud/cloud_registered'),
                ('scan',     '/scan'),
            ],
        )
        nodes.append(scan_node)

    else:
        # ── Multi-camera: merge then convert ─────────────────────────────────
        # ZED topic: /<namespace>/<camera_name>/... where both equal cam{i}
        input_topics = [
            f'/cam{i}/cam{i}/point_cloud/cloud_registered'
            for i in range(num_cameras)
        ]

        merger_node = Node(
            package='wheelchair_slam',
            executable='pointcloud_merger',
            name='pointcloud_merger',
            output='screen',
            parameters=[{
                'input_topics':  input_topics,
                'output_frame':  'base_link',
                'output_topic':  '/merged_cloud',
                'max_delay_sec': 0.15,
            }],
        )
        nodes.append(merger_node)

        scan_node = Node(
            package='pointcloud_to_laserscan',
            executable='pointcloud_to_laserscan_node',
            name='pointcloud_to_laserscan_node',
            output='screen',
            parameters=[scan_params],
            remappings=[
                ('cloud_in', '/merged_cloud'),
                ('scan',     '/scan'),
            ],
        )
        nodes.append(scan_node)

    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'num_cameras', default_value='3',
            description='Number of active ZED cameras (1, 2, or 3)'
        ),
        OpaqueFunction(function=launch_merge_nodes),
    ])
