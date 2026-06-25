import random
import asyncio
import logging
import time

from mouse_controller import MouseController
from gesture_processor import GestureProcessor, SmartScrollEngine
from session_store import (
    create_session,
    restore_session,
    update_session,
    touch_session,
    list_sessions,
    delete_session,
    log_event,
    audit_log,
)

logger = logging.getLogger("touchmorph.ws")

VALID_MODES = ("mouse", "touchpad", "airmouse", "presentation", "media")
VALID_BUTTONS = ("left", "right", "middle")
VALID_DIRECTIONS = ("left", "right", "up", "down")
RATE_LIMIT_EVENTS = 60
RATE_LIMIT_WINDOW = 1.0


class TouchMorphSocket:
    def __init__(self):
        self.sessions = {}
        self.sid_to_token = {}
        self.mouse = MouseController()
        self.gesture = GestureProcessor()
        self.scroll_engine = SmartScrollEngine()
        self.active_token = None
        self.mouse_state = {"held": False}
        self._rate_buckets = {}
        self._airmouse_log_throttle = {}

    def _check_rate(self, sid) -> bool:
        now = time.time()
        bucket = self._rate_buckets.get(sid)
        if not bucket or now - bucket["reset"] > RATE_LIMIT_WINDOW:
            self._rate_buckets[sid] = {"count": 1, "reset": now}
            return True
        bucket["count"] += 1
        if bucket["count"] > RATE_LIMIT_EVENTS:
            return False
        return True

    def _rate_warn(self, sid):
        now = time.time()
        last = self._rate_buckets.get(sid, {}).get("last_warn", 0)
        if now - last > 5:
            self._rate_buckets[sid]["last_warn"] = now
            return True
        return False

    def _get_ip(self, sid) -> str:
        s = self.sessions.get(sid, {})
        return s.get("ip", "")

    def _get_device_name(self, sid) -> str:
        s = self.sessions.get(sid, {})
        return s.get("device_name", "")

    async def on_connect(self, sid, environ=None):
        ip = ""
        device_name = ""
        if environ:
            headers = dict(environ.get("headers", []))
            ip = headers.get("x-forwarded-for", headers.get("remote-addr", ""))
            ua = headers.get("user-agent", "")
            if "android" in ua.lower():
                device_name = "Android"
            elif "iphone" in ua.lower() or "ipad" in ua.lower():
                device_name = "iOS"
        self.sessions[sid] = {
            "sid": sid,
            "token": None,
            "ip": ip,
            "device_name": device_name,
            "paired": False,
            "pairing_code": None,
            "mode": "mouse",
            "connected_at": time.time(),
        }
        self.sid_to_token[sid] = None
        logger.info(f"Client connected: {sid} from {ip}")
        audit_log("", "connection", "connect", {"sid": sid},
                  ip=ip, device_name=device_name, severity="info")

    async def on_disconnect(self, sid):
        session = self.sessions.pop(sid, None)
        token = self.sid_to_token.pop(sid, None)
        self._rate_buckets.pop(sid, None)
        self._airmouse_log_throttle.pop(sid, None)
        if session:
            ip = session.get("ip", "")
            dn = session.get("device_name", "")
            touch_session(token) if token else None
            audit_log(token or "", "connection", "disconnect", {"sid": sid},
                      ip=ip, device_name=dn)
        logger.info(f"Client disconnected: {sid}")

    def _screen_info(self):
        return {
            "width": self.mouse._screen_w,
            "height": self.mouse._screen_h,
        }

    # ─── Session & Pairing ────────────────────────────────────────────────

    async def on_session_restore(self, sid, data, sio):
        token = data.get("token", "") if isinstance(data, dict) else ""
        stored = restore_session(token) if token else None
        ip = self._get_ip(sid)
        dn = self._get_device_name(sid)
        if stored:
            self.sessions[sid]["token"] = token
            self.sessions[sid]["paired"] = stored["paired"]
            self.sessions[sid]["mode"] = stored["mode"]
            self.sid_to_token[sid] = token
            touch_session(token)
            audit_log(token, "connection", "reconnect", {"sid": sid},
                      ip=ip, device_name=dn)
            info = self._screen_info()
            await sio.emit("session:restored", {
                "token": token, "paired": stored["paired"],
                "mode": stored["mode"],
                "screenWidth": info["width"], "screenHeight": info["height"],
            }, to=sid)
            logger.info(f"Session restored for {sid}: {token}")
            return True
        else:
            token = create_session(ip=ip)
            self.sessions[sid]["token"] = token
            self.sid_to_token[sid] = token
            self.sessions[sid]["device_name"] = dn
            update_session(token, ip=ip, device_name=dn)
            audit_log(token, "connection", "connect", {"sid": sid},
                      ip=ip, device_name=dn)
            info = self._screen_info()
            await sio.emit("session:created", {"token": token,
                "screenWidth": info["width"], "screenHeight": info["height"]}, to=sid)
            return False

    async def on_pair_request(self, sid, sio):
        code = str(random.randint(100000, 999999))
        if sid in self.sessions:
            self.sessions[sid]["pairing_code"] = code
            self.sessions[sid]["paired"] = False
        await sio.emit("pair:code", {"code": code}, to=sid)
        token = self.sid_to_token.get(sid)
        audit_log(token or "", "connection", "pair_request", {"code": code},
                  ip=self._get_ip(sid), device_name=self._get_device_name(sid))
        logger.info(f"Pairing code generated for {sid}: {code}")

    async def on_pair_verify(self, sid, data, sio):
        session = self.sessions.get(sid)
        if not session:
            return
        code = data.get("code", "") if isinstance(data, dict) else ""
        token = self.sid_to_token.get(sid)
        ip = self._get_ip(sid)
        dn = self._get_device_name(sid)
        if session["pairing_code"] and code == session["pairing_code"]:
            session["paired"] = True
            if token:
                update_session(token, paired=1)
            audit_log(token or "", "connection", "paired", {"code": code},
                      ip=ip, device_name=dn)
            await sio.emit("pair:success", {"message": "Device paired successfully"}, to=sid)
            logger.info(f"Device paired: {sid}")
        else:
            audit_log(token or "", "security", "pair_failed",
                      {"attempted_code": code},
                      ip=ip, device_name=dn, severity="warning")
            await sio.emit("pair:error", {"message": "Invalid pairing code"}, to=sid)

    async def on_mode_switch(self, sid, data, sio):
        session = self.sessions.get(sid)
        if not session:
            return
        mode = data.get("mode", "") if isinstance(data, dict) else ""
        token = self.sid_to_token.get(sid)
        ip = self._get_ip(sid)
        if mode in VALID_MODES:
            old_mode = session.get("mode", "mouse")
            session["mode"] = mode
            if token:
                update_session(token, mode=mode)
            audit_log(token or "", "system", "mode_switch",
                      {"from": old_mode, "to": mode},
                      ip=ip, device_name=self._get_device_name(sid))
            info = self._screen_info()
            await sio.emit("mode:switched", {
                "mode": mode,
                "screenWidth": info["width"],
                "screenHeight": info["height"],
            }, to=sid)
        else:
            audit_log(token or "", "security", "invalid_mode",
                      {"attempted": mode, "valid": list(VALID_MODES)},
                      ip=ip, severity="warning")
            await sio.emit("mode:switched", {"mode": "mouse"}, to=sid)

    # ─── Mouse ────────────────────────────────────────────────────────────

    async def on_click(self, sid, button):
        if not self._check_rate(sid):
            if self._rate_warn(sid):
                audit_log(self.sid_to_token.get(sid) or "", "security", "rate_limited",
                          "click", ip=self._get_ip(sid), severity="warning")
            return
        if not self._is_active(sid):
            return
        if button not in VALID_BUTTONS:
            audit_log(self.sid_to_token.get(sid) or "", "security", "invalid_button",
                      {"button": button}, ip=self._get_ip(sid), severity="warning")
            return
        self.mouse.click(button)
        self._log(sid, "mouse", "click", {"button": button})

    async def on_double_click(self, sid):
        if not self._check_rate(sid):
            return
        if not self._is_active(sid):
            return
        self.mouse.double_click()
        self._log(sid, "mouse", "double_click")

    async def on_scroll(self, sid, data):
        if not self._check_rate(sid):
            return
        if not self._is_active(sid):
            return
        if not isinstance(data, dict):
            self._log(sid, "security", "invalid_payload", {"type": type(data).__name__}, severity="warning")
            return
        dx = _num(data.get("deltaX", 0))
        dy = _num(data.get("deltaY", 0))
        self.mouse.scroll(dx, dy)
        self._log(sid, "mouse", "scroll", {"deltaX": dx, "deltaY": dy})

    async def on_mouse_event(self, sid, data):
        if not self._check_rate(sid):
            return
        if not self._is_active(sid):
            return
        if not isinstance(data, dict):
            self._log(sid, "security", "invalid_payload", {"type": type(data).__name__}, severity="warning")
            return
        event_type = data.get("type", "")
        if event_type == "move":
            x = _num(data.get("x", 0))
            y = _num(data.get("y", 0))
            self.mouse.move(x, y)
        elif event_type == "click":
            btn = data.get("button", "left")
            if btn in VALID_BUTTONS:
                self.mouse.click(btn)
            else:
                self._log(sid, "security", "invalid_button", {"button": btn}, severity="warning")
                return
        elif event_type == "doubleclick":
            self.mouse.double_click()
        elif event_type == "scroll":
            dx = _num(data.get("deltaX", 0))
            dy = _num(data.get("deltaY", 0))
            self.mouse.scroll(dx, dy)
        else:
            self._log(sid, "security", "unknown_event_type", {"type": event_type}, severity="warning")
            return
        self._log(sid, "mouse", event_type)

    async def on_mouse_hold(self, sid):
        if not self._is_active(sid):
            return
        self.mouse.hold()
        self.mouse_state["held"] = True
        self._log(sid, "mouse", "hold")

    async def on_mouse_release(self, sid):
        if not self._is_active(sid):
            return
        self.mouse.release()
        self.mouse_state["held"] = False
        self._log(sid, "mouse", "release")

    async def on_mouse_drag(self, sid, data):
        if not self._is_active(sid) or not self.mouse_state["held"]:
            return
        if not isinstance(data, dict):
            return
        x = _num(data.get("x", 0))
        y = _num(data.get("y", 0))
        self.mouse.move(x, y)
        self._log(sid, "mouse", "drag", {"x": x, "y": y})

    # ─── Touchpad ─────────────────────────────────────────────────────────

    async def on_touchpad_event(self, sid, data):
        if not self._check_rate(sid) or not self._is_active(sid):
            return
        if not isinstance(data, dict):
            self._log(sid, "security", "invalid_payload", {"type": type(data).__name__}, severity="warning")
            return
        event_type = data.get("type", "")
        if event_type == "move":
            dx = _num(data.get("deltaX", 0))
            dy = _num(data.get("deltaY", 0))
            x, y = self.mouse.position()
            self.mouse.move(int(x + dx), int(y + dy))
            nx, ny = self.mouse.position()
            edge_margin = 5
            if nx >= self.mouse._screen_w - edge_margin:
                self.mouse.scroll(-dx, 0)
            elif nx <= edge_margin:
                self.mouse.scroll(-dx, 0)
            if ny >= self.mouse._screen_h - edge_margin:
                self.mouse.scroll(0, -dy)
            elif ny <= edge_margin:
                self.mouse.scroll(0, -dy)
        elif event_type == "tap":
            self.mouse.click("left")
        elif event_type == "double_tap":
            self.mouse.double_click()
        elif event_type == "two_finger_scroll":
            dx = _num(data.get("deltaX", 0))
            dy = _num(data.get("deltaY", 0))
            self.mouse.scroll(dx, dy)
        elif event_type == "two_finger_tap":
            self.mouse.click("right")
        elif event_type == "three_finger_tap":
            self.mouse.middle_click()
        else:
            self._log(sid, "security", "unknown_touchpad_event",
                      {"type": event_type}, severity="warning")
            return
        self._log(sid, "touchpad", event_type)

    async def on_smart_scroll_start(self, sid):
        if not self._is_active(sid):
            return
        self.scroll_engine.start()

    async def on_smart_scroll_move(self, sid, data):
        if not self._check_rate(sid) or not self._is_active(sid):
            return
        if not isinstance(data, dict):
            return
        dx = _num(data.get("deltaX", 0))
        dy = _num(data.get("deltaY", 0))
        self.scroll_engine.update(dx, dy)
        sx, sy, _ = self.scroll_engine.get_momentum()
        self.mouse.scroll_smooth(sx, sy)

    async def on_smart_scroll_end(self, sid, sio):
        if not self._is_active(sid):
            return
        self._log(sid, "touchpad", "smart_scroll_end")
        async def momentum_loop():
            for _ in range(60):
                sx, sy, active = self.scroll_engine.get_momentum()
                if not active:
                    break
                self.mouse.scroll_smooth(sx, sy)
                await asyncio.sleep(0.016)
            self.scroll_engine.stop()
        asyncio.ensure_future(momentum_loop())

    async def on_smart_scroll_config(self, sid, data):
        if isinstance(data, dict):
            self.scroll_engine.set_config(
                invert=data.get("invert"),
                sensitivity=_num(data.get("sensitivity", 1.0)),
                decay=_num(data.get("decay", 0.92)),
            )
            self._log(sid, "touchpad", "smart_scroll_config",
                      {"invert": data.get("invert"), "sensitivity": data.get("sensitivity"),
                       "decay": data.get("decay")})

    # ─── Gesture ──────────────────────────────────────────────────────────

    async def on_gesture_start(self, sid, data):
        if not self._is_active(sid) or not isinstance(data, dict):
            return
        touch_id = _num(data.get("touchId", 0))
        x = _num(data.get("x", 0))
        y = _num(data.get("y", 0))
        self.gesture.start(touch_id, x, y)

    async def on_gesture_move(self, sid, data):
        if not self._is_active(sid) or not isinstance(data, dict):
            return
        touch_id = _num(data.get("touchId", 0))
        x = _num(data.get("x", 0))
        y = _num(data.get("y", 0))
        self.gesture.move(touch_id, x, y)

        touches = self.gesture.active_touches()
        mode = self.sessions.get(sid, {}).get("mode", "mouse")
        if mode in ("mouse", "touchpad") and len(touches) >= 2:
            pinch = self.gesture.detect_pinch()
            if pinch:
                self._log(sid, "gesture", "pinch", {"direction": pinch})
                await sio.emit("gesture:detected", {"gesture": pinch}, to=sid)
        if mode == "airmouse" and self.gesture.detect_shake(x, y):
            self._log(sid, "gesture", "shake")
            await sio.emit("gesture:detected", {"gesture": "shake"}, to=sid)
        lp = self.gesture.check_long_press(touch_id)
        if lp:
            self._log(sid, "gesture", lp)
            await sio.emit("gesture:detected", {"gesture": lp}, to=sid)
            if mode == "mouse":
                self.mouse.hold()
                self.mouse_state["held"] = True
        self.gesture.compute_velocity(touch_id)

    async def on_gesture_end(self, sid, data, sio):
        if not self._is_active(sid) or not isinstance(data, dict):
            return
        touch_id = _num(data.get("touchId", 0))
        touches_before = self.gesture.touch_count()
        self.gesture.end(touch_id)
        touches_after = self.gesture.touch_count()
        mode = self.sessions.get(sid, {}).get("mode", "mouse")
        if mode == "mouse" and self.mouse_state.get("held") and touches_before == 1 and touches_after == 0:
            self.mouse.release()
            self.mouse_state["held"] = False

    async def on_gesture_n_finger_swipe(self, sid, data, sio):
        if not self._is_active(sid) or not isinstance(data, dict):
            return
        finger_count = int(data.get("fingerCount", 0))
        direction = data.get("direction", "")
        if finger_count < 2 or direction not in VALID_DIRECTIONS:
            self._log(sid, "security", "invalid_swipe",
                      {"fingerCount": finger_count, "direction": direction}, severity="warning")
            return
        gesture_name = f"{finger_count}F_{direction}"
        self._log(sid, "gesture", gesture_name)
        mode = self.sessions.get(sid, {}).get("mode", "mouse")

        if mode in ("mouse", "touchpad"):
            if finger_count == 2 and direction in ("left", "right"):
                self.mouse.scroll(0, 120 if direction == "right" else -120)
            elif finger_count == 3:
                acts = {"left": "alt_tab", "right": "switch_window", "up": "task_view", "down": "show_desktop"}
                getattr(self.mouse, acts.get(direction, "alt_tab"))()
            elif finger_count == 4:
                acts = {"up": "show_desktop", "down": "lock_screen"}
                getattr(self.mouse, acts.get(direction, "show_desktop"))()
        elif mode == "presentation":
            acts = {"left": "left", "right": "right", "up": "b", "down": "w"}
            self.mouse.press(acts.get(direction, "right"))

    # ─── Air Mouse ────────────────────────────────────────────────────────

    async def on_airmouse_move(self, sid, data):
        if not self._check_rate(sid) or not self._is_active(sid):
            return
        if not isinstance(data, dict):
            return
        mode = data.get("mode", "relative")
        x, y = self.mouse.position()
        sw, sh = self.mouse._screen_w, self.mouse._screen_h
        if mode == "absolute":
            nx = _num(data.get("x", 0)) * sw
            ny = _num(data.get("y", 0)) * sh
        else:
            dx = _num(data.get("deltaX", 0))
            dy = _num(data.get("deltaY", 0))
            sens = _num(data.get("sensitivity", 1.5))
            nx = x + dx * sens
            ny = y + dy * sens
        self.mouse.move(max(0, min(sw, nx)), max(0, min(sh, ny)))
        # Throttled audit log for airmouse moves (once per 30s per sid)
        now = time.time()
        last = self._airmouse_log_throttle.get(sid, 0)
        if now - last > 30:
            self._airmouse_log_throttle[sid] = now
            self._log(sid, "airmouse", "move", {"mode": mode})

    async def on_airmouse_click(self, sid, data):
        if not self._is_active(sid) or not isinstance(data, dict):
            return
        btn = data.get("button", "left")
        if btn not in VALID_BUTTONS:
            self._log(sid, "security", "invalid_button", {"button": btn}, severity="warning")
            return
        self.mouse.click(btn)
        self._log(sid, "airmouse", "click", {"button": btn})

    async def on_screen_info(self, sid, sio):
        info = self._screen_info()
        await sio.emit("screen:dimensions", info, to=sid)
        self._log(sid, "system", "screen_info_request")

    # ─── Presentation ─────────────────────────────────────────────────────

    async def on_presentation_action(self, sid, data):
        if not self._is_active(sid) or not isinstance(data, dict):
            return
        action = data.get("action", "")
        if action == "next":
            self.mouse.press("right")
        elif action == "prev":
            self.mouse.press("left")
        elif action == "black":
            self.mouse.press("b")
        elif action == "white":
            self.mouse.press("w")
        elif action == "start":
            self.mouse.press("f5")
        elif action == "escape":
            self.mouse.press("esc")
        elif action == "first":
            self.mouse.press("home")
        elif action == "pointer":
            self.mouse.press("ctrl")
            self.mouse.hold()
        elif action == "pointer_stop":
            self.mouse.release()
        else:
            self._log(sid, "security", "unknown_presentation_action",
                      {"action": action}, severity="warning")
            return
        self._log(sid, "presentation", action)

    # ─── Media ────────────────────────────────────────────────────────────

    async def on_media_action(self, sid, data):
        if not self._is_active(sid) or not isinstance(data, dict):
            return
        action = data.get("action", "")
        if action == "play_pause":
            self.mouse.media_play_pause()
        elif action == "next":
            self.mouse.media_next()
        elif action == "prev":
            self.mouse.media_prev()
        elif action == "vol_up":
            self.mouse.media_vol_up()
        elif action == "vol_down":
            self.mouse.media_vol_down()
        elif action == "mute":
            self.mouse.media_mute()
        else:
            self._log(sid, "security", "unknown_media_action",
                      {"action": action}, severity="warning")
            return
        self._log(sid, "media", action)

    # ─── System ───────────────────────────────────────────────────────────

    async def on_system_action(self, sid, data):
        if not self._is_active(sid) or not isinstance(data, dict):
            return
        action = data.get("action", "")
        acts = {
            "alt_tab": self.mouse.alt_tab,
            "show_desktop": self.mouse.show_desktop,
            "task_view": self.mouse.task_view,
            "lock": self.mouse.lock_screen,
            "copy": self.mouse.copy,
            "paste": self.mouse.paste,
            "cut": self.mouse.cut,
            "undo": self.mouse.undo,
            "redo": self.mouse.redo,
            "select_all": self.mouse.select_all,
            "save": self.mouse.save,
            "find": self.mouse.find,
            "esc": self.mouse.esc,
            "enter": self.mouse.enter,
        }
        fn = acts.get(action)
        if fn:
            fn()
            self._log(sid, "system", action)
        else:
            self._log(sid, "security", "unknown_system_action",
                      {"action": action}, severity="warning")

    # ─── Helpers ──────────────────────────────────────────────────────────

    def _is_active(self, sid) -> bool:
        session = self.sessions.get(sid)
        if not session or not session.get("paired"):
            return False
        token = self.sid_to_token.get(sid)
        if token:
            touch_session(token)
            self.active_token = token
        return True

    async def get_devices(self) -> list[dict]:
        return list_sessions()

    async def kick_device(self, token: str, sio):
        delete_session(token)
        for sid, t in list(self.sid_to_token.items()):
            if t == token:
                self.sessions.pop(sid, None)
                self.sid_to_token.pop(sid, None)
                self._rate_buckets.pop(sid, None)
                self._airmouse_log_throttle.pop(sid, None)
                audit_log(token, "admin", "kicked", {"sid": sid},
                          ip=self._get_ip(sid), severity="warning")
                await sio.disconnect(sid)
                logger.info(f"Kicked device with token {token} (sid {sid})")
                break

    def _log(self, sid, category, event, detail=None, severity="info"):
        token = self.sid_to_token.get(sid)
        if detail is None:
            detail = ""
        audit_log(token or "", category, event, detail,
                  ip=self._get_ip(sid), device_name=self._get_device_name(sid),
                  severity=severity)


def _num(v, default=0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default
