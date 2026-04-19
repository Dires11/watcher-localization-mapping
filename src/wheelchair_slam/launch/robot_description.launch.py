"""
robot_description.launch.py

Loads the wheelchair URDF/xacro and publishes:
  - /robot_description  (latched, consumed by robot_state_publisher)
  - Static TF: base_link → zed_camN_link for each camera

Camera mount positions are read from camera_params.yaml and passed as
xacro arguments so only the YAML needs updating when hardware is finalised.
"""

import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro


def load_camera_params():
    pkg = get_package_share_directory('wheelchair_slam')
    cfg_path = os.path.join(pkg, 'config', 'camera_params.yaml')
    with open(cfg_path, 'r') as f:
        return yaml.safe_load(f)


def generate_launch_description():
    pkg = get_package_share_directory('wheelchair_slam')
    urdf_path = os.path.join(pkg, 'urdf', 'wheelchair_base.urdf.xacro')

    num_cameras_arg = DeclareLaunchArgument(
        'num_cameras', default_value='3',
        description='Number of ZED Mini cameras (1, 2, or 3)'
    )
    num_cameras = LaunchConfiguration('num_cameras')

    cfg = load_camera_params()
    cams = cfg['cameras']

    def cam_arg(cam_key, field, default='0.0'):
        return str(cams.get(cam_key, {}).get(field, default))

    # Process xacro with camera mount positions from YAML
    # We resolve num_cameras at launch time via LaunchConfiguration, but xacro
    # needs a concrete value.  We pass all three camera poses unconditionally;
    # the xacro <xacro:if> guards handle exclusion based on num_cameras arg.
    xacro_args = {
        'cam0_x':     cam_arg('cam0', 'x_offset', '0.30'),
        'cam0_y':     cam_arg('cam0', 'y_offset', '0.00'),
        'cam0_z':     cam_arg('cam0', 'z_offset', '0.60'),
        'cam0_roll':  cam_arg('cam0', 'roll',  '0.0'),
        'cam0_pitch': cam_arg('cam0', 'pitch', '0.0'),
        'cam0_yaw':   cam_arg('cam0', 'yaw',   '0.0'),

        'cam1_x':     cam_arg('cam1', 'x_offset', '-0.10'),
        'cam1_y':     cam_arg('cam1', 'y_offset',  '0.25'),
        'cam1_z':     cam_arg('cam1', 'z_offset',  '0.55'),
        'cam1_roll':  cam_arg('cam1', 'roll',  '0.0'),
        'cam1_pitch': cam_arg('cam1', 'pitch', '0.0'),
        'cam1_yaw':   cam_arg('cam1', 'yaw',   '1.5708'),

        'cam2_x':     cam_arg('cam2', 'x_offset', '-0.10'),
        'cam2_y':     cam_arg('cam2', 'y_offset', '-0.25'),
        'cam2_z':     cam_arg('cam2', 'z_offset',  '0.55'),
        'cam2_roll':  cam_arg('cam2', 'roll',  '0.0'),
        'cam2_pitch': cam_arg('cam2', 'pitch', '0.0'),
        'cam2_yaw':   cam_arg('cam2', 'yaw',  '-1.5708'),

        # num_cameras controls which camera joints are generated in xacro
        'num_cameras': '3',
    }

    robot_description_content = xacro.process_file(
        urdf_path, mappings=xacro_args
    ).toxml()

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_content,
            'use_sim_time': False,
        }],
    )

    return LaunchDescription([
        num_cameras_arg,
        robot_state_publisher,
    ])
