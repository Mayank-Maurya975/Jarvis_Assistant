###############################################
# FILE: skills/explorer.py
# PURPOSE: Controls File Explorer — opens drives, named folders, arbitrary paths.
#          Closes folder windows safely via PowerShell COM (never taskkill).
#          Also creates folders and lists contents.
# DEPENDENCIES: subprocess, os, core/speaker.py
# CONNECTED TO: core/intent.py, skills/apps.py
###############################################

import os
import subprocess
import core.speaker as speaker

PATH_MAP = {
    "c drive": "C:\\",
    "d drive": "D:\\",
    "e drive": "E:\\",
    "f drive": "F:\\",
    "downloads": os.path.expanduser("~\\Downloads"),
    "documents": os.path.expanduser("~\\Documents"),
    "desktop": os.path.expanduser("~\\Desktop"),
    "pictures": os.path.expanduser("~\\Pictures"),
    "music": os.path.expanduser("~\\Music"),
    "videos": os.path.expanduser("~\\Videos"),
    "appdata": os.path.expanduser("~\\AppData"),
    "local appdata": os.path.expanduser("~\\AppData\\Local"),
    "temp": os.path.expanduser("~\\AppData\\Local\\Temp"),
    "program files": "C:\\Program Files",
    "program files x86": "C:\\Program Files (x86)",
    "system32": "C:\\Windows\\System32",
    "windows": "C:\\Windows",
    "user folder": os.path.expanduser("~"),
    "home": os.path.expanduser("~"),
    "onedrive": os.path.expanduser("~\\OneDrive"),
    "recycle bin": "shell:RecycleBinFolder",
}


def _launch_explorer(target: str):
    try:
        if target.startswith("shell:"):
            subprocess.Popen(f"explorer {target}", shell=True,
                             creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            os.startfile(target)
    except Exception:
        try:
            subprocess.Popen(
                f'explorer "{target}"', shell=True,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        except Exception:
            speaker.speak("I could not open that location, sir.")


def open_path(location_name: str = None):
    """Open File Explorer at a named location from PATH_MAP."""
    if location_name and location_name.lower() in PATH_MAP:
        target = PATH_MAP[location_name.lower()]
        label = location_name
    else:
        target = os.path.expanduser("~")
        label = "Home"
    speaker.speak(f"Opening {label} in File Explorer, sir.")
    _launch_explorer(target)


def open_folder(folder_path: str):
    """Open any arbitrary folder path or named location."""
    # Check PATH_MAP first
    key = folder_path.lower().strip()
    if key in PATH_MAP:
        open_path(key)
        return
    # Expand user paths
    expanded = os.path.expanduser(folder_path)
    if os.path.exists(expanded):
        speaker.speak(f"Opening {folder_path}, sir.")
        _launch_explorer(expanded)
    else:
        speaker.speak(f"I could not find the folder {folder_path}, sir.")


def create_folder(folder_path: str):
    """Create a new folder at the given path."""
    try:
        expanded = os.path.expanduser(folder_path)
        os.makedirs(expanded, exist_ok=True)
        speaker.speak(f"Folder created at {folder_path}, sir.")
    except Exception as e:
        speaker.speak(f"I could not create that folder, sir.")


def list_folder(folder_path: str):
    """List contents of a folder and speak the first few items."""
    try:
        expanded = os.path.expanduser(folder_path)
        items = os.listdir(expanded)
        if not items:
            speaker.speak(f"The folder {folder_path} is empty, sir.")
            return
        preview = items[:5]
        names = ", ".join(preview)
        more = f" and {len(items) - 5} more" if len(items) > 5 else ""
        speaker.speak(f"The folder contains: {names}{more}, sir.")
    except Exception:
        speaker.speak(f"I could not list that folder, sir.")


def close_explorer_windows():
    """Close all open File Explorer folder windows via PowerShell COM."""
    ps = (
        "$shell = New-Object -ComObject Shell.Application;"
        "$shell.Windows() | ForEach-Object { $_.Quit() }"
    )
    try:
        subprocess.run(["powershell", "-Command", ps],
                       capture_output=True, timeout=10)
        speaker.speak("Closed all File Explorer windows, sir.")
    except Exception:
        try:
            import psutil
            main_pid = None
            for proc in psutil.process_iter(["pid", "name", "ppid"]):
                if proc.info["name"] and proc.info["name"].lower() == "explorer.exe":
                    try:
                        parent = psutil.Process(proc.info["ppid"])
                        if parent.name().lower() != "explorer.exe":
                            main_pid = proc.info["pid"]
                            break
                    except Exception:
                        pass
            for proc in psutil.process_iter(["pid", "name"]):
                if proc.info["name"] and proc.info["name"].lower() == "explorer.exe":
                    if proc.info["pid"] != main_pid:
                        try:
                            proc.kill()
                        except Exception:
                            pass
            speaker.speak("Closed File Explorer windows, sir.")
        except Exception:
            speaker.speak("I could not close File Explorer windows, sir.")
