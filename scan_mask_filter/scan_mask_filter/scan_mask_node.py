#!/usr/bin/env python3

import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class ScanMaskNode(Node):

    def __init__(self):
        super().__init__('scan_mask_node')

        # ---- Parameters ----
        self.declare_parameter('input_topic', '/scan')
        self.declare_parameter('output_topic', '/scan_masked')

        # Flat list: [start1, end1, start2, end2, ...]
        self.declare_parameter('sectors', [0.0, 0.0])

        self.input_topic = self.get_parameter('input_topic').value
        self.output_topic = self.get_parameter('output_topic').value
        sector_list = self.get_parameter('sectors').value

        # ---- Normalize & store sectors ----
        self.sectors = []
        for i in range(0, len(sector_list), 2):
            a = self.normalize_angle(sector_list[i])
            b = self.normalize_angle(sector_list[i + 1])
            self.sectors.append((a, b))

        # ---- Sub / Pub ----
        self.sub = self.create_subscription(
            LaserScan,
            self.input_topic,
            self.scan_callback,
            10
        )

        self.pub = self.create_publisher(
            LaserScan,
            self.output_topic,
            10
        )

        self.get_logger().info(
            f"Scan mask started\n"
            f"Input: {self.input_topic}\n"
            f"Output: {self.output_topic}\n"
            f"Sectors (rad, normalized): {self.sectors}"
        )

    # ---- Helpers ----
    def normalize_angle(self, angle):
        """Normalize angle to [-pi, pi]."""
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle

    def angle_in_sector(self, angle, start, end):
        """
        Check if angle is inside a sector.
        Handles wrap-around at ±pi.
        """
        if start <= end:
            return start <= angle <= end
        else:
            # Sector crosses the ±pi boundary
            return angle >= start or angle <= end

    # ---- Masking ----
    def scan_callback(self, msg):

        ranges = list(msg.ranges)

        for i in range(len(ranges)):
            angle = msg.angle_min + i * msg.angle_increment

            for start, end in self.sectors:
                if self.angle_in_sector(angle, start, end):
                    ranges[i] = msg.range_max
                    break

        # ---- Publish new scan ----
        out = LaserScan()
        out.header = msg.header
        out.angle_min = msg.angle_min
        out.angle_max = msg.angle_max
        out.angle_increment = msg.angle_increment
        out.time_increment = msg.time_increment
        out.scan_time = msg.scan_time
        out.range_min = msg.range_min
        out.range_max = msg.range_max
        out.ranges = ranges
        out.intensities = msg.intensities

        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = ScanMaskNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
