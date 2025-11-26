import cv2
import numpy as np
import math
import os
import sys
import math

heatmap_width = 92
heatmap_height = 92
# Joints Explained
# 14 joints:
# 0-right shoulder, 1-right elbow, 2-right wrist, 3-left shoulder, 4-left elbow, 5-left wrist,
# 6-right hip, 7-right knee, 8-right ankle, 9-left hip, 10-left knee, 11-left ankle,
# 12-top of the head and 13-neck

#                      12
#                      |
#                      |
#                0-----13-----3
#               /              \
#              1                4




JOINT_LIMB = [[12, 13], [13, 0], [13, 3]]
COLOR = [[0, 255, 0], [0, 255, 0], [0, 255, 0]]

RIGHT_LEFT_SHOULDER_DIFF = 17
SHOULDER_NECK_DIFF = 35
IDEAL_LEFT_SHOULDER_DIFF = 30
ANGLE_HEAD_SHOULDER_DIFF = 15
FRONT_HEAD_TILT = 10

def decode_pose(heatmaps, scale, image_original):
    """obtain joint list from heatmap"""

    # joint_list: a python list of joints, joint_list[i] is an numpy array with the (x,y) coordinates of
    # the i'th joint (refer to the 'Joints Explained' in this file, e.g., 0th joint is right shoulder)
    joint_list = [peak_index_to_coords(heatmap) * scale for heatmap in heatmaps]

    points_coordinates = []
    for i, point in enumerate(joint_list):
        x, y = point.astype(int)
        if i in [0, 3, 12, 13]:
            points_coordinates.append((i, x, y))
            if (i == 0):
                print(f"Right shoulder -  {i}: ({x}, {y})")
            if (i == 3):
                print(f"Left shoulder -  {i}: ({x}, {y})")
            if (i == 12):
                print(f"Head -  {i}: ({x}, {y})")
            if (i == 13):
                print(f"Neck -  {i}: ({x}, {y})")
    
    # start #
    
    # ideal  posture - lengths between points 0 and 13, 3 and 13, 12 and 13 respectively.
    # The "ideal" photo I took with straight spine, shoulders and head, that is why I will take received coordinates as "ideal".
    # Right shoulder -  0: (201, 276)
    # Left shoulder -  3: (480, 276)
    # Head -  12: (347, 10)
    # Neck -  13: (333, 208)
    ideal_right_shoulder_length = math.sqrt((333 - 201) ** 2 + (208 - 276) ** 2)
    ideal_left_shoulder_length = math.sqrt((333 - 480) ** 2 + (208 - 276) ** 2)
    ideal_neck_head_length = 150

    # print("Ideal right shoulder length = ", ideal_right_shoulder_length)
    # print("Ideal left shoulder length = ", ideal_left_shoulder_length)
    # print("Ideal neck-head length =", ideal_neck_head_length)


    # metrics of good/bad posture #
    y_right_shoulder = points_coordinates[0][2] # get coordinates of right shoulder
    y_left_shoulder = points_coordinates[1][2] # get coordinates of left shoulder
    # print("Y of left shoulder: ", y_left_shoulder, "; Y of right shoulder: ", y_right_shoulder)

    x_right_shoulder = points_coordinates[0][1]
    x_left_shoulder = points_coordinates[1][1]
    # print("X of left shoulder: ", x_left_shoulder, "; X of right shoulder: ", x_right_shoulder)


    x_neck = points_coordinates[3][1]
    y_neck = points_coordinates[3][2]
    # print("X of neck: ", x_neck, "; Y of neck: ", y_neck)


    x_head = points_coordinates[2][1]
    y_head = points_coordinates[2][2]
    # print("X of head: ", x_head, "; Y of head: ", y_head)


    left_shoulder_length = math.sqrt((x_neck - x_left_shoulder) ** 2 + (y_neck - y_left_shoulder) ** 2)
    right_shoulder_length = math.sqrt((x_neck - x_right_shoulder) ** 2 + (y_neck - y_right_shoulder) ** 2)
    # print("Left shoulder length: ", left_shoulder_length, "; Right shoulder length: ", right_shoulder_length)


    neck_head_length = math.sqrt((x_head - x_neck) ** 2 + (y_head - y_neck) ** 2)
    # print("Neck-head length: ", neck_head_length)


    x_vector_head = x_head - x_neck
    y_vector_head = y_head - y_neck
    # print("X of head vector: ", x_vector_head, "; Y of head vector: ", y_vector_head)
    x_vector_ideal_head = 347 - 333
    y_vector_ideal_head = 10 - 208
    # print("X of ideal head vector: ", x_vector_ideal_head, "; Y of ideal head vector: ", y_vector_ideal_head)


    x_vector_left_shoulder = x_left_shoulder - x_neck
    y_vector_left_shoulder = y_left_shoulder - y_neck
    # print("X of left shoulder vector: ", x_vector_left_shoulder, "; Y of left shoulder vector: ", y_vector_left_shoulder)
    x_vector_right_shoulder = x_right_shoulder - x_neck
    y_vector_right_shoulder = y_right_shoulder - y_neck
    # print("X of right shoulder vector: ", x_vector_right_shoulder, "; Y of right shoulder vector: ", y_vector_right_shoulder)


    cos_left_shoulder_head = (x_vector_left_shoulder * x_vector_head + y_vector_left_shoulder * y_vector_head) / (left_shoulder_length * neck_head_length)
    cos_right_shoulder_head = (x_vector_right_shoulder * x_vector_head + y_vector_right_shoulder * y_vector_head) / (right_shoulder_length * neck_head_length)
    # print("COS left shoulder and head: ", cos_left_shoulder_head, "; COS right shoulder and head: ", cos_right_shoulder_head)


    angle_head_left_shoulder = math.degrees(math.acos(cos_left_shoulder_head))
    angle_head_right_shoulder = math.degrees(math.acos(cos_right_shoulder_head))
    # print("Angle between left shoulder and head:: ", angle_head_left_shoulder, "; Angle between right shoulder and head: ", angle_head_right_shoulder)


    # 1 - assymetric shoulders. How much one shoulder higher than another
    # 2 - what is the side angle of the neck
    # 3 - how much shoulders higher/lower than neck (this is directly related with straight spine)

    if ((abs(y_left_shoulder - y_right_shoulder) >= RIGHT_LEFT_SHOULDER_DIFF) or 
        (abs(angle_head_left_shoulder - angle_head_right_shoulder) >= ANGLE_HEAD_SHOULDER_DIFF) or 
        ((abs(y_left_shoulder - y_neck) <= SHOULDER_NECK_DIFF) or (abs(y_right_shoulder - y_neck) <= SHOULDER_NECK_DIFF))):
        print("Incorrect posture")


    if ((abs(y_left_shoulder - y_right_shoulder) < RIGHT_LEFT_SHOULDER_DIFF) and 
        (abs(angle_head_left_shoulder - angle_head_right_shoulder) < ANGLE_HEAD_SHOULDER_DIFF) and 
        ((abs(y_left_shoulder - y_neck) > SHOULDER_NECK_DIFF) or (abs(y_right_shoulder - y_neck) > SHOULDER_NECK_DIFF))):
        print("Correct posture")


    

    if ((y_left_shoulder - y_right_shoulder) >= RIGHT_LEFT_SHOULDER_DIFF):
        print("Your left shoulder higher than right shoulder. You should straighten your left shoulder as right shoulder")
    elif ((y_right_shoulder - y_left_shoulder) >= RIGHT_LEFT_SHOULDER_DIFF):
        print("Your right shoulder higher than left shoulder. You should straighten your right shoulder as left shoulder")
    elif(((y_left_shoulder - y_right_shoulder) >= RIGHT_LEFT_SHOULDER_DIFF) and ((y_right_shoulder - y_left_shoulder) >= RIGHT_LEFT_SHOULDER_DIFF)):
        print("Your shoulders higher than neck. You should straighten your shoulders")



    if (ideal_left_shoulder_length - left_shoulder_length >= IDEAL_LEFT_SHOULDER_DIFF):
        print("Your left shoulder close to the body. You should straighten your left shoulder")
    elif (ideal_right_shoulder_length - right_shoulder_length >= IDEAL_LEFT_SHOULDER_DIFF):
        print("Your right shoulder close to the body. You should straighten your right shoulder")
    elif ((ideal_left_shoulder_length - left_shoulder_length >= IDEAL_LEFT_SHOULDER_DIFF) and (ideal_right_shoulder_length - right_shoulder_length >= IDEAL_LEFT_SHOULDER_DIFF)):
        print("Both your shoulders close to the body. You should straighten your shoulders")


    if (abs(angle_head_left_shoulder - angle_head_right_shoulder) >= ANGLE_HEAD_SHOULDER_DIFF):
        print("Your head is tilted to the side. You should straighten your head")

    if ((ideal_neck_head_length - neck_head_length) > FRONT_HEAD_TILT):
        print("Your head is titled forward or backward. You should straighten your head")

    # end #
        
    # plot the pose on original image
    canvas = image_original
    for idx, limb in enumerate(JOINT_LIMB):
        joint_from, joint_to = joint_list[limb[0]], joint_list[limb[1]]
        canvas = cv2.line(canvas, tuple(joint_from.astype(int)),
                          tuple(joint_to.astype(int)), color=COLOR[idx], thickness=4)
    return canvas

def peak_index_to_coords(heatmap):
    """
    @peak_index is the index of max value in flatten heatmap
    This function convert it back to the coordinates of the original heatmap
    """
    flat_index = int(np.argmax(heatmap))
    peak_coords = np.unravel_index(flat_index, (heatmap_height, heatmap_width))
    return np.array(peak_coords, dtype=np.float32)

