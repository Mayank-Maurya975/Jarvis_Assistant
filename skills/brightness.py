###############################################
# FILE: skills/brightness.py
# PURPOSE: Controls screen brightness on Windows laptops.
#          Set exact value or increase/decrease by steps.
#          Emits brightness_update socket event to sync UI slider.
# DEPENDENCIES: screen_brightness_control, core/speaker.py
# CONNECTED TO: core/intent.py
###############################################

import core.speaker as speaker

try:
    import screen_brightness_control as sbc
    _SBC = True
except Exception:
    _SBC = False


def _emit(event, data):
    if speaker._socketio:
        try:
            speaker._socketio.emit(event, data)
        except Exception:
            pass


def get_brightness() -> int:
    if _SBC:
        try:
            val = sbc.get_brightness(display=0)
            return int(val[0]) if val else 50
        except Exception:
            pass
    return 50


def set_brightness(level: int):
    level = max(0, min(100, int(level)))
    if _SBC:
        try:
            sbc.set_brightness(level)
            speaker.speak(f"Brightness set to {level} percent, sir.")
            _emit("brightness_update", {"value": level})
            return
        except Exception:
            pass
    speaker.speak("Brightness control is not supported on this display, sir.")


def increase_brightness(step: int = 10):
    set_brightness(get_brightness() + step)


def decrease_brightness(step: int = 10):
    set_brightness(get_brightness() - step)
