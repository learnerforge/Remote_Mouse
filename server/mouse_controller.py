import logging

logger = logging.getLogger("touchmorph.mouse")

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
    HAVE_PYAUTOGUI = True
except ImportError:
    HAVE_PYAUTOGUI = False
    logger.warning("pyautogui not installed — running in preview mode")


class MouseController:
    def __init__(self):
        self._screen_w = 1920
        self._screen_h = 1080
        if HAVE_PYAUTOGUI:
            try:
                w, h = pyautogui.size()
                self._screen_w = w
                self._screen_h = h
            except Exception:
                pass

    def move(self, x, y):
        if HAVE_PYAUTOGUI:
            try:
                pyautogui.moveTo(int(x), int(y))
            except Exception as e:
                logger.error(f"moveTo failed: {e}")
        else:
            logger.info(f"[Preview] moveTo({x}, {y})")

    def click(self, button="left"):
        if HAVE_PYAUTOGUI:
            try:
                btn = "left" if button == "left" else ("right" if button == "right" else "middle")
                pyautogui.click(button=btn)
            except Exception as e:
                logger.error(f"click failed: {e}")
        else:
            logger.info(f"[Preview] click({button})")

    def double_click(self):
        if HAVE_PYAUTOGUI:
            try:
                pyautogui.doubleClick()
            except Exception as e:
                logger.error(f"doubleClick failed: {e}")
        else:
            logger.info("[Preview] doubleClick()")

    def middle_click(self):
        if HAVE_PYAUTOGUI:
            try:
                pyautogui.click(button="middle")
            except Exception as e:
                logger.error(f"middleClick failed: {e}")
        else:
            logger.info("[Preview] middleClick()")

    def hold(self):
        if HAVE_PYAUTOGUI:
            try:
                pyautogui.mouseDown()
            except Exception as e:
                logger.error(f"mouseDown failed: {e}")
        else:
            logger.info("[Preview] mouseDown()")

    def release(self):
        if HAVE_PYAUTOGUI:
            try:
                pyautogui.mouseUp()
            except Exception as e:
                logger.error(f"mouseUp failed: {e}")
        else:
            logger.info("[Preview] mouseUp()")

    def scroll(self, dx, dy):
        if HAVE_PYAUTOGUI:
            try:
                clicks = int(-dy / 10)
                if clicks != 0:
                    pyautogui.scroll(clicks)
            except Exception as e:
                logger.error(f"scroll failed: {e}")
        else:
            logger.info(f"[Preview] scroll({dx}, {dy})")

    def scroll_smooth(self, dx, dy):
        if HAVE_PYAUTOGUI:
            try:
                clicks_x = int(dx / 10)
                clicks_y = int(-dy / 10)
                if clicks_y != 0:
                    pyautogui.scroll(clicks_y)
                if clicks_x != 0:
                    pyautogui.hscroll(clicks_x)
            except Exception as e:
                logger.error(f"smoothScroll failed: {e}")
        else:
            logger.info(f"[Preview] smoothScroll({dx}, {dy})")

    def position(self):
        if HAVE_PYAUTOGUI:
            try:
                return pyautogui.position()
            except Exception as e:
                logger.error(f"position failed: {e}")
        return (0, 0)

    def key_combo(self, *keys):
        if HAVE_PYAUTOGUI:
            try:
                pyautogui.hotkey(*keys)
            except Exception as e:
                logger.error(f"keyCombo {keys} failed: {e}")
        else:
            logger.info(f"[Preview] keyCombo({keys})")

    def press(self, key):
        if HAVE_PYAUTOGUI:
            try:
                pyautogui.press(key)
            except Exception as e:
                logger.error(f"press {key} failed: {e}")
        else:
            logger.info(f"[Preview] press({key})")

    def media_play_pause(self):
        self.press("playpause")

    def media_next(self):
        self.press("nexttrack")

    def media_prev(self):
        self.press("prevtrack")

    def media_vol_up(self):
        self.press("volumeup")

    def media_vol_down(self):
        self.press("volumedown")

    def media_mute(self):
        self.press("volumemute")

    def alt_tab(self):
        self.key_combo("alt", "tab")

    def task_view(self):
        self.key_combo("win", "tab")

    def show_desktop(self):
        self.key_combo("win", "d")

    def switch_window(self):
        self.key_combo("alt", "shift", "tab")

    def copy(self):
        self.key_combo("ctrl", "c")

    def paste(self):
        self.key_combo("ctrl", "v")

    def cut(self):
        self.key_combo("ctrl", "x")

    def undo(self):
        self.key_combo("ctrl", "z")

    def redo(self):
        self.key_combo("ctrl", "shift", "z")

    def select_all(self):
        self.key_combo("ctrl", "a")

    def save(self):
        self.key_combo("ctrl", "s")

    def find(self):
        self.key_combo("ctrl", "f")

    def esc(self):
        self.press("esc")

    def enter(self):
        self.press("enter")

    def arrow(self, direction):
        self.press(direction)

    def fullscreen(self):
        self.press("f11")

    def lock_screen(self):
        self.key_combo("win", "l")
