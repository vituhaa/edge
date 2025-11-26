import cv2

cap = cv2.VideoCapture(0)

ret, frame = cap.read()

if ret:
    cv2.imwrite('/home/HwHiAiUser/my_project/body_pose_picture/data/photo.jpg', frame)
    print("Saved")
else:
    print("Couldnt save")


cap.release()

