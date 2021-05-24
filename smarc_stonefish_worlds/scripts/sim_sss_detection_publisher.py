#!/usr/bin/env python

import rospy
import numpy as np
from nav_msgs.msg import Odometry
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose
from visualization_msgs.msg import Marker, MarkerArray


class sim_sss_detector:
    """A mock SSS object detector for simulation. Only objects within the
    detection_range of the vehicle will be detectable."""
    def __init__(self, detection_range=5):
        self.detection_range = detection_range
        self.prev_pose = None
        self.current_pose = None
        self.marked_positions = {}

        self.odom_sub = rospy.Subscriber('/sam/dr/odom', Odometry,
                                         self._update_pose)
        self.marked_pos_sub = rospy.Subscriber('/sam/sim/marked_positions',
                                               MarkerArray,
                                               self._update_marked_positions)
        self.pub = rospy.Publisher('/sam/sim/sidescan/detection',
                                   Detection2DArray,
                                   queue_size=2)

    #TODO: get things into the correct frame. marked_positions is published in map frame,
    #      dr/odom is in world_ned
    def _update_marked_positions(self, msg):
        """Update marked_positions based on the MarkerArray msg received."""
        if len(self.marked_positions) > 0:
            return
        for marker in msg.markers:
            self.marked_positions[f'{marker.ns}/{marker.id}'] = marker

    def _update_pose(self, msg):
        """Update prev_pose and current_pose according to the odom msg received"""
        if not self.prev_pose:
            self.prev_pose = msg.pose.pose
            self.current_pose = msg.pose.pose

        self.prev_pose = self.current_pose
        self.current_pose = msg.pose.pose

        heading = self.calculate_heading()
        markers_in_range = self.get_markers_in_detection_range()
        print(heading)

    def _get_position_differences(self, position1, position2):
        dx = position1.x - position2.x
        dy = position1.y - position2.y
        dz = position1.z - position2.z
        return dx, dy, dz

    def _normalize_vector(self, position_array):
        """Given an np.ndarray, return the normalized equivalent"""
        norm = np.linalg.norm(position_array)
        if norm > 0:
            position_array = position_array / norm
        return position_array

    def calculate_heading(self):
        """Returns a unit vector of heading based on the difference between
        current_pose and prev_pose"""
        if not self.prev_pose or not self.current_pose:
            raise rospy.ROSException(
                'Not enough odom measurement for heading calculation')
        dx, dy, dz = self._get_position_differences(self.current_pose.position,
                                                    self.prev_pose.position)
        heading = np.array([dx, dy, dz]).reshape(-1, 1)
        heading = self._normalize_vector(position_array=heading)

        return heading

    def _calculate_distance_to_position(self, position):
        """Calculate the distance between current_pose.position and the
        given position"""
        dx, dy, dz = self._get_position_differences(position,
                                                    self.current_pose.position)
        return (dx**2 + dy**2 + dz**2)**.5

    def get_markers_in_detection_range(self):
        """Returns a list of markers within detection_range relative to
        self.current_pose"""
        markers_in_range = []
        for marker_name, marker in self.marked_positions:
            distance = self._calculate_distance_to_position(
                marker.pose.position)
            if distance < self.detection_range:
                markers_in_range.append(marker_name)
        return markers_in_range


def main():
    rospy.init_node('sim_sss_detection_publisher', anonymous=False)
    rospy.Rate(5)  # ROS Rate at 5Hz

    detector = sim_sss_detector()
    while not rospy.is_shutdown():
        rospy.spin()


if __name__ == '__main__':
    main()
