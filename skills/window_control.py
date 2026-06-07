###############################################
# FILE: skills/window_control.py
# PURPOSE: Controls open windows — minimize, maximize, restore, close.
#          Also handles browser tab switching via keyboard shortcuts.
#          Uses pygetwindow for window management and pyautogui for hotkeys.
# DEPENDENCIES: pygetwindow, pyautogui, core/speaker.py
# CONNECTED TO: core/intent.py
###############################################

import time
import pyautogui
import core.speaker as speaker

try:
    import pygetwindow as gw
    _GW = True
except Exception:
    _GW = False


def _find_window(name: str):
    """Find first window whose title contains name (case-insensitive)."""
    if not _GW:
        return None
    try:
        name_lower = name.lower()
        for w in gw.getAllWindows():
            if w.title and name_lower in w.title.lower():
                return w
    except Exception:
        pass
    return None


def minimize_window(app_name: str):
    speaker.speak(f"Minimizing {app_name}, sir.")
    try:
        win = _find_window(app_name)
        if win:
            win.minimize()
        else:
            speaker.speak(f"I could not find a window for {app_name}, sir.")
    except Exception as e:
        speaker.speak(f"Could not minimize {app_name}, sir.")


def minimize_all_windows():
    speaker.speak("Minimizing all windows, sir.")
    try:
        pyautogui.hotkey("win", "d")
    except Exception:
        speaker.speak("I could not minimize all windows, sir.")


def maximize_window(app_name: str):
    speaker.speak(f"Maximizing {app_name}, sir.")
    try:
        win = _find_window(app_name)
        if win:
            win.maximize()
        else:
            speaker.speak(f"I could not find a window for {app_name}, sir.")
    except Exception:
        speaker.speak(f"Could not maximize {app_name}, sir.")


def restore_window(app_name: str):
    speaker.speak(f"Restoring {app_name}, sir.")
    try:
        win = _find_window(app_name)
        if win:
            win.restore()
        else:
            speaker.speak(f"I could not find a window for {app_name}, sir.")
    except Exception:
        speaker.speak(f"Could not restore {app_name}, sir.")


def close_window(app_name: str):
    speaker.speak(f"Closing {app_name} window, sir.")
    try:
        win = _find_window(app_name)
        if win:
            win.close()
        else:
            speaker.speak(f"I could not find a window for {app_name}, sir.")
    except Exception:
        speaker.speak(f"Could not close {app_name} window, sir.")


def switch_tab_next():
    speaker.speak("Switching to next tab, sir.")
    try:
        pyautogui.hotkey("ctrl", "tab")
    except Exception:
        speaker.speak("Could not switch tab, sir.")


def switch_tab_prev():
    speaker.speak("Switching to previous tab, sir.")
    try:
        pyautogui.hotkey("ctrl", "shift", "tab")
    except Exception:
        speaker.speak("Could not switch tab, sir.")


def switch_tab_number(n: int):
    speaker.speak(f"Switching to tab {n}, sir.")
    try:
        pyautogui.hotkey("ctrl", str(n))
    except Exception:
        speaker.speak(f"Could not switch to tab {n}, sir.")


def new_tab():
    speaker.speak("Opening a new tab, sir.")
    try:
        pyautogui.hotkey("ctrl", "t")
    except Exception:
        speaker.speak("Could not open new tab, sir.")


def close_tab():
    speaker.speak("Closing current tab, sir.")
    try:
        pyautogui.hotkey("ctrl", "w")
    except Exception:
        speaker.speak("Could not close tab, sir.")
