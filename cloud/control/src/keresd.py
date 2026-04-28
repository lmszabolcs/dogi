import cv2
import numpy as np
import zmq
import time
import socket
import pickle
import threading
import random
from io import BytesIO
import os
import glob
from ultralytics import YOLO

import utils
import config

PORT = 5053

MAXPITCH = 20
MAXYAW = 16

DEBUG_mode = os.getenv('DEBUG', '0') == '1'

# Create a UDP sockets to web page server
sock_web = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_web.connect(('localhost', PORT))

# Subscribe to video
zmqcontext = zmq.Context()
subscriber = zmqcontext.socket(zmq.SUB)
subscriber.setsockopt(zmq.CONFLATE, 1)
subscriber.setsockopt_string(zmq.SUBSCRIBE, '')  # Subscribe to all topics
subscriber.connect("ipc:///tmp/video_frames_c.ipc")  # IPC socket address

publisher = zmqcontext.socket(zmq.PUB)
publisher.bind("ipc:///tmp/video_frames_keresd.ipc")

# Prompts will be eliminated later, for now they are disabled
#text = {
#    'en': "Let's play a ball finding game! Ready or not, here I come! I'm starting to look!",
#    'hu': "Játsszunk labdakereső játékot! Aki bújt, aki nem, indulok. Figyelj, keresni kezdek."
#}
#xtext = utils.select_text(text, config.get_ui_language(), True)
#print(xtext)
#wav, d = utils.tts_wav(xtext, config.get_ui_language() + "_intro_keresd")
#utils.play_wav(wav)
#time.sleep(d)

front_pic = None
ball = None
ball_lock = threading.Lock()

# Function to process the frame
def take_and_process_frame(model):
    global ball, front_pic

    width = 640
    height = 480

    frame_bytes = subscriber.recv()

    if frame_bytes is None:
        return None
    
    img_array = np.frombuffer(frame_bytes, dtype=np.uint8)
    img_array = img_array.reshape((height, width, 3))

    results = model.track(img_array, imgsz=[height, width], conf=0.25, classes=[32], verbose=False, persist=True)
    annotated_frame = results[0].plot()
    publisher.send(annotated_frame.tobytes())

    front_pic = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
    #cv2.imshow("Front", front_pic)
    cv2.waitKey(1)

    with ball_lock:
        if len(results[0].boxes.xywhn) > 0:
            (x, y, w, h) = results[0].boxes.xywhn[0].cpu().numpy()
            x = round(x,2)
            y = round(y,2)
            ball = (x, y)
        else:
            ball = None

def move_forward():
    utils.dogy_look(0, 0, 0) # Look straight
    time.sleep(1)
    utils.dogy_control('forward', (5, ))
    time.sleep(3)
    utils.dogy_control('stop')

def turn_left():
    utils.dogy_look(0, 0, 0) # Look straight
    time.sleep(1)
    utils.dogy_control('turn', (5, ))
    time.sleep(3)
    utils.dogy_control('stop')

def turn_right():
    utils.dogy_look(0, 0, 0) # Look straight
    time.sleep(1)
    utils.dogy_control('turn', (-5, ))
    time.sleep(3)
    utils.dogy_control('stop')

def look_left_right(model):
    global ball

    for yaw in [-MAXYAW, 0, MAXYAW]:
        utils.dogy_look(0, 0, yaw) # Look
        start = time.time()
        while time.time() - start < 1.5:
            take_and_process_frame(model)
            if ball:
                break
        if ball:
            break

    utils.dogy_look(0, 0, 0) # Look front

def loop_body(model):
    global ball, front_pic

    front_pic = None
    ball = None

    try:
        if DEBUG_mode:
            jpg_files = glob.glob("/root/debug/*.jpeg")
            if jpg_files:
                random_file = random.choice(jpg_files)
                front_pic = cv2.imread(random_file)
                print(f"Loaded random picture: {random_file}")
                if front_pic is not None:
                    # Publish the raw bytes of the picture
                    publisher.send(front_pic.tobytes())
                
                # Example coordinates for the ball
                ball = (0.5, 0.5)
            else:
                print("No jpeg files found in the folder.")
        else:
            take_and_process_frame(model)

        if not ball:
            thread = threading.Thread(target=look_left_right, args=(model,))
            thread.start()
            thread.join()

        if ball:
            # Wait 20 seconds before continuing the process (but update the image)
            start = time.time()
            while time.time() - start < 20:
                take_and_process_frame(model)
            return
        
    except Exception as e:
        print('Error:', e)
        return
    
    # Check if 'q' is pressed and if so, break the loop
    if cv2.waitKey(1) & 0xFF == ord('q'):
        return

    if random.choice([True, False]):
        turn_left()
    else:
        turn_right()


if __name__ == "__main__":
    model = YOLO('yolov8m-seg.pt')
    config.init()

    while True:
        loop_body(model)

# Release the video capture and close the window
subscriber.close()
publisher.close()
zmqcontext.term()
cv2.destroyAllWindows()
