#!/usr/bin/env python

import rospy
from geometry_msgs.msg import PoseStamped
from styx_msgs.msg import Lane, Waypoint

import math

import numpy as np
from scipy.spatial import KDTree
from std_msgs.msg import Int32
'''
This node will publish waypoints from the car's current position to some `x` distance ahead.

As mentioned in the doc, you should ideally first implement a version which does not care
about traffic lights or obstacles.

Once you have created dbw_node, you will update this node to use the status of traffic lights too.

Please note that our simulator also provides the exact location of traffic lights and their
current status in `/vehicle/traffic_lights` message. You can use this message to build this node
as well as to verify your TL classifier.

TODO (for Yousuf and Aaron): Stopline location for each traffic light.
'''

LOOKAHEAD_WPS   = 50 # Number of waypoints we will publish. You can change this number
MAXDECEL        = 0.5

class WaypointUpdater(object):


    def __init__(self):
        rospy.init_node('waypoint_updater')

        rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)

        # TODO: Add a subscriber for /traffic_waypoint and /obstacle_waypoint below
        rospy.Subscriber('/traffic_waypoint', Int32, self.traffic_cb)
        rospy.Subscriber('/obstacle_waypoint', Lane, self.obstacle_cb)

        self.final_waypoints_pub = rospy.Publisher('final_waypoints', Lane, queue_size=1)

        # TODO: Add other member variables you need below
        self.current_pose = None
        self.waypoints    = None
        self.traffic_waypoints  = None
        self.obstacle_waypoints = None
        self.waypoints_2d       = None
        self.waypoint_tree      = None
        self.stopline_wp_idx    = -1
        self.loop()

    def pose_cb(self, msg):
        # TODO: Implement
        self.current_pose = msg

    def waypoints_cb(self, msg):
        # TODO: Implement
        self.waypoints    = msg.waypoints
        if not self.waypoints_2d:
            self.waypoints_2d = [[waypoint.pose.pose.position.x, waypoint.pose.pose.position.y] for waypoint in self.waypoints]
            self.waypoint_tree = KDTree(self.waypoints_2d)


    def traffic_cb(self, msg):
        # TODO: Callback for /traffic_waypoint message. Implement
        self.stopline_wp_idx = msg.data

    def obstacle_cb(self, msg):
        # TODO: Callback for /obstacle_waypoint message. We will implement it later
        pass

    def get_waypoint_velocity(self, waypoint):
        return waypoint.twist.twist.linear.x

    def set_waypoint_velocity(self, waypoints, waypoint, velocity):
        waypoints[waypoint].twist.twist.linear.x = velocity

    def distance(self, waypoints, wp1, wp2):
        dist = 0
        dl = lambda a, b: math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2  + (a.z-b.z)**2)
        for i in range(wp1, wp2+1):
            dist += dl(waypoints[wp1].pose.pose.position, waypoints[i].pose.pose.position)
            wp1 = i
        return dist


    def loop(self):
        rate = rospy.Rate(50)
        rospy.loginfo("Test1")
        while not rospy.is_shutdown():
            #rospy.loginfo("Test2",)
            if self.current_pose and self.waypoint_tree:
                
                self.publish_waypoints()
            rate.sleep()     

    
    def get_closest_waypoint_idx(self):

        current_postion_coord = [self.current_pose.pose.position.x, self.current_pose.pose.position.y]
        closest_wp_idx = self.waypoint_tree.query(current_postion_coord, 1)[1]

        closest_wp_coord = self.waypoints_2d[closest_wp_idx]
        prev_wp_coord    = self.waypoints_2d[closest_wp_idx - 1]

        closest_wp         = np.array(closest_wp_coord)
        prev_wp            = np.array(prev_wp_coord)
        current_postion_wp = np.array(current_postion_coord)

        val = np.dot(closest_wp - prev_wp, current_postion_wp - closest_wp)

        if val > 0:
            closest_wp_idx = (closest_wp_idx + 1) % len(self.waypoints_2d)

        return closest_wp_idx      

    def publish_waypoints(self):
        final_lane = self.generate_lane()
        self.final_waypoints_pub.publish(final_lane)

    def generate_lane(self):
        lane = Lane()
        closest_wp_idx  = self.get_closest_waypoint_idx()
        wp_to_publish = self.waypoints[closest_wp_idx : closest_wp_idx + LOOKAHEAD_WPS]

        if self.stopline_wp_idx == -1 or (self.stopline_wp_idx >= (closest_wp_idx + LOOKAHEAD_WPS)):
            lane.waypoints = wp_to_publish
        else:
            lane.waypoints = self.decelerate_waypoints(wp_to_publish, closest_wp_idx)
        return lane  
    
        


    def decelerate_waypoints(self, waypoints, closest_wp_idx):
        temp = []   
        for i, wp in enumerate(waypoints):
            p = Waypoint()
            p.pose = wp.pose
            
            stop_wp_idx = max(self.stopline_wp_idx - closest_wp_idx - 2, 0)
            dist        = self.distance(waypoints, i, stop_wp_idx)
            vel         = math.sqrt(2 * MAXDECEL * dist)

            if vel < 1.0:
                vel = 0.0

            p.twist.twist.linear.x = min(vel, wp.twist.twist.linear.x)
            temp.append(p)

        return temp        



 

if __name__ == '__main__':
    try:
        WaypointUpdater()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start waypoint updater node.')
