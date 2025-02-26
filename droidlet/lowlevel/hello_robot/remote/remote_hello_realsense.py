"""
Copyright (c) Facebook, Inc. and its affiliates.
"""
# python -m Pyro4.naming -n <MYIP>
import logging
import os
import json
import time
import copy
from math import *

import pyrealsense2 as rs
import Pyro4
import numpy as np
import cv2
from droidlet.lowlevel.hello_robot.remote.utils import transform_global_to_base, goto
from slam_pkg.utils import depth_util as du


# Configure depth and color streams
CH = 480
CW = 640
FREQ = 30

Pyro4.config.SERIALIZER = "pickle"
Pyro4.config.SERIALIZERS_ACCEPTED.add("pickle")
Pyro4.config.ITER_STREAMING = True

# #####################################################

@Pyro4.expose
class RemoteHelloRobot(object):
    """Hello Robot interface"""

    def __init__(self, bot):
        self.bot = bot
        self._done = True
        self._connect_to_realsense()
        # Slam stuff
        #uv_one_in_cam
        intrinsic_mat = np.asarray(self.get_intrinsics())
        intrinsic_mat_inv = np.linalg.inv(intrinsic_mat)
        img_resolution = self.get_img_resolution()
        img_pixs = np.mgrid[0 : img_resolution[1] : 1, 0 : img_resolution[0] : 1] # Camera on the hello is oriented vertically
        img_pixs = img_pixs.reshape(2, -1)
        img_pixs[[0, 1], :] = img_pixs[[1, 0], :]
        uv_one = np.concatenate((img_pixs, np.ones((1, img_pixs.shape[1]))))
        self.uv_one_in_cam = np.dot(intrinsic_mat_inv, uv_one)
    
    def get_camera_transform(self):
        return self.bot.get_camera_transform()

    def _connect_to_realsense(self):
        config = rs.config()
        pipeline = rs.pipeline()
        config.enable_stream(rs.stream.color, CW, CH, rs.format.bgr8, 30)
        config.enable_stream(rs.stream.depth, CW, CH, rs.format.z16, 30)

        cfg = pipeline.start(config)
        dev = cfg.get_device()

        depth_sensor = dev.first_depth_sensor()
        #set high accuracy: https://github.com/IntelRealSense/librealsense/issues/2577#issuecomment-432137634
        depth_sensor.set_option(rs.option.visual_preset, 3)
        self.realsense = pipeline

        profile = pipeline.get_active_profile()
        # because we align the depth frame to the color frame, and only use the aligned depth frame,
        # we need to use the intrinsics of the color frame
        color_profile = rs.video_stream_profile(profile.get_stream(rs.stream.color))
        i = color_profile.get_intrinsics()
        self.intrinsic_mat = np.array([[i.fx, 0,    i.ppx],
                                       [0,    i.fy, i.ppy],
                                       [0,    0,    1]])
        align_to = rs.stream.color
        self.align = rs.align(align_to)
        print("connected to realsense")

    def get_intrinsics(self):
        return self.intrinsic_mat

    def get_img_resolution(self, rotate=True):
        if rotate:
            return (CW, CH)
        else:
            return (CH, CW)

    def test_connection(self):
        print("Connected!!")  # should print on server terminal
        return "Connected!"  # should print on client terminal

    def get_rgb_depth(self, rotate=True):
        tm = time.time()
        frames = None
        while not frames:
            frames = self.realsense.wait_for_frames()
            aligned_frames = self.align.process(frames)

            # Get aligned frames
            aligned_depth_frame = aligned_frames.get_depth_frame() # aligned_depth_frame is a 640x480 depth image
            color_frame = aligned_frames.get_color_frame()

            # Validate that both frames are valid
            if not aligned_depth_frame or not color_frame:
                continue

            depth_image = np.asanyarray(aligned_depth_frame.get_data()) / 1000 # convert to meters
            color_image = np.asanyarray(color_frame.get_data())

            # rotate
            if rotate:
                depth_image = np.rot90(depth_image, k=1, axes=(1,0))
                color_image = np.rot90(color_image, k=1, axes=(1,0))

        return color_image, depth_image

    def get_pcd_data(self, rotate=True):
        """Gets all the data to calculate the point cloud for a given rgb, depth frame."""
        rgb, depth = self.get_rgb_depth(rotate=rotate)
        depth *= 1000  # convert to mm
        # cap anything more than np.power(2,16)~ 65 meter
        depth[depth > np.power(2, 16) - 1] = np.power(2, 16) - 1
        depth = depth.astype(np.uint16)
        T = self.get_camera_transform()
        rot = T[:3, :3]
        trans = T[:3, 3]
        base2cam_trans = np.array(trans).reshape(-1, 1)
        base2cam_rot = np.array(rot)
        return rgb, depth, base2cam_rot, base2cam_trans

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pass in server device IP")
    parser.add_argument(
        "--ip",
        help="Server device (robot) IP. Default is 192.168.0.0",
        type=str,
        default="0.0.0.0",
    )

    args = parser.parse_args()

    np.random.seed(123)

    with Pyro4.Daemon(args.ip) as daemon:
        bot = Pyro4.Proxy("PYRONAME:hello_robot@" + args.ip)
        robot = RemoteHelloRobot(bot)
        robot_uri = daemon.register(robot)
        with Pyro4.locateNS() as ns:
            ns.register("hello_realsense", robot_uri)

        print("Server is started...")
        # try:
        #     while True:
        #         print(time.asctime(), "Waiting for requests...")
                
        #         sockets = daemon.sockets
        #         ready_socks = select.select(sockets, [], [], 0)
        #         events = []
        #         for s in ready_socks:
        #             events.append(s)
        #         daemon.events(events)
        #         time.sleep(0.0)
        # except KeyboardInterrupt:
        #     pass
        def callback():
            time.sleep(0.)
            return True
        daemon.requestLoop(callback)
