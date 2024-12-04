import numpy as np
import cv2 as cv
import glob
import os

# termination criteria
criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)
# prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
objp = np.zeros((6 * 8, 3), np.float32)
objp[:, :2] = np.mgrid[0:8, 0:6].T.reshape(-1, 2)
# Arrays to store object points and image points from all the images.
objpoints = []  # 3d point in real world space
imgpoints = []  # 2d points in image plane.
images = glob.glob('/home/rokey/Desktop/test_images/Fisheye1*.jpg')

for fname in images:
    img = cv.imread(fname)
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    # Find the chess board corners
    ret, corners = cv.findChessboardCorners(gray, (8, 6), None)
    # If found, add object points, image points (after refining them)
    if ret == True:
        objpoints.append(objp)
        corners2 = cv.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        imgpoints.append(corners2)
        # Draw and display the corners
        cv.drawChessboardCorners(img, (8, 6), corners2, ret)
        # cv.imshow('img', img)
        # cv.waitKey(500)
# Perform camera calibration

ret, mtx, dist, rvecs, tvecs = cv.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)
# Print the calibration results
print("Camera matrix :\n", mtx)
print("Distortion coefficients :\n", dist)

for fname in images:
    img = cv.imread(fname)
    h, w = img.shape[:2]
    new_camera_mtx, roi = cv.getOptimalNewCameraMatrix(mtx, dist, (w, h), 1, (w, h))
    # Undistort the image
    dst = cv.undistort(img, mtx, dist, None, new_camera_mtx)
    # Crop the image if needed
    x, y, w, h = roi
    dst = dst[y:y + h, x:x + w]
    # Save the undistorted image
    undistorted_fname = os.path.join('/home/rokey/B4_Fulfillment_ws/src/b4_fulfillment/resource', 'cal_' + os.path.basename(fname))
    cv.imwrite(undistorted_fname, dst)

cv.destroyAllWindows()

