#!/usr/bin/env python
# Set linear and angular values of Turtlesim's speed and turning.

import os
import select
import sys
import getkey

import rclpy  # Needed to create a ROS node
from geometry_msgs.msg import Twist  # Message that moves base
# from torch.distributed.tensor import empty
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from rclpy.action import ActionClient
from control_msgs.action import GripperCommand
from std_msgs.msg import Header
from rclpy.node import Node
from collections import namedtuple
from b4_fulfillment_interfaces.srv import DataCollect

import math
import time
import cv2

r1 = 130
r2 = 124
r3 = 126

th1_offset = - math.atan2(0.024, 0.128)
th2_offset = - 0.5 * math.pi - th1_offset

usage = """
Control Your OpenManipulator!
---------------------------
Joint Space Control:
- Joint1 : Increase (Y), Decrease (H)
- Joint2 : Increase (U), Decrease (J)
- Joint3 : Increase (I), Decrease (K)
- Joint4 : Increase (O), Decrease (L)

INIT : (1)

CTRL-C to quit
"""
joint_angle_delta = 0.05  # radian

Coordinate = namedtuple("Coordinate", ["x", "y", "z"])


class ManipulationNode(Node):
    # settings = None
    # if os.name != 'nt':
    # 	settings = termios.tcgetattr(sys.stdin)

    def __init__(self):
        super().__init__('ManipulationNode')
        key_value = ''

        self.cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)
        self.joint_pub = self.create_publisher(JointTrajectory, '/arm_controller/joint_trajectory', 10)
        self.gripper_action_client = ActionClient(self, GripperCommand, 'gripper_controller/gripper_cmd')

        self.gripper_state = 0

        # self.timer = self.create_timer(1.0, self.timer_callback)

        # Twist is geometry_msgs for linear and angular velocity
        self.move_cmd = Twist()
        # Linear speed in x in meters/second is + (forward) or
        #    - (backwards)
        self.move_cmd.linear.x = 1.3  # Modify this value to change speed
        # Turn at 0 radians/s
        self.move_cmd.angular.z = 0.8
        # Modify this value to cause rotation rad/s

        self.trajectory_msg = JointTrajectory()

        # # 박스 잡는 위치 테스트용
        # self.send_joint_pose_goal(200, 0, 40, r1, r2, r3)

        # 그리퍼 호출
        # # 집게 열기
        # open = self.send_gripper_goal('open')
        # # 집게 닫기
        # close = self.send_gripper_goal('close')

        # 자동 데이터 수집 서비스 서버 생성
        _ = self.create_service(
            DataCollect,
            'data_collect_service',
            self.handle_data_collect_service_request
        )
        # 자동 학습 기능
        self.auto_data_collection()

    def handle_data_collect_service_request(self, request, response):
        """
        # Request
        bool start
        ---
        # Response
        bool success

        """
        self.get_logger().info(f"자동 데이터 수집 시작: {request.start}")

        if self.auto_data_collection():
            response.success = True
        else:
            response.success = False

        return response


    def auto_data_collection(self):
        coordinates = [
            Coordinate(x=150, y=45, z=130),
            Coordinate(x=160, y=50, z=180),
            Coordinate(x=205, y=45, z=130),
            Coordinate(x=210, y=-55, z=130),
            Coordinate(x=155, y=-40, z=130)
        ]

        index = 1

        cap = cv2.VideoCapture('/dev/video0')
        # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # 가로 해상도 설정
        # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)  # 세로 해상도 설정

        time.sleep(2)

        for _ in range(30):
            for box in coordinates:
                self.send_joint_pose_goal(box.x, box.y, box.z, r1, r2, r3)
                time.sleep(6)

                self.get_image_data(cap=cap, index=index)
                time.sleep(3)
                index += 1

        cap.release()
        return True
        # cv2.destroyAllWindows()

    def get_image_data(self, cap, index):
        save_directory = "img_capture"
        os.makedirs(save_directory, exist_ok=True)

        # 처음 5개 프레임은 무시
        for _ in range(5):
            ret, frame = cap.read()

        # 유효한 이미지 캡처
        ret, frame = cap.read()
        if ret:  # 이미지 캡처가 성공적으로 되었는지 확인
            file_name = f'{save_directory}/box_{index}.jpg'
            cv2.imwrite(file_name, frame)
            print(f"Image saved. name:{file_name}")
        else:
            print("Failed to capture image.")

    def send_gripper_goal(self, action):
        position = -0.015
        if action == 'open':
            position = 0.025

        goal = GripperCommand.Goal()
        goal.command.position = position
        goal.command.max_effort = -1.0

        if not self.gripper_action_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().error("Gripper action server not available!")
            return None
        print("보냄")
        return self.gripper_action_client.send_goal_async(goal)


    def send_joint_pose_goal(self, x, y, z, r1, r2, r3):
        J0, J1, J2, J3, Sxy, sr1, sr2, sr3, St, Rt = self.solv_robot_arm2(x, y, z, r1, r2, r3)

        current_time = self.get_clock().now()
        self.trajectory_msg.header = Header()
        #		self.trajectory_msg.header.stamp = current_time.to_msg()
        self.trajectory_msg.header.frame_id = ''
        self.trajectory_msg.joint_names = ['joint1', 'joint2', 'joint3', 'joint4']

        point = JointTrajectoryPoint()
        # point.positions = [0.003, math.pi / 4.0, -0.489, 2.041]
        #		point.positions = [0.0] * 4
        point.positions = [Sxy, sr1 + th1_offset, sr2 + th2_offset, sr3]
        point.velocities = [0.0] * 4
        point.time_from_start.sec = 3
        point.time_from_start.nanosec = 0

        self.trajectory_msg.points = [point]
        self.joint_pub.publish(self.trajectory_msg)


    # author : karl.kwon (mrthinks@gmail.com)
    # r1 : distance J0 to J1
    # r2 : distance J1 to J2
    # r3 : distance J0 to J2
    def solv2(self, r1, r2, r3):
        d1 = (r3 ** 2 - r2 ** 2 + r1 ** 2) / (2 * r3)
        d2 = (r3 ** 2 + r2 ** 2 - r1 ** 2) / (2 * r3)

        s1 = math.acos(d1 / r1)
        s2 = math.acos(d2 / r2)

        return s1, s2

    # author : karl.kwon (mrthinks@gmail.com)
    # x, y, z : relational position from J0 (joint 0)
    # r1 : distance J0 to J1
    # r2 : distance J1 to J2
    # r3 : distance J2 to J3
    # sr1 : angle between z-axis to J0->J1
    # sr2 : angle between J0->J1 to J1->J2
    # sr3 : angle between J1->J2 to J2->J3 (maybe always parallel)
    def solv_robot_arm2(self, x, y, z, r1, r2, r3):
        Rt = math.sqrt(x ** 2 + y ** 2 + z ** 2)
        Rxy = math.sqrt(x ** 2 + y ** 2)
        St = math.asin(z / Rt)
        #   Sxy = math.acos(x / Rxy)
        Sxy = math.atan2(y, x)

        s1, s2 = self.solv2(r1, r2, Rt)

        sr1 = math.pi / 2 - (s1 + St)
        sr2 = s1 + s2
        sr2_ = sr1 + sr2
        sr3 = math.pi - sr2_

        J0 = (0, 0, 0)
        J1 = (J0[0] + r1 * math.sin(sr1) * math.cos(Sxy),
              J0[1] + r1 * math.sin(sr1) * math.sin(Sxy),
              J0[2] + r1 * math.cos(sr1))
        J2 = (J1[0] + r2 * math.sin(sr1 + sr2) * math.cos(Sxy),
              J1[1] + r2 * math.sin(sr1 + sr2) * math.sin(Sxy),
              J1[2] + r2 * math.cos(sr1 + sr2))
        J3 = (J2[0] + r3 * math.sin(sr1 + sr2 + sr3) * math.cos(Sxy),
              J2[1] + r3 * math.sin(sr1 + sr2 + sr3) * math.sin(Sxy),
              J2[2] + r3 * math.cos(sr1 + sr2 + sr3))

        return J0, J1, J2, J3, Sxy, sr1, sr2, sr3, St, Rt


