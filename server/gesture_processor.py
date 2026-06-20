import time
import logging

logger = logging.getLogger("touchmorph.gesture")

SWIPE_THRESHOLD = 30
TAP_TIMEOUT = 0.3
DOUBLE_TAP_TIMEOUT = 0.4
LONG_PRESS_TIMEOUT = 0.8


class GestureProcessor:
    def __init__(self):
        self.history = {}
        self.last_tap_time = 0
        self.last_tap_pos = None

    def start(self, touch_id, x, y):
        self.history[touch_id] = [(x, y, time.time())]

    def move(self, touch_id, x, y):
        if touch_id not in self.history:
            self.history[touch_id] = []
        self.history[touch_id].append((x, y, time.time()))
        if len(self.history[touch_id]) > 10:
            self.history[touch_id].pop(0)

    def end(self, touch_id):
        return self.history.pop(touch_id, None)

    def detect_swipe(self, touch_id):
        points = self.history.get(touch_id, [])
        if len(points) < 3:
            return None

        first = points[0]
        last = points[-1]
        dx = last[0] - first[0]
        dy = last[1] - first[1]
        dist = (dx * dx + dy * dy) ** 0.5

        if dist < SWIPE_THRESHOLD:
            return None

        velocity = dist / (last[2] - first[2]) if (last[2] - first[2]) > 0 else 0
        if velocity < 0.3:
            return None

        angle = __import__("math").atan2(dy, dx)
        if abs(angle) < __import__("math").pi / 4:
            return "swipe_right"
        elif abs(angle) > 3 * __import__("math").pi / 4:
            return "swipe_left"
        elif angle > 0:
            return "swipe_down"
        else:
            return "swipe_up"

    def detect_tap(self, x, y):
        now = time.time()
        since_last = now - self.last_tap_time

        if (
            self.last_tap_pos
            and since_last < DOUBLE_TAP_TIMEOUT
            and abs(x - self.last_tap_pos[0]) < SWIPE_THRESHOLD
            and abs(y - self.last_tap_pos[1]) < SWIPE_THRESHOLD
        ):
            self.last_tap_time = 0
            self.last_tap_pos = None
            return "double_tap"

        self.last_tap_time = now
        self.last_tap_pos = (x, y)
        return "tap"

    def reset(self):
        self.history.clear()
        self.last_tap_time = 0
        self.last_tap_pos = None
