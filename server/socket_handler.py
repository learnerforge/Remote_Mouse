import random
import logging
import time

from mouse_controller import MouseController
from gesture_processor import GestureProcessor
from session_store import (
    create_session,
    restore_session,
    update_session,
    touch_session,
    list_sessions,
    delete_session,
    log_event,
)

logger = logging.getLogger("touchmorph.ws")


class TouchMorphSocket:
    def __init__(self):
        self.sessions = {}  # sid -> session dict
        self.sid_to_token = {}  # sid -> token
        self.mouse = MouseController()
        self.gesture = GestureProcessor()
        self.active_token = None  # which token currently controls the mouse

    async def on_connect(self, sid, environ=None):
        ip = ""
        if environ:
            headers = dict(environ.get("headers", []))
            ip = headers.get("x-forwarded-for", headers.get("remote-addr", ""))

        self.sessions[sid] = {
            "sid": sid,
            "token": None,
            "paired": False,
            "pairing_code": None,
            "mode": "mouse",
            "connected_at": time.time(),
        }
        self.sid_to_token[sid] = None
        logger.info(f"Client connected: {sid} from {ip}")

    async def on_disconnect(self, sid):
        session = self.sessions.pop(sid, None)
        token = self.sid_to_token.pop(sid, None)
        if session and token:
            touch_session(token)
            log_event(token, "disconnect")
        logger.info(f"Client disconnected: {sid}")

    async def on_session_restore(self, sid, data, sio):
        token = data.get("token", "")
        stored = restore_session(token) if token else None
        if stored:
            self.sessions[sid]["token"] = token
            self.sessions[sid]["paired"] = stored["paired"]
            self.sessions[sid]["mode"] = stored["mode"]
            self.sid_to_token[sid] = token
            touch_session(token)
            log_event(token, "reconnect")
            await sio.emit("session:restored", {
                "token": token,
                "paired": stored["paired"],
                "mode": stored["mode"],
            }, to=sid)
            logger.info(f"Session restored for {sid}: {token}")
            return True
        else:
            # Create new session
            token = create_session()
            self.sessions[sid]["token"] = token
            self.sid_to_token[sid] = token
            log_event(token, "connect")
            await sio.emit("session:created", {"token": token}, to=sid)
            return False

    async def on_pair_request(self, sid, sio):
        code = str(random.randint(100000, 999999))
        if sid in self.sessions:
            self.sessions[sid]["pairing_code"] = code
            self.sessions[sid]["paired"] = False
        await sio.emit("pair:code", {"code": code}, to=sid)
        logger.info(f"Pairing code generated for {sid}: {code}")

    async def on_pair_verify(self, sid, data, sio):
        session = self.sessions.get(sid)
        if not session:
            return
        code = data.get("code", "")
        if session["pairing_code"] and code == session["pairing_code"]:
            session["paired"] = True
            token = self.sid_to_token.get(sid)
            if token:
                update_session(token, paired=1)
                log_event(token, "paired")
            await sio.emit("pair:success", {"message": "Device paired successfully"}, to=sid)
            logger.info(f"Device paired: {sid}")
        else:
            await sio.emit("pair:error", {"message": "Invalid pairing code"}, to=sid)

    async def on_mode_switch(self, sid, data, sio):
        session = self.sessions.get(sid)
        if not session:
            return
        mode = data.get("mode", "mouse")
        if mode in ("mouse", "touchpad"):
            session["mode"] = mode
            token = self.sid_to_token.get(sid)
            if token:
                update_session(token, mode=mode)
                log_event(token, f"mode:{mode}")
            await sio.emit("mode:switched", {"mode": mode}, to=sid)
            logger.info(f"Mode switched: {sid} -> {mode}")

    async def on_click(self, sid, button):
        if self._is_active(sid):
            self.mouse.click(button)
            self._log(sid, f"click:{button}")

    async def on_double_click(self, sid):
        if self._is_active(sid):
            self.mouse.double_click()
            self._log(sid, "double_click")

    async def on_scroll(self, sid, data):
        if self._is_active(sid):
            dx = data.get("deltaX", 0)
            dy = data.get("deltaY", 0)
            self.mouse.scroll(dx, dy)
            self._log(sid, "scroll")

    async def on_mouse_event(self, sid, data):
        if not self._is_active(sid):
            return
        event_type = data.get("type", "")
        if event_type == "move":
            x = data.get("x", 0)
            y = data.get("y", 0)
            self.mouse.move(x, y)
        elif event_type == "click":
            self.mouse.click(data.get("button", "left"))
        elif event_type == "doubleclick":
            self.mouse.double_click()
        elif event_type == "scroll":
            dx = data.get("deltaX", 0)
            dy = data.get("deltaY", 0)
            self.mouse.scroll(dx, dy)
        self._log(sid, f"mouse:{event_type}")

    async def on_touchpad_event(self, sid, data):
        if not self._is_active(sid):
            return
        event_type = data.get("type", "")
        if event_type == "move":
            dx = data.get("deltaX", 0)
            dy = data.get("deltaY", 0)
            x, y = self.mouse.position()
            self.mouse.move(x + dx, y + dy)
        elif event_type == "tap":
            self.mouse.click("left")
        elif event_type == "two_finger_scroll":
            dx = data.get("deltaX", 0)
            dy = data.get("deltaY", 0)
            self.mouse.scroll(dx, dy)
        self._log(sid, f"touchpad:{event_type}")

    def _is_active(self, sid) -> bool:
        token = self.sid_to_token.get(sid)
        if token:
            touch_session(token)
            self.active_token = token
        return True

    async def get_devices(self) -> list[dict]:
        return list_sessions()

    async def kick_device(self, token: str, sio):
        delete_session(token)
        # Find and disconnect the corresponding socket
        for sid, t in list(self.sid_to_token.items()):
            if t == token:
                self.sessions.pop(sid, None)
                self.sid_to_token.pop(sid, None)
                await sio.disconnect(sid)
                logger.info(f"Kicked device with token {token} (sid {sid})")
                break

    def _log(self, sid, event):
        token = self.sid_to_token.get(sid)
        if token:
            log_event(token, event)