def manipulation_controller(node=None):
    if node is None:
        print("node가 없습니다.")
        return
    key_value = getkey.getkey()

    if key_value == '1':
        node.trajectory_msg.points[0].positions = [0.0] * 4
        node.joint_pub.publish(node.trajectory_msg)
        print('joint1 +')
    elif key_value == 'y':
        node.trajectory_msg.points[0].positions[0] += joint_angle_delta
        node.joint_pub.publish(node.trajectory_msg)
        print('joint1 +')
    elif key_value == 'h':
        node.trajectory_msg.points[0].positions[0] -= joint_angle_delta
        node.joint_pub.publish(node.trajectory_msg)
        print('joint1 -')
    elif key_value == 'u':
        node.trajectory_msg.points[0].positions[1] += joint_angle_delta
        node.joint_pub.publish(node.trajectory_msg)
        print('joint2 +')
    elif key_value == 'j':
        node.trajectory_msg.points[0].positions[1] -= joint_angle_delta
        node.joint_pub.publish(node.trajectory_msg)
        print('joint2 -')
    elif key_value == 'i':
        node.trajectory_msg.points[0].positions[2] += joint_angle_delta
        node.joint_pub.publish(node.trajectory_msg)
        print('joint3 +')
    elif key_value == 'k':
        node.trajectory_msg.points[0].positions[2] -= joint_angle_delta
        node.joint_pub.publish(node.trajectory_msg)
        print('joint3 -')
    elif key_value == 'o':
        node.trajectory_msg.points[0].positions[3] += joint_angle_delta
        node.joint_pub.publish(node.trajectory_msg)
        print('joint4 +')
    elif key_value == 'l':
        node.trajectory_msg.points[0].positions[3] -= joint_angle_delta
        node.joint_pub.publish(node.trajectory_msg)
        print('joint4 -')
    elif key_value == 'q':
        return


def main(args=None):
    try:
        rclpy.init()
    except Exception as e:
        print(e)

    try:
        node = ManipulationNode()
    except Exception as e:
        print(e)

    try:
        while rclpy.ok():
            # rclpy.spin_once(node)
            if manipulation_controller(node):
                break

    except Exception as e:
        print(e)
    finally:
        # if os.name != 'nt':
        #     termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()