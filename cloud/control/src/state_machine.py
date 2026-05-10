import enum
import time

import numpy as np
import zmq
from ultralytics import YOLO

import config
import utils
from keresd import KeresdLogic  # Import KeresdLogic from keresd.py
from kovesd import KovesdLogic  # Import KovesdLogic from kovesd.py
from log_setup import get_logger

logger = get_logger()


class State(enum.Enum):
    DETECT = "detect"
    FOLLOW = "follow"


BALL_CLASS = 32
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

class StateMachineController:
    def __init__(self):
        logger.info("[FSM] Loading YOLO model...")
        self.model = YOLO("yolov8m-seg.pt")
        config.init()

        logger.info("[FSM] Connecting ZMQ...")
        self.zmqcontext = zmq.Context()
        self.subscriber = self.zmqcontext.socket(zmq.SUB)
        self.subscriber.setsockopt(zmq.CONFLATE, 1)
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
        self.subscriber.connect("ipc:///tmp/video_frames_c.ipc")
        self.subscriber.setsockopt(zmq.RCVTIMEO, 1000)

        # Single FSM output for web_fsm
        self.publisher_fsm = self.zmqcontext.socket(zmq.PUB)
        self.publisher_fsm.bind("ipc:///tmp/video_frames_fsm.ipc")

        self.state = State.FOLLOW
        self.last_ball_seen_at = time.monotonic()
        self.state_changed = False

        self.keresd_logic = KeresdLogic()
        self.kovesd_logic = KovesdLogic()

    def set_state(self, new_state: State):
        if new_state == self.state:
            return

        logger.info(f"[FSM] STATE CHANGE: {self.state.value} -> {new_state.value}")
        self.state_changed = True
        logger.info(f"[FSM] sending stop() due to state change")
        utils.dogy_control("stop")
        logger.info(f"[FSM] resetting both logics")
        self.keresd_logic.reset()
        self.kovesd_logic.reset()
        self.state = new_state

    def process_frame(self, frame_bytes):
        img_array = np.frombuffer(frame_bytes, dtype=np.uint8)
        img_array = img_array.reshape((FRAME_HEIGHT, FRAME_WIDTH, 3))

        results = self.model.track(
            img_array,
            imgsz=[FRAME_HEIGHT, FRAME_WIDTH],
            conf=0.10,
            classes=[BALL_CLASS],
            verbose=False,
            persist=True,
        )

        annotated_frame = results[0].plot()
        annotated_frame_bytes = annotated_frame.tobytes()

        # Send annotated frame to FSM topic
        self.publisher_fsm.send(annotated_frame_bytes)
        
        # Write FSM state to file for web UI
        try:
            with open("/tmp/fsm_state", "w") as f:
                f.write(self.state.value)
        except Exception as e:
            logger.info(f"[FSM] Error writing FSM state: {e}")

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return None

        cls = boxes.cls.cpu().numpy().astype(int)
        xywhn = boxes.xywhn.cpu().numpy()
        confs = boxes.conf.cpu().numpy()

        best_ball = None
        best_ball_conf = -1.0

        for i in range(len(cls)):
            if int(cls[i]) != BALL_CLASS:
                continue

            if confs[i] > best_ball_conf:
                best_ball_conf = float(confs[i])
                x, y, _, _ = xywhn[i]
                best_ball = (round(float(x), 2), round(float(y), 2))

        return best_ball

    def tick(self):
        try:
            try:
                frame_bytes = self.subscriber.recv()
            except zmq.Again:
                logger.info("[FSM] waiting for camera frames...")
                return  # No frame available, skip this tick

            ball = self.process_frame(frame_bytes)

            now = time.monotonic()
            if ball is not None:
                self.last_ball_seen_at = now
                if self.state != State.FOLLOW:
                    logger.info(f"[FSM] switching to FOLLOW")
                    self.set_state(State.FOLLOW)
            elif now - self.last_ball_seen_at >= 5.0 and self.state != State.DETECT:
                logger.info(f"[FSM] ball lost for 5s, switching to DETECT")
                self.set_state(State.DETECT)

            # Skip step execution on frame immediately after state change to allow stop() to take effect
            if not self.state_changed:
                if self.state == State.DETECT:
                    self.keresd_logic.step(ball)
                elif self.state == State.FOLLOW:
                    self.kovesd_logic.step(ball)
            else:
                self.state_changed = False
        except Exception as e:
            logger.info(f"[FSM] tick exception: {e}")
            return

    def close(self):
        utils.dogy_control("stop")
        self.subscriber.close()
        self.publisher_fsm.close()
        self.zmqcontext.term()


def main():
    ctrl = StateMachineController()
    logger.info("[FSM] Online. Processing frames centrally...")
    try:
        while True:
            ctrl.tick()
    except KeyboardInterrupt:
        logger.info("[FSM] Stopping FSM")
    finally:
        ctrl.close()


if __name__ == "__main__":
    main()
