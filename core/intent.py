###############################################
# FILE: core/intent.py
# PURPOSE: Decision engine — routes every command to the correct skill.
#          Stop command is highest priority. Falls back to Groq LLM.
# DEPENDENCIES: re, all skills/, core/brain.py, core/speaker.py
# CONNECTED TO: core/voice.py and server/events.py send commands here
###############################################

import re
import core.speaker as speaker
import core.brain as brain
import skills.apps as apps
import skills.explorer as explorer
import skills.volume as volume
import skills.brightness as brightness
import skills.system as system
import skills.info as info
import skills.screenshot as screenshot
import skills.window_control as wc

_pending_confirmation = None


def _emit(event, data):
    if speaker._socketio:
        try:
            speaker._socketio.emit(event, data)
        except Exception:
            pass


def _num(match, group=1, default=10):
    try:
        return int(match.group(group))
    except Exception:
        return default


def _fuzzy_match(name: str) -> str:
    """
    Try to find the best matching key in URL_APPS or APP_MAP
    for a partial/misheard name. Returns the matched key or original name.
    Examples: 'lm' → 'lms', 'cuim' → 'cuims', 'geeks for' → 'geeks for geeks'
    """
    n = name.lower().strip()
    all_keys = list(apps.URL_APPS.keys()) + list(apps.APP_MAP.keys())

    # 1. Exact match
    if n in apps.URL_APPS or n in apps.APP_MAP:
        return n

    # 2. Starts-with match (longest wins)
    starts = [k for k in all_keys if k.startswith(n) or n.startswith(k)]
    if starts:
        return max(starts, key=len)

    # 3. Contains match
    contains = [k for k in all_keys if n in k or k in n]
    if contains:
        return max(contains, key=len)

    # 4. Word overlap — count shared words
    n_words = set(n.split())
    best, best_score = n, 0
    for k in all_keys:
        k_words = set(k.split())
        score = len(n_words & k_words)
        if score > best_score:
            best_score = score
            best = k
    if best_score > 0:
        return best

    return n


def set_pending(action):
    global _pending_confirmation
    _pending_confirmation = action


def confirm_action():
    global _pending_confirmation
    action = _pending_confirmation
    _pending_confirmation = None
    if action == "shutdown":
        system.confirm_shutdown()
    elif action == "restart":
        system.confirm_restart()


def cancel_action():
    global _pending_confirmation
    _pending_confirmation = None
    speaker.speak("Understood, sir. Action cancelled.")


