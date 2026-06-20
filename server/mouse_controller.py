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
    def move(self, x, y):
        if HAVE_PYAUTOGUI:
            try:
                pyautogui.moveTo(x, y)
            except Exception as e:
                logger.error(f"moveTo failed: {e}")
        else:
            logger.info(f"[Preview] moveTo({x}, {y})")

    def click(self, button="left"):
        if HAVE_PYAUTOGUI:
            try:
                btn = "left" if button == "left" else "right"
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

    def position(self):
        if HAVE_PYAUTOGUI:
            try:
                return pyautogui.position()
            except Exception as e:
                logger.error(f"position failed: {e}")
        return (0, 0)
