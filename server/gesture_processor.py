import time
import math
import logging

logger = logging.getLogger("touchmorph.gesture")

SWIPE_THRESHOLD = 30
TAP_TIMEOUT = 0.3
DOUBLE_TAP_TIMEOUT = 0.4
LONG_PRESS_TIME = 0.6
PINCH_RATIO_THRESHOLD = 1.3
SHAKE_THRESHOLD = 15
SHAKE_WINDOW = 0.5
VELOCITY_SMOOTHING = 0.85


class SmartScrollEngine:
    def __init__(self):
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.active = False
        self.last_time = 0.0
        self.invert = True
        self.sensitivity = 1.0
        self.momentum_decay = 0.92

    def start(self):
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.active = True
        self.last_time = time.time()

    def update(self, dx, dy):
        now = time.time()
        dt = now - self.last_time if self.last_time else 0.016
        self.last_time = now
        if dt < 0.001:
            dt = 0.016
        factor = self.sensitivity * (1.0 if not self.invert else -1.0)
        self.velocity_x = self.velocity_x * VELOCITY_SMOOTHING + (dx / dt) * factor * (1 - VELOCITY_SMOOTHING)
        self.velocity_y = self.velocity_y * VELOCITY_SMOOTHING + (dy / dt) * factor * (1 - VELOCITY_SMOOTHING)

    def get_momentum(self):
        if not self.active:
            return (0, 0, False)
        self.velocity_x *= self.momentum_decay
        self.velocity_y *= self.momentum_decay
        vx, vy = self.velocity_x, self.velocity_y
        speed = (vx * vx + vy * vy) ** 0.5
        if speed < 1.0:
            self.velocity_x = 0.0
            self.velocity_y = 0.0
            return (0, 0, False)
        step_x = vx * 0.016
        step_y = vy * 0.016
        step_clamped_x = max(-50, min(50, step_x))
        step_clamped_y = max(-50, min(50, step_y))
        return (step_clamped_x, step_clamped_y, True)

    def stop(self):
        self.active = False
        self.velocity_x = 0.0
        self.velocity_y = 0.0

    def set_config(self, invert=None, sensitivity=None, decay=None):
        if invert is not None:
            self.invert = invert
        if sensitivity is not None:
            self.sensitivity = sensitivity
        if decay is not None:
            self.momentum_decay = decay


