#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TwistStamped


class StampedFilterNode(Node):

    def __init__(self):
        super().__init__('stamped_filter_node')

        # ---- Parameters ----
        self.declare_parameter('input_topic', 'cmd_vel')
        self.declare_parameter('output_topic', 'cmd_vel_stamped')
        self.declare_parameter('frame_id', 'base_link')

        self.input_topic = self.get_parameter('input_topic').value
        self.output_topic = self.get_parameter('output_topic').value
        self.frame_id = self.get_parameter('frame_id').value

        # ---- Publisher ----
        self.publisher = self.create_publisher(
            TwistStamped,
            self.output_topic,
            10
        )

        # ---- Subscriber ----
        self.subscription = self.create_subscription(
            Twist,
            self.input_topic,
            self.callback,
            10
        )

    def callback(self, msg: Twist):
        stamped_msg = TwistStamped()

        # Copy twist data
        stamped_msg.twist = msg

        # Add timestamp
        stamped_msg.header.stamp = self.get_clock().now().to_msg()

        # Add frame_id
        stamped_msg.header.frame_id = self.frame_id

        # Publish
        self.publisher.publish(stamped_msg)


def main(args=None):
    rclpy.init(args=args)
    node = StampedFilterNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()