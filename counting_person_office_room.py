# Write in BGR space
import numpy as np
import cv2
import Person
import time
import argparse
import imutils
from imutils.video import FileVideoStream
from imutils.video import FPS

INST_WIDTH = 800
INST_HEIGHT = 600
# http://docs.opencv.org/master/d3/dc0/group__imgproc__shape.html#ga17ed9f5d79ae97bd4c7cf18403e1689a&gsc.tab=0
# http://docs.opencv.org/master/d4/d73/tutorial_py_contours_begin.html#gsc.tab=0

### Input and Output Counters
cnt_up = 0
cnt_down = 0

# construct the argument parse and parse the arguments
#ap = argparse.ArgumentParser()
#ap.add_argument("-v", "--video", required=True,
#    help="path to input video file")
#args = vars(ap.parse_args())

### Open video file
#cap = cv2.VideoCapture('src/cctv01.avi')
cap = cv2.VideoCapture('../src/mycctv01.avi')
#cap = cv2.resize(cap, (400, 300))

w = INST_WIDTH
h = INST_HEIGHT
frameArea = h*w
areaTH = frameArea/250
print('Area Threshold', areaTH)

### Line of up/down
line_up = int(2*(h/10))
line_down = int(3*(h/10))

#line_mid = (line_up + line_down) / 2

up_limit = int(1*(h/10))
down_limit = int(4*(h/10))

print("Blue line y:", str(line_down))
print("Red line y:", str(line_up))
line_down_color = (255,0,0)
line_up_color = (0,0,255)
# Point = [x, y]
# line_down
pt1 = [0, line_down]
pt2 = [w, line_down]
pts_L1 = np.array([pt1,pt2], np.int32)
pts_L1 = pts_L1.reshape((-1,1,2))
# line_up
pt3 = [0, line_up];
pt4 = [w, line_up];
pts_L2 = np.array([pt3, pt4], np.int32)
pts_L2 = pts_L2.reshape((-1,1,2))

pt5 = [0, up_limit]
pt6 = [w, up_limit]
pts_L3 = np.array([pt5, pt6], np.int32)
pts_L3 = pts_L3.reshape((-1,1,2))
pt7 = [0, down_limit]
pt8 = [w, down_limit]
pts_L4 = np.array([pt7, pt8], np.int32)
pts_L4 = pts_L4.reshape((-1,1,2))

#kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
### Create the background substractor
fgbg = cv2.createBackgroundSubtractorMOG2(detectShadows = True)

### Create kernel for doing Opening and Closing operation
kernelOp = np.ones((5,5), np.uint8)
#kernelOp2 = np.ones((5,5), np.uint8)
kernelCl = np.ones((5,5), np.uint8)

### Define the minimum contours to detect the person and other Variables
font = cv2.FONT_HERSHEY_SIMPLEX
persons = []
max_p_age = 5
pid = 1
#areaTH = 500

if cap.isOpened():
    ret, image = cap.read()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (INST_WIDTH, INST_HEIGHT))
    # Assign new height and width for ROI
    (xr, yr, wr, hr) = cv2.boundingRect(gray)
    startYROI = 2*hr/10
    endYROI = hr-5*hr/20
else:
    print("Camera is not open")