class GestureProcessor:
    def __init__(self):
        self.touches = {}
        self.last_tap_time = 0
        self.last_tap_pos = None
        self.long_press_timers = {}
        self.long_press_fired = set()
        self.pinch_start = None
        self.last_shake_time = 0
        self.shake_positions = []
        self.velocity = (0.0, 0.0)

    def start(self, touch_id, x, y):
        self.touches[touch_id] = {
            "points": [(x, y, time.time())],
            "start": (x, y),
            "start_time": time.time(),
            "last": (x, y),
            "state": "active",
        }
        self.long_press_fired.discard(touch_id)

    def move(self, touch_id, x, y):
        t = self.touches.get(touch_id)
        if not t:
            self.touches[touch_id] = {
                "points": [],
                "start": (x, y),
                "start_time": time.time(),
                "last": (x, y),
                "state": "active",
            }
            t = self.touches[touch_id]
        t["points"].append((x, y, time.time()))
        if len(t["points"]) > 20:
            t["points"].pop(0)
        t["last"] = (x, y)
        if t["state"] == "active" and t.get("long_press_triggered"):
            t["state"] = "dragging"

    def end(self, touch_id):
        return self.touches.pop(touch_id, None)

    def active_touches(self):
        return list(self.touches.keys())

    def touch_count(self):
        return len(self.touches)

    def check_long_press(self, touch_id):
        t = self.touches.get(touch_id)
        if not t or touch_id in self.long_press_fired:
            return None
        elapsed = time.time() - t["start_time"]
        dx = t["last"][0] - t["start"][0]
        dy = t["last"][1] - t["start"][1]
        dist = (dx * dx + dy * dy) ** 0.5
        if elapsed >= LONG_PRESS_TIME and dist < 20:
            self.long_press_fired.add(touch_id)
            t["long_press_triggered"] = True
            return "long_press"
        return None

    def detect_swipe(self, touch_id):
        t = self.touches.get(touch_id)
        if not t:
            return None
        points = t["points"]
        if len(points) < 3:
            return None
        first = points[0]
        last = points[-1]
        dx = last[0] - first[0]
        dy = last[1] - first[1]
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < SWIPE_THRESHOLD:
            return None
        duration = last[2] - first[2]
        velocity = dist / duration if duration > 0 else 0
        if velocity < 0.3:
            return None
        angle = math.atan2(dy, dx)
        if abs(angle) < math.pi / 4:
            return "swipe_right"
        elif abs(angle) > 3 * math.pi / 4:
            return "swipe_left"
        elif angle > 0:
            return "swipe_down"
        else:
            return "swipe_up"

    def detect_n_finger_swipe(self, active_touches):
        if len(active_touches) < 2:
            return None
        swipes = []
        for tid in active_touches:
            result = self.detect_swipe(tid)
            if result:
                swipes.append(result)
        if len(swipes) != len(active_touches):
            return None
        direction = swipes[0]
        if all(s == direction for s in swipes):
            finger_count = len(active_touches)
            if finger_count == 2:
                return f"2F_{direction}"
            elif finger_count == 3:
                return f"3F_{direction}"
            elif finger_count >= 4:
                return f"4F_{direction}"
        return None

    def detect_pinch(self):
        active = [t for t in self.touches.values() if t["state"] == "active"]
        if len(active) < 2:
            self.pinch_start = None
            return None
        positions = [t["last"] for t in active[:2]]
        current_dist = math.dist(positions[0], positions[1])
        if self.pinch_start is None:
            self.pinch_start = current_dist
            return None
        ratio = current_dist / self.pinch_start if self.pinch_start > 0 else 1.0
        if ratio > PINCH_RATIO_THRESHOLD:
            self.pinch_start = current_dist
            return "pinch_out"
        elif ratio < 1.0 / PINCH_RATIO_THRESHOLD:
            self.pinch_start = current_dist
            return "pinch_in"
        return None

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

    def detect_shake(self, x, y):
        now = time.time()
        self.shake_positions.append((x, y, now))
        while self.shake_positions and now - self.shake_positions[0][2] > SHAKE_WINDOW:
            self.shake_positions.pop(0)
        if len(self.shake_positions) < 5:
            return False
        total_movement = sum(
            math.dist((self.shake_positions[i][0], self.shake_positions[i][1]),
                      (self.shake_positions[i - 1][0], self.shake_positions[i - 1][1]))
            for i in range(1, len(self.shake_positions))
        )
        avg_velocity = total_movement / (now - self.shake_positions[0][2]) if (now - self.shake_positions[0][2]) > 0 else 0
        if avg_velocity > SHAKE_THRESHOLD:
            direction_changes = sum(
                1 for i in range(2, len(self.shake_positions))
                if ((self.shake_positions[i][0] - self.shake_positions[i - 1][0]) *
                    (self.shake_positions[i - 1][0] - self.shake_positions[i - 2][0])) < 0
            )
            if direction_changes >= 3:
                self.shake_positions.clear()
                return True
        return False

    def compute_velocity(self, touch_id):
        t = self.touches.get(touch_id)
        if not t or len(t["points"]) < 3:
            return (0.0, 0.0)
        recent = t["points"][-5:]
        if len(recent) < 2:
            return (0.0, 0.0)
        dt = recent[-1][2] - recent[0][2]
        if dt < 0.001:
            return (0.0, 0.0)
        dx = recent[-1][0] - recent[0][0]
        dy = recent[-1][1] - recent[0][1]
        vx = dx / dt
        vy = dy / dt
        self.velocity = (
            self.velocity[0] * VELOCITY_SMOOTHING + vx * (1 - VELOCITY_SMOOTHING),
            self.velocity[1] * VELOCITY_SMOOTHING + vy * (1 - VELOCITY_SMOOTHING),
        )
        return self.velocity

    def reset(self):
        self.touches.clear()
        self.last_tap_time = 0
        self.last_tap_pos = None
        self.long_press_timers.clear()
        self.long_press_fired.clear()
        self.pinch_start = None
        self.shake_positions.clear()
        self.velocity = (0.0, 0.0)