def _open_single(target: str):
    """Open one app/URL/folder without speaking (used in multi-open)."""
    t = _fuzzy_match(target.lower().strip())
    # Check explorer paths
    for key in explorer.PATH_MAP:
        if key in t:
            explorer.open_path(key)
            return
    import webbrowser
    if t in apps.URL_APPS:
        try:
            webbrowser.open(apps.URL_APPS[t])
        except Exception:
            pass
        return
    exe = apps.APP_MAP.get(t)
    if exe and exe.endswith(":"):
        try:
            import os
            import os as _os
            _os.startfile(exe)
        except Exception:
            pass
        return
    import subprocess
    try:
        launch = exe if exe else t
        subprocess.Popen(
            f"start {launch}", shell=True,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    except Exception:
        pass


def _close_single(target: str):
    """Close one app/URL without speaking (used in multi-close)."""
    import skills.explorer as _exp
    t = _fuzzy_match(target.lower().strip())
    if any(w in t for w in ["explorer", "file explorer", "file manager"]):
        _exp.close_explorer_windows()
        return
    if t in apps.URL_APPS:
        apps._close_url_app(t, t)
        return
    exe = apps.APP_MAP.get(t, t)
    if exe.endswith(":"):
        return
    if not exe.endswith(".exe"):
        exe = exe + ".exe"
    if exe.lower() in __import__('config').PROTECTED_PROCESSES:
        return
    try:
        import subprocess
        subprocess.call(["taskkill", "/f", "/im", exe],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def process(command: str):
    global _pending_confirmation
    cmd = command.lower().strip()

    # ══ STOP — highest priority, interrupts everything ════════
    if re.search(r"^(stop|jarvis stop|stop jarvis|shut up|be quiet|quiet|silence)$", cmd):
        speaker.stop()
        return

    _emit("user_message", {"text": command})
    _emit("status_change", {"status": "thinking"})

    # ── Confirmation flow ──────────────────────────────────────
    if _pending_confirmation:
        if any(w in cmd for w in ["yes", "confirm", "sure", "do it", "proceed"]):
            confirm_action()
        else:
            cancel_action()
        return

    # ── Time ──────────────────────────────────────────────────
    if re.search(r"\b(what.?s the time|what time is it|current time|tell me the time|time now)\b", cmd):
        info.speak_time()
        return

    # ── Date ──────────────────────────────────────────────────
    if re.search(r"\b(what.?s the date|what date|today.?s date|current date)\b", cmd):
        info.speak_date()
        return

    # ── Battery ───────────────────────────────────────────────
    if re.search(r"\b(battery|battery status|battery level|battery percentage)\b", cmd):
        info.battery_status()
        return

    # ── System stats ──────────────────────────────────────────
    if re.search(r"\b(cpu|ram|memory|system stats|system status|processor)\b", cmd):
        info.system_stats()
        return

    # ── Screenshot ────────────────────────────────────────────
    if re.search(r"\b(screenshot|take a screenshot|capture screen|take screenshot)\b", cmd):
        screenshot.take_screenshot()
        return

    # ── Lock ──────────────────────────────────────────────────
    if re.search(r"\b(lock screen|lock computer|lock the screen|lock the computer)\b", cmd):
        system.lock_screen()
        return

    # ── Sleep ─────────────────────────────────────────────────
    if re.search(r"\b(sleep|hibernate|sleep mode|put to sleep)\b", cmd):
        system.sleep_pc()
        return

    # ── Shutdown / Restart ────────────────────────────────────
    if re.search(r"\b(shutdown|shut down|power off|turn off computer)\b", cmd):
        system.shutdown_pc()
        return
    if re.search(r"\b(restart|reboot|restart computer)\b", cmd):
        system.restart_pc()
        return

    # ── WiFi ──────────────────────────────────────────────────
    if re.search(r"\b(turn on wi.?fi|enable wi.?fi|wi.?fi on|connect wi.?fi)\b", cmd):
        system.wifi_on()
        return
    if re.search(r"\b(turn off wi.?fi|disable wi.?fi|wi.?fi off|disconnect wi.?fi)\b", cmd):
        system.wifi_off()
        return

    # ── Hotspot ───────────────────────────────────────────────
    if re.search(r"\b(turn on hotspot|enable hotspot|start hotspot|hotspot on)\b", cmd):
        system.hotspot_on()
        return
    if re.search(r"\b(turn off hotspot|disable hotspot|stop hotspot|hotspot off)\b", cmd):
        system.hotspot_off()
        return

    # ── Bluetooth ─────────────────────────────────────────────
    if re.search(r"\b(bluetooth on|enable bluetooth|turn on bluetooth|connect bluetooth)\b", cmd):
        system.bluetooth_on()
        return
    if re.search(r"\b(bluetooth off|disable bluetooth|turn off bluetooth|disconnect bluetooth)\b", cmd):
        system.bluetooth_off()
        return

    # ── Airplane mode ─────────────────────────────────────────
    if re.search(r"\b(airplane mode on|enable airplane|flight mode on|turn on airplane)\b", cmd):
        system.airplane_mode_on()
        return
    if re.search(r"\b(airplane mode off|disable airplane|flight mode off|turn off airplane)\b", cmd):
        system.airplane_mode_off()
        return

    # ── Night light ───────────────────────────────────────────
    if re.search(r"\b(night light on|enable night light|turn on night light|night mode on)\b", cmd):
        system.night_light_on()
        return
    if re.search(r"\b(night light off|disable night light|turn off night light|night mode off)\b", cmd):
        system.night_light_off()
        return

    # ── Battery saver ─────────────────────────────────────────
    if re.search(r"\b(battery saver on|enable battery saver|turn on battery saver|power saver on)\b", cmd):
        system.battery_saver_on()
        return
    if re.search(r"\b(battery saver off|disable battery saver|turn off battery saver|power saver off)\b", cmd):
        system.battery_saver_off()
        return

    # ── Settings / Task Manager ───────────────────────────────
    if re.search(r"\b(open settings|windows settings|system settings)\b", cmd):
        system.open_settings()
        return
    if re.search(r"\b(open task manager|task manager|taskmgr)\b", cmd):
        system.open_task_manager()
        return

    # ── Mute / Unmute ─────────────────────────────────────────
    if re.search(r"\b(mute|mute audio|mute sound|mute the volume)\b", cmd):
        volume.mute()
        return
    if re.search(r"\b(unmute|unmute audio|restore sound|unmute the volume)\b", cmd):
        volume.unmute()
        return

    # ── Volume — all natural phrasings ────────────────────────
    # "set volume to 50" / "set volume at 50" / "volume to 50" / "volume 50"
    # "set the volume to 50 percent" / "volume of 50 percent"
    # "decrease volume to 30" / "increase volume to 80"
    m = re.search(
        r"(?:set\s+(?:the\s+)?volume\s+(?:to|at|of)|volume\s+(?:to|at|of|level))\s+(\d+)\s*(?:percent|%)?",
        cmd)
    if m:
        volume.set_volume(int(m.group(1)))
        return

    m = re.search(r"\bvolume\s+(\d+)\s*(?:percent|%)?", cmd)
    if m:
        volume.set_volume(int(m.group(1)))
        return

    # "increase/raise/turn up volume [by N] [to N]"
    m = re.search(r"(?:increase|raise|turn up|boost)\s+(?:the\s+)?volume\s+(?:by\s+)?(\d+)", cmd)
    if m:
        volume.increase_volume(int(m.group(1)))
        return
    m = re.search(r"(?:increase|raise|turn up|boost)\s+(?:the\s+)?volume", cmd)
    if m:
        volume.increase_volume(10)
        return

    # "decrease/lower/turn down/reduce volume [by N] [to N]"
    m = re.search(r"(?:decrease|lower|turn down|reduce|drop)\s+(?:the\s+)?volume\s+(?:by\s+)?(\d+)", cmd)
    if m:
        volume.decrease_volume(int(m.group(1)))
        return
    # "decrease volume to 30" — set absolute
    m = re.search(r"(?:decrease|lower|turn down|reduce|drop)\s+(?:the\s+)?volume\s+to\s+(\d+)", cmd)
    if m:
        volume.set_volume(int(m.group(1)))
        return
    m = re.search(r"(?:decrease|lower|turn down|reduce|drop)\s+(?:the\s+)?volume", cmd)
    if m:
        volume.decrease_volume(10)
        return

    # ── Brightness — all natural phrasings ────────────────────
    m = re.search(
        r"(?:set\s+(?:the\s+)?brightness\s+(?:to|at|of)|brightness\s+(?:to|at|of|level))\s+(\d+)\s*(?:percent|%)?",
        cmd)
    if m:
        brightness.set_brightness(int(m.group(1)))
        return

    m = re.search(r"\bbrightness\s+(\d+)\s*(?:percent|%)?", cmd)
    if m:
        brightness.set_brightness(int(m.group(1)))
        return

    m = re.search(r"(?:increase|raise|turn up|boost)\s+(?:the\s+)?brightness\s+(?:by\s+)?(\d+)", cmd)
    if m:
        brightness.increase_brightness(int(m.group(1)))
        return
    m = re.search(r"(?:increase|raise|turn up|boost)\s+(?:the\s+)?brightness", cmd)
    if m:
        brightness.increase_brightness(10)
        return

    m = re.search(r"(?:decrease|lower|turn down|reduce|dim|drop)\s+(?:the\s+)?brightness\s+(?:by\s+)?(\d+)", cmd)
    if m:
        brightness.decrease_brightness(int(m.group(1)))
        return
    m = re.search(r"(?:decrease|lower|turn down|reduce|dim|drop)\s+(?:the\s+)?brightness\s+to\s+(\d+)", cmd)
    if m:
        brightness.set_brightness(int(m.group(1)))
        return
    m = re.search(r"(?:decrease|lower|turn down|reduce|dim|drop)\s+(?:the\s+)?brightness", cmd)
    if m:
        brightness.decrease_brightness(10)
        return

    # ── Window: minimize all ──────────────────────────────────
    if re.search(r"\b(minimize all|show desktop|hide all windows|desktop)\b", cmd):
        wc.minimize_all_windows()
        return

    # ── Window: minimize specific ─────────────────────────────
    m = re.search(r"\bminimize\s+(.+)", cmd)
    if m:
        wc.minimize_window(m.group(1).strip())
        return

    # ── Window: maximize ──────────────────────────────────────
    m = re.search(r"\bmaximize\s+(.+)", cmd)
    if m:
        wc.maximize_window(m.group(1).strip())
        return

    # ── Window: restore ───────────────────────────────────────
    m = re.search(r"\brestore\s+(.+)", cmd)
    if m:
        wc.restore_window(m.group(1).strip())
        return

    # ── Tabs ──────────────────────────────────────────────────
    if re.search(r"\b(next tab|switch tab|tab next)\b", cmd):
        wc.switch_tab_next()
        return
    if re.search(r"\b(previous tab|prev tab|tab back|tab previous)\b", cmd):
        wc.switch_tab_prev()
        return
    m = re.search(r"(?:switch to |go to |open )?tab\s+(\d+)", cmd)
    if m:
        wc.switch_tab_number(int(m.group(1)))
        return
    if re.search(r"\bnew tab\b", cmd):
        wc.new_tab()
        return
    if re.search(r"\bclose tab\b", cmd):
        wc.close_tab()
        return

    # ── Create folder ─────────────────────────────────────────
    m = re.search(r"(?:create|make|new)\s+folder\s+(.+)", cmd)
    if m:
        explorer.create_folder(m.group(1).strip())
        return

    # ── List folder ───────────────────────────────────────────
    m = re.search(r"(?:list|show|what.?s in)\s+(?:folder\s+)?(.+)", cmd)
    if m and ("folder" in cmd or any(k in cmd for k in explorer.PATH_MAP)):
        explorer.list_folder(m.group(1).strip())
        return

    # ── Open file explorer / named folder ─────────────────────
    if re.search(r"\b(open file explorer|open explorer|file explorer)\b", cmd):
        for key in explorer.PATH_MAP:
            if key in cmd:
                explorer.open_path(key)
                return
        explorer.open_path(None)
        return

    for key in explorer.PATH_MAP:
        if re.search(r"\bopen\s+" + re.escape(key) + r"\b", cmd):
            explorer.open_path(key)
            return

    # ── Open arbitrary folder path ────────────────────────────
    m = re.search(r"open folder\s+(.+)", cmd)
    if m:
        explorer.open_folder(m.group(1).strip())
        return

    # ── Close app — supports multiple targets ─────────────────
    m = re.search(r"\b(?:close|kill|exit|quit)\s+(.+)", cmd)
    if m:
        raw = m.group(1).strip()
        parts = re.split(r"\s+and\s+|\s*,\s*|\s*&\s*|\s+also\s+|\s+as well as\s+", raw)
        parts = [p.strip() for p in parts if p.strip()]
        _FILLERS = {"me","please","now","up","the","a","an","both","all","together"}
        parts = [p for p in parts if p.lower() not in _FILLERS]
        if len(parts) > 1:
            names = ", ".join(parts)
            speaker.speak(f"Closing {names}, sir.")
            for part in parts:
                _close_single(part)
        else:
            target = parts[0] if parts else raw
            matched = _fuzzy_match(target)
            apps.close_app(matched)
        return

    # ── Open app / URL — supports multiple targets at once ────
    m = re.search(r"\b(?:open|launch|start|run)\s+(.+)", cmd)
    if m:
        raw = m.group(1).strip()

        # Split on common separators: "and", "," , "&", "also"
        parts = re.split(r"\s+and\s+|\s*,\s*|\s*&\s*|\s+also\s+|\s+as well as\s+", raw)
        parts = [p.strip() for p in parts if p.strip()]

        # Filter out filler words that aren't app names
        _FILLERS = {"me", "please", "now", "up", "the", "a", "an", "both", "all", "together", "simultaneously"}
        parts = [p for p in parts if p.lower() not in _FILLERS]

        if len(parts) > 1:
            names = ", ".join(parts)
            speaker.speak(f"Opening {names} for you, sir.")
            for part in parts:
                _open_single(part)
        else:
            target = parts[0] if parts else raw
            matched = _fuzzy_match(target)
            for key in explorer.PATH_MAP:
                if key in matched:
                    explorer.open_path(key)
                    return
            apps.open_app(matched)
        return

    # ── Fallback: Groq LLM ────────────────────────────────────
    reply = brain.ask_groq(command)
    speaker.speak(reply)
