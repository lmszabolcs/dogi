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
from log_setup import get_logger

logger = get_logger()

PORT = 5053

MAXPITCH = 20
MAXYAW = 16

DEBUG_mode = os.getenv('DEBUG', '0') == '1'

# These are initialized only when running this module directly.
sock_web = None
zmqcontext = None
subscriber = None
publisher = None

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

class KeresdLogic:
    def __init__(self):
        self._action_thread = None
        self._stop_event = threading.Event()

    def reset(self):
        logger.info(f"[KERESD] reset() called")
        self._stop_event.set()
        if self._action_thread is not None and self._action_thread.is_alive():
            logger.info(f"[KERESD] waiting for thread to finish...")
            self._action_thread.join(timeout=0.5)
        self._action_thread = None
        self._stop_event.clear()

    def _wait_or_stop(self, seconds, step=0.05):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self._stop_event.wait(step):
                utils.dogy_control('stop')
                return True
        return False

    def _search_move_once(self):
        logger.info(f"[KERESD.SEARCH] starting search move sequence")
        self.look_left_right(None)
        if random.choice([True, False]):
            logger.info(f"[KERESD.SEARCH] chose turn_left")
            self.turn_left()
        else:
            logger.info(f"[KERESD.SEARCH] chose turn_right")
            self.turn_right()
        logger.info(f"[KERESD.SEARCH] search move complete")

    def step(self, ball):
        """FSM mode: keep the same motion order as the standalone version."""
        if ball is not None:
            logger.info(f"[KERESD] ball detected at {ball}, stopping search")
            self._stop_event.set()
            utils.dogy_control('stop')
            self._action_thread = None
            return

        # If action thread is already running, don't start another one
        if self._action_thread is not None and self._action_thread.is_alive():
            return

        # Run full search motion in a separate thread so tick() is not blocked
        logger.info(f"[KERESD] no ball, starting search")
        self._stop_event.clear()
        self._action_thread = threading.Thread(target=self._search_move_once, daemon=False)
        self._action_thread.start()

    def move_forward(self):
        logger.info(f"[KERESD.MOVE] move_forward: looking straight")
        utils.dogy_look(0, 0, 0) # Look straight
        if self._wait_or_stop(1):
            return
        logger.info(f"[KERESD.MOVE] move_forward: moving forward")
        utils.dogy_control('forward', (3,))
        if self._wait_or_stop(3):
            return
        logger.info(f"[KERESD.MOVE] move_forward: stopping")
        utils.dogy_control('stop')

    def turn_left(self):
        logger.info(f"[KERESD.MOVE] turn_left: looking straight")
        utils.dogy_look(0, 0, 0) # Look straight
        logger.info(f"[KERESD.MOVE] turn_left: turning left")
        utils.dogy_control('turn', (5,))
        if self._wait_or_stop(1):
            return
        logger.info(f"[KERESD.MOVE] turn_left: stopping")
        if self._wait_or_stop(3):
            return
        utils.dogy_control('stop')

    def turn_right(self):
        logger.info(f"[KERESD.MOVE] turn_right: looking straight")
        utils.dogy_look(0, 0, 0) # Look straight
        logger.info(f"[KERESD.MOVE] turn_right: turning right")
        utils.dogy_control('turn', (-5,))
        if self._wait_or_stop(1):
            return
        logger.info(f"[KERESD.MOVE] turn_right: stopping")
        if self._wait_or_stop(3):
            return
        utils.dogy_control('stop')

    def look_left_right(self, model):
        global ball

        # FSM mode: central YOLO is in state_machine, so this function runs motion-only.
        if model is None or subscriber is None or publisher is None:
            logger.info(f"[KERESD.LOOK] starting look left-right loop")
            for yaw in [-MAXYAW, 0, MAXYAW]:
                if self._stop_event.is_set():
                    utils.dogy_control('stop')
                    return
                logger.info(f"[KERESD.LOOK] looking at yaw={yaw}")
                utils.dogy_look(0, 0, yaw)
                if self._wait_or_stop(1.5):
                    return
            logger.info(f"[KERESD.LOOK] look front")
            utils.dogy_look(0, 0, 0)
            return

        logger.info(f"[KERESD.LOOK] starting look left-right with model tracking")
        for yaw in [-MAXYAW, 0, MAXYAW]:
            logger.info(f"[KERESD.LOOK] looking at yaw={yaw}")
            utils.dogy_look(0, 0, yaw) # Look
            start = time.time()
            while time.time() - start < 1.5:
                take_and_process_frame(model)
                if ball:
                    logger.info(f"[KERESD.LOOK] ball found during look!")
                    break
            if ball:
                break

        logger.info(f"[KERESD.LOOK] look front")
        utils.dogy_look(0, 0, 0) # Look front

    def loop_body(self, model):
        global ball, front_pic

        front_pic = None
        ball = None

        try:
            if DEBUG_mode:
                jpg_files = glob.glob("/root/debug/*.jpeg")
                if jpg_files:
                    random_file = random.choice(jpg_files)
                    front_pic = cv2.imread(random_file)
                    logger.info(f"Loaded random picture: {random_file}")
                    if front_pic is not None:
                        # Publish the raw bytes of the picture
                        publisher.send(front_pic.tobytes())
                
                # Example coordinates for the ball
                ball = (0.5, 0.5)
            else:
                take_and_process_frame(model)

            if not ball:
                thread = threading.Thread(target=self.look_left_right, args=(model,))
                thread.start()
                thread.join()

            if ball:
                # Wait 20 seconds before continuing the process (but update the image)
                start = time.time()
                while time.time() - start < 20:
                    take_and_process_frame(model)
                return
            
        except Exception as e:
            logger.info(f"[KERESD] Error: {e}")
            return
        
        # Check if 'q' is pressed and if so, break the loop
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return

        if random.choice([True, False]):
            self.turn_left()
        else:
            self.turn_right()


if __name__ == "__main__":
    model = YOLO('yolov8m-seg.pt')
    config.init()

    sock_web = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_web.connect(('localhost', PORT))

    zmqcontext = zmq.Context()
    subscriber = zmqcontext.socket(zmq.SUB)
    subscriber.setsockopt(zmq.CONFLATE, 1)
    subscriber.setsockopt_string(zmq.SUBSCRIBE, '')
    subscriber.connect("ipc:///tmp/video_frames_c.ipc")

    publisher = zmqcontext.socket(zmq.PUB)
    publisher.bind("ipc:///tmp/video_frames_keresd.ipc")

    keresd_logic = KeresdLogic()

    try:
        while True:
            keresd_logic.loop_body(model)
    finally:
        subscriber.close()
        publisher.close()
        zmqcontext.term()
        cv2.destroyAllWindows()