while(cap.isOpened()):
    ### Read a frame
    ret, frame = cap.read()
    frame = cv2.resize(frame, (INST_WIDTH, INST_HEIGHT))
    cv2.rectangle(frame, (150, startYROI), (wr-300, endYROI), (0, 255, 0), 2)
    roi_image = frame[startYROI:endYROI, 150:wr-300]
    #frame = cv2.GaussianBlur(frame,(3,3),0)

    for i in persons:
        i.age_one()     # age every person one frame

    #####################
    #   PRE_PROCESSING  #
    #####################

    ### Use the substractor
    fgmask = fgbg.apply(roi_image)
    blur = cv2.medianBlur(fgmask, 5)
    blur = cv2.GaussianBlur(blur,(3,3),0)
    #fgmask2 = fgbg.apply(frame)
    #fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)

    try:
        ret, imBin = cv2.threshold(fgmask,210,255,cv2.THRESH_BINARY)
        #ret, imBin2 = cv2.threshold(fgmask2,200,255,cv2.THRESH_BINARY)
        ### Opening (erode->dilate) Removing noise
        mask = cv2.morphologyEx(imBin, cv2.MORPH_OPEN, kernelOp)
        #mask2 = cv2.morphologyEx(imBin2, cv2.MORPH_OPEN, kernelOp2)
        ### Closing (dilate->erode) Joining the white regions
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernelCl)
        #mask2 = cv2.morphologyEx(mask2, cv2.MORPH_CLOSE, kernelCl)
        #cv2.imshow('Frame', frame)
        #cv2.imshow('Background Subtraction', fgmask)
        cv2.imshow('Morphology Extraction', mask)
    except:
        #if there are no more frames to show
        print('EOF')
        print('UP:', cnt_up)
        print('DOWN:', cnt_down)
        break

    ### Find Contour ###
    #_, contours0, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    _, contours0, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours0:
        #cv2.drawContours(frame, cnt, -1, (0,255,0), 3, 8)
        area = cv2.contourArea(cnt)
        print(area)
        if area > 9000 and area < 30000:
            #############
            #  TRACKING #
            #############
            M = cv2.moments(cnt)
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])
            x,y,w,h = cv2.boundingRect(cnt)

            new = True
            if cy in range(up_limit, down_limit):
                for i in persons:
                    ## Verify person which is the same as person who already detected before
                    if abs(x-i.getX()) <= w and abs(y-i.getY()) <= h:
                        new = False
                        i.updateCoords(cx, cy)  ##Update coordinate of person and reset age
                        if i.going_UP(line_down, line_up) == True:
                            cnt_up += 1;
                            print("ID:", i.getId(), 'crossed going up at', time.strftime("%c"))
                        elif i.going_DOWN(line_down, line_up) == True:
                            cnt_down += 1;
                            print("ID:", i.getId(), 'crossed going down at', time.strftime("%c"))
                        break

                    if i.getState() == '1':
                        if i.getDir() == 'down' and i.getY() > down_limit:
                            i.setDone()
                        elif i.getDir() == 'up' and i.getY() < up_limit:
                            i.setDone()

                    if i.timedOut():
                        ### remove from the person list
                        index = persons.index(i)
                        persons.pop(index)
                        del i   # free memory

                if new == True:
                    p = Person.MyPerson(pid, cx, cy, max_p_age)
                    persons.append(p)
                    pid += 1
            ################
            #   DRAWING    #
            ################
            cv2.circle(roi_image, (cx, cy), 5, (0,0,255), -1)
            img = cv2.rectangle(roi_image, (x, y), (x+w, y+h), (0,255,0), 2)
            #cv2.drawContours(frame, cnt, -1, (0,255,0), 3)

        #############################
        #   DRAWING TRAJECTORIES    #
        #############################
        for i in persons:
            #if len(i.getTracks()) >= 2:
            #    pts = np.array(i.getTracks(), np.int32)
            #    pts = pts.reshape((-1,1,2))
            #    frame = cv2.polylqines(frame, [pts], False, i.getRGB())
            #if i.getId() == 9:
            #    print str(i.getX()), ',', str(i.getY())
            cv2.putText(roi_image, str(i.getId()), (i.getX(), i.getY()), font, 0.3, i.getRGB(), 1, cv2.LINE_AA)

        #############
        #   IMAGES  #
        #############
        str_up = 'UP: ' + str(cnt_up)
        str_down = 'DOWN: ' + str(cnt_down)
        cv2.polylines(roi_image, [pts_L1], False, line_down_color, thickness=2)
        cv2.polylines(roi_image, [pts_L2], False, line_up_color, thickness=2)
        # line limit
        cv2.polylines(roi_image, [pts_L3], False, (255,255,255), thickness=1)
        cv2.polylines(roi_image, [pts_L4], False, (255,255,255), thickness=1)
        cv2.putText(roi_image, str_up, (10,40), font, 0.5, (255,255,255), 2, cv2.LINE_AA)
        cv2.putText(roi_image, str_up, (10,40), font, 0.5, (0,0,255), 1, cv2.LINE_AA)
        cv2.putText(roi_image, str_down, (10,90), font, 0.5, (255,255,255), 2, cv2.LINE_AA)
        cv2.putText(roi_image, str_down, (10, 90), font, 0.5, (255,0,0), 1, cv2.LINE_AA)
        #cv2.imshow('Frame', frame)

        cv2.imshow("Region of Interest", roi_image)

    ### Abort and exit with 'q' or ESC ###
    if cv2.waitKey(1) & 0xff == ord('q'):
        break

### Release video file
cap.release()
cv2.destroyAllWindows() ### Close all opencv windows
