"""
pointcloud_merger.py

Subscribes to N point cloud topics, transforms each into base_link frame
using tf2, concatenates them, and publishes a single merged cloud.

No pcl_ros dependency — uses only sensor_msgs and tf2_ros which are always
available in a ROS2 Jazzy desktop install.

Topics:
  Subscribes:  /cam0/zed_node/point_cloud/cloud_registered  (and cam1, cam2)
  Publishes:   /merged_cloud  (sensor_msgs/PointCloud2, frame: base_link)
"""

import struct
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import PointCloud2, PointField
from tf2_ros import Buffer, TransformListener
import tf2_sensor_msgs  # registers the PointCloud2 transform


class PointCloudMerger(Node):

    def __init__(self):
        super().__init__('pointcloud_merger')

        self.declare_parameter('input_topics', [
            '/cam0/zed_node/point_cloud/cloud_registered',
        ])
        self.declare_parameter('output_frame', 'base_link')
        self.declare_parameter('output_topic', '/merged_cloud')
        self.declare_parameter('max_delay_sec', 0.15)

        topics = self.get_parameter('input_topics').value
        self._output_frame = self.get_parameter('output_frame').value
        output_topic = self.get_parameter('output_topic').value
        self._max_delay = self.get_parameter('max_delay_sec').value

        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)

        best_effort_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=5,
        )

        self._clouds = {t: None for t in topics}

        for topic in topics:
            self.create_subscription(
                PointCloud2, topic,
                lambda msg, t=topic: self._cloud_cb(msg, t),
                best_effort_qos,
            )

        self._pub = self.create_publisher(PointCloud2, output_topic, 10)

        self.get_logger().info(
            f'PointCloudMerger: merging {len(topics)} cloud(s) → {output_topic}'
        )

    def _cloud_cb(self, msg: PointCloud2, topic: str):
        # Transform cloud into base_link frame
        try:
            cloud_in_base = tf2_sensor_msgs.do_transform_cloud(
                msg,
                self._tf_buffer.lookup_transform(
                    self._output_frame,
                    msg.header.frame_id,
                    rclpy.time.Time(),          # latest available transform
                    timeout=rclpy.duration.Duration(seconds=self._max_delay),
                )
            )
        except Exception as e:
            self.get_logger().warn(f'TF lookup failed for {topic}: {e}', throttle_duration_sec=5.0)
            return

        self._clouds[topic] = cloud_in_base
        self._publish_merged()

    def _publish_merged(self):
        clouds = [c for c in self._clouds.values() if c is not None]
        if not clouds:
            return

        if len(clouds) == 1:
            self._pub.publish(clouds[0])
            return

        # All clouds are already in base_link so fields and point_step must match.
        # ZED clouds all have the same layout (XYZ + RGB), so this is safe.
        merged = PointCloud2()
        merged.header.stamp = self.get_clock().now().to_msg()
        merged.header.frame_id = self._output_frame
        merged.fields = clouds[0].fields
        merged.point_step = clouds[0].point_step
        merged.is_dense = all(c.is_dense for c in clouds)
        merged.is_bigendian = clouds[0].is_bigendian
        merged.height = 1

        combined_data = b''.join(c.data.tobytes() if hasattr(c.data, 'tobytes') else bytes(c.data)
                                 for c in clouds)
        merged.data = combined_data
        merged.width = len(combined_data) // merged.point_step
        merged.row_step = len(combined_data)

        self._pub.publish(merged)


def main(args=None):
    rclpy.init(args=args)
    node = PointCloudMerger()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
