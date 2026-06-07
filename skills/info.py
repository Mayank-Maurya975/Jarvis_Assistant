###############################################
# FILE: skills/info.py
# PURPOSE: Provides system information — battery, CPU, RAM, time, date.
#          Speaks and returns data for the UI dashboard.
# DEPENDENCIES: psutil, datetime, core/speaker.py
# CONNECTED TO: core/intent.py, server/app.py (dashboard API)
###############################################

import datetime
import psutil
import core.speaker as speaker


def battery_status():
    try:
        bat = psutil.sensors_battery()
        if bat:
            pct = int(bat.percent)
            status = "and currently charging" if bat.power_plugged else "and not charging"
            speaker.speak(f"Your battery is at {pct} percent, {status}, sir.")
        else:
            speaker.speak("I could not retrieve battery information, sir.")
    except Exception:
        speaker.speak("Battery information is unavailable, sir.")


def speak_time():
    now = datetime.datetime.now().strftime("%I:%M %p")
    speaker.speak(f"It is currently {now}, sir.")


def speak_date():
    today = datetime.datetime.now().strftime("%A, %B %d %Y")
    speaker.speak(f"Today is {today}, sir.")


def system_stats():
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        speaker.speak(
            f"CPU usage is at {cpu} percent, and RAM usage is at {ram} percent, sir."
        )
    except Exception:
        speaker.speak("I could not retrieve system statistics, sir.")


def get_dashboard_data() -> dict:
    """Returns a dict of all stats for the UI /api/stats endpoint."""
    data = {
        "cpu": 0,
        "ram": 0,
        "battery": None,
        "charging": False,
        "time": datetime.datetime.now().strftime("%I:%M:%S %p"),
        "date": datetime.datetime.now().strftime("%A, %B %d %Y"),
    }
    try:
        data["cpu"] = psutil.cpu_percent(interval=0.1)
        data["ram"] = psutil.virtual_memory().percent
        bat = psutil.sensors_battery()
        if bat:
            data["battery"] = int(bat.percent)
            data["charging"] = bat.power_plugged
    except Exception:
        pass
    return data
