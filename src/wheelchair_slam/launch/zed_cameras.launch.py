"""
zed_cameras.launch.py

Launches one zed_camera.launch.py (from the ZED wrapper) per camera,
each in its own namespace (cam0, cam1, cam2).

Arguments:
  num_cameras    Number of cameras to launch (1, 2, or 3).  Default: 3
  use_svo        Set to 'true' to replay an SVO file instead of live cameras.
  svo_file       Absolute path to the .svo file (required when use_svo=true).
  svo_loop       Set to 'true' to loop SVO playback.  Default: false
"""

import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration


def load_camera_params():
    pkg = get_package_share_directory('wheelchair_slam')
    cfg_path = os.path.join(pkg, 'config', 'camera_params.yaml')
    with open(cfg_path, 'r') as f:
        return yaml.safe_load(f)


def launch_zed_nodes(context, *args, **kwargs):
    num_cameras = int(LaunchConfiguration('num_cameras').perform(context))
    use_svo     = LaunchConfiguration('use_svo').perform(context).lower() == 'true'
    svo_file    = LaunchConfiguration('svo_file').perform(context)
    svo_loop    = LaunchConfiguration('svo_loop').perform(context).lower() == 'true'

    cfg = load_camera_params()
    cam_cfgs = cfg.get('cameras', {})

    pkg_slam = get_package_share_directory('wheelchair_slam')
    pkg_zed  = get_package_share_directory('zed_wrapper')

    zed_launch_file = os.path.join(
        pkg_zed, 'launch', 'zed_camera.launch.py'
    )
    override_yaml = os.path.join(
        pkg_slam, 'config', 'zed_override.yaml'
    )

    nodes = []
    cam_keys = ['cam0', 'cam1', 'cam2'][:num_cameras]

    for cam_key in cam_cfgs:
        if cam_key not in cam_keys:
            continue
        cam = cam_cfgs[cam_key]

        launch_args = {
            # Use cam_key (cam0/cam1/cam2) as both namespace and camera_name so
            # all topics land at /cam0/..., /cam1/..., /cam2/...
            # and TF frames are named cam0_camera_link, etc.
            'namespace':    cam_key,
            'camera_name':  cam_key,
            'camera_model': 'zedm',     # ZED Mini

            # Our parameter overrides (depth mode, frame rate, IMU fusion, etc.)
            'ros_params_override_path': override_yaml,

            # Let the ZED wrapper publish its own camera URDF in its namespace.
            # Without this, the ZED hangs on "Waiting for valid static
            # transformations" and never starts publishing frames.
            # The ZED's robot_state_publisher uses topic cam0_description (not
            # /robot_description) so it does not conflict with ours.
            'publish_urdf':    'true',
            # Do NOT publish map→odom — RTAB-Map owns that transform
            'publish_map_tf':  'false',
            # DO publish odom→camera_link (used by point cloud transforms)
            'publish_tf':      'true',
        }

        # SVO playback
        if use_svo:
            launch_args['svo_path'] = svo_file
            # Always publish the SVO clock so all nodes share SVO timestamps
            launch_args['publish_svo_clock'] = 'true'
        else:
            sn = cam.get('serial_number', '0')
            if sn != '0':
                launch_args['serial_number'] = sn

        nodes.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(zed_launch_file),
                launch_arguments=launch_args.items(),
            )
        )

    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'num_cameras', default_value='3',
            description='Number of ZED Mini cameras to launch (1, 2, or 3)'
        ),
        DeclareLaunchArgument(
            'use_svo', default_value='false',
            description='Replay an SVO file instead of live cameras'
        ),
        DeclareLaunchArgument(
            'svo_file', default_value='',
            description='Absolute path to the .svo recording file'
        ),
        DeclareLaunchArgument(
            'svo_loop', default_value='false',
            description='Loop SVO playback'
        ),
        OpaqueFunction(function=launch_zed_nodes),
    ])
