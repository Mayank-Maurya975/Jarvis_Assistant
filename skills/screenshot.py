###############################################
# FILE: skills/screenshot.py
# PURPOSE: Captures full screen screenshot and saves to Desktop
#          with a timestamp filename. Notifies user with file path.
# DEPENDENCIES: pyautogui, datetime, os, core/speaker.py
# CONNECTED TO: core/intent.py
###############################################

import os
import datetime
import pyautogui
import core.speaker as speaker
from config import SCREENSHOT_DIR


def take_screenshot():
    try:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"JARVIS_Screenshot_{ts}.png"
        save_dir = os.path.expanduser(SCREENSHOT_DIR)
        path = os.path.join(save_dir, filename)
        img = pyautogui.screenshot()
        img.save(path)
        speaker.speak(f"Screenshot saved to your Desktop as {filename}, sir.")
    except Exception as e:
        print(f"[Screenshot] Error: {e}")
        speaker.speak("I could not take a screenshot, sir.")
