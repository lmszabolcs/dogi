import cv2
import numpy as np
import zmq
import time
from ultralytics import YOLO
#from DOGZILLALib.DOGZILLALib import DOGZILLALib as dog
import socket
import pickle

import config
import utils
from log_setup import get_logger

logger = get_logger()

# These are initialized only when running this module directly.
model = None
zmqcontext = None
subscriber = None
publisher = None

MAXPITCH = 20
MAXYAW = 16
TURNBASE = 7
X_DEADZONE = 0.05
Y_DEADZONE = 0.05

# Function to process the frame
def process_frame(frame_bytes):
    global att, att_changed
    
    width = 640
    height = 480
    img_array = np.frombuffer(frame_bytes, dtype=np.uint8)
    img_array = img_array.reshape((height, width, 3))

    #img_array = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
    #cv2.imshow("Dogi video", img_array)

    results = model.track(img_array, imgsz=[height, width], conf=0.25, classes=[32], verbose=False, persist=True)
    annotated_frame = results[0].plot()
    
    publisher.send(annotated_frame.tobytes())

    annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
    cv2.imshow("YOLO Dogi video", annotated_frame)
    #logger.info(result[0].boxes.xywhn)

    if len(results[0].boxes.xywhn) > 0:
        #logger.info(results[0].boxes.xywhn[0])
        #logger.info(results[0].boxes.cls)
        (x, y, w, h) = results[0].boxes.xywhn[0].cpu().numpy()
        x = round(x,2)
        y = round(y,2)
        return (x, y)
    else:
        return None
    

class KovesdLogic:
    def __init__(self):
        self.att_yaw = 0
        self.o_att_yaw = 0
        self.att_pitch = 0
        self.o_att_pitch = 0
        self.skip = 0
        self.turn = 0
        self.o_turn = 0
        

    @staticmethod
    def in_center_deadzone(x, y):
        return abs(x - 0.5) <= X_DEADZONE and abs(y - 0.5) <= Y_DEADZONE

    def reset(self):
        logger.info(f"[KOVESD] reset() called")
        self.att_yaw = 0
        self.o_att_yaw = 0
        self.att_pitch = 0
        self.o_att_pitch = 0
        self.skip = 0
        self.turn = 0
        self.o_turn = 0
        

    def step(self, ball):
        if self.skip > 0:
            self.skip -= 1
            return

        if ball:
            (x, y) = ball
            ##logger.info(f"[KOVESD] ball at x={x:.2f}, y={y:.2f}, att_yaw={self.att_yaw}, att_pitch={self.att_pitch}, turn={self.turn}")
            if self.turn > 0:
                if x < 0.5 + X_DEADZONE:
                    self.turn = TURNBASE    # Continue turn left
                else:
                    self.turn = 0
                    self.skip = 3    # Stop turning and pause
            elif self.turn < 0:
                if x > 0.5 - X_DEADZONE:
                    self.turn = -TURNBASE   # Continue turn right
                else:
                    self.turn = 0
                    self.skip = 3    # Stop turning and pause
            else:   # No turn in progress
                if x < 0.5 - X_DEADZONE:
                    if self.att_yaw == MAXYAW:
                        self.att_yaw = 0
                        self.turn = TURNBASE    # Start turning left
                        self.skip = 10
                    else:
                        self.att_yaw += 1    # Lean left
                elif x > 0.5 + X_DEADZONE:
                    if self.att_yaw == -MAXYAW:
                        self.att_yaw = 0
                        self.turn = -TURNBASE   # Start turning right
                        self.skip = 10
                    else:
                        self.att_yaw -= 1    # Lean right

                if y < 0.5 - Y_DEADZONE and self.att_pitch > -MAXPITCH:
                    self.att_pitch -= 1
                if y > 0.5 + Y_DEADZONE and self.att_pitch < MAXPITCH:
                    self.att_pitch += 1

        if self.turn != self.o_turn:
            self.o_turn = self.turn
            logger.info(f"[KOVESD] TURN {self.turn}")
            if self.turn > 0:
                utils.dogy_control('turn', (10, ))
            elif self.turn < 0:
                utils.dogy_control('turn', (-10, ))
            else:
                utils.dogy_control('stop')
                self.att_yaw = 0 # Reset the attitude yaw

        elif self.att_yaw != self.o_att_yaw or self.att_pitch != self.o_att_pitch:
            self.o_att_yaw = self.att_yaw
            self.o_att_pitch = self.att_pitch
            logger.info(f"[KOVESD] setting attitude yaw={self.att_yaw}, pitch={self.att_pitch}")
            utils.dogy_control('attitude', (["y", "p", "r"], [self.att_yaw, self.att_pitch, 0]))

        if self.turn > 0:
            self.turn -= 1
        elif self.turn < 0:
            self.turn += 1

if __name__ == '__main__':
    model = YOLO('yolov8m-seg.pt')
    config.init()

    zmqcontext = zmq.Context()
    subscriber = zmqcontext.socket(zmq.SUB)
    subscriber.setsockopt(zmq.CONFLATE, 1)
    subscriber.setsockopt_string(zmq.SUBSCRIBE, '')
    subscriber.connect("ipc:///tmp/video_frames_c.ipc")

    publisher = zmqcontext.socket(zmq.PUB)
    publisher.bind("ipc:///tmp/video_frames_kovesd.ipc")

    kovesd_logic = KovesdLogic()
    try:
        while True:

            try:
                frame_bytes = subscriber.recv()
                ball = process_frame(frame_bytes)
                
                kovesd_logic.step(ball)

            except zmq.error.Again:
                pass  # No frame received, continue processing

            # Display the result on the screen
            #if cv2.waitKey(1) == ord('q'):
            #    break
    finally:
        # Release the video capture and close the window
        subscriber.close()
        publisher.close()
        zmqcontext.term()
        cv2.destroyAllWindows()
