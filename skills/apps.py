###############################################
# FILE: skills/apps.py
# PURPOSE: Opens and closes any application on Windows.
#          Extended APP_MAP covers all common apps + URLs.
#          Dynamic URL handling — any website can be opened/closed by name.
#          Uses taskkill safely with protected process check.
# DEPENDENCIES: subprocess, os, webbrowser, config.PROTECTED_PROCESSES, core/speaker.py
# CONNECTED TO: core/intent.py routes open/close commands here
###############################################

import os
import subprocess
import webbrowser
import re as _re
import core.speaker as speaker
from config import PROTECTED_PROCESSES
import skills.explorer as explorer

# ── URL_APPS: name → full URL ──────────────────────────────────
# Add any website here — JARVIS will open and close it by name
URL_APPS = {
    # Social / General
    "youtube":          "https://youtube.com",
    "gmail":            "https://gmail.com",
    "google":           "https://google.com",
    "instagram":        "https://instagram.com",
    "twitter":          "https://twitter.com",
    "x":                "https://x.com",
    "facebook":         "https://facebook.com",
    "whatsapp web":     "https://web.whatsapp.com",
    "linkedin":         "https://linkedin.com",
    "reddit":           "https://reddit.com",
    "netflix":          "https://netflix.com",
    "amazon":           "https://amazon.com",
    "amazon prime":     "https://primevideo.com",
    "prime video":      "https://primevideo.com",
    "hotstar":          "https://hotstar.com",
    "disney":           "https://hotstar.com",
    "spotify web":      "https://open.spotify.com",
    "pinterest":        "https://pinterest.com",
    "snapchat":         "https://snapchat.com",
    "telegram web":     "https://web.telegram.org",

    # Productivity / Tools
    "figma":            "https://figma.com",
    "notion":           "https://notion.so",
    "chatgpt":          "https://chatgpt.com",
    "maps":             "https://maps.google.com",
    "google maps":      "https://maps.google.com",
    "github":           "https://github.com",
    "google drive":     "https://drive.google.com",
    "google docs":      "https://docs.google.com",
    "google sheets":    "https://sheets.google.com",
    "google slides":    "https://slides.google.com",
    "google calendar":  "https://calendar.google.com",
    "google meet":      "https://meet.google.com",
    "zoom web":         "https://zoom.us",
    "canva":            "https://canva.com",
    "trello":           "https://trello.com",
    "slack web":        "https://slack.com",
    "dropbox":          "https://dropbox.com",
    "onedrive web":     "https://onedrive.live.com",

    # Outlook / Mail
    "outlook":          "https://outlook.cloud.microsoft/mail/inbox/id/AAQkADZmMjNmYmY4LWNkZTUtNDFiZi1iNGJkLWYyZjEzYmM2ZWJiNAAQAA3GdVXVZFNDl8iHGU%2B7cQ8%3D",
    "outlook web":      "https://outlook.cloud.microsoft/mail/inbox/id/AAQkADZmMjNmYmY4LWNkZTUtNDFiZi1iNGJkLWYyZjEzYmM2ZWJiNAAQAA3GdVXVZFNDl8iHGU%2B7cQ8%3D",
    "outlook mail":     "https://outlook.cloud.microsoft/mail/inbox/id/AAQkADZmMjNmYmY4LWNkZTUtNDFiZi1iNGJkLWYyZjEzYmM2ZWJiNAAQAA3GdVXVZFNDl8iHGU%2B7cQ8%3D",
    "mail":             "https://outlook.cloud.microsoft/mail/inbox/id/AAQkADZmMjNmYmY4LWNkZTUtNDFiZi1iNGJkLWYyZjEzYmM2ZWJiNAAQAA3GdVXVZFNDl8iHGU%2B7cQ8%3D",

    # College portals
    "cuims":            "https://students.cuchd.in/Login.aspx?identifier1=JSt5qqbQXb6auAjKCgkfW2TMPALrIPALiI3FTuB9c5zJt4jz+Vy0uCvv1yqdFEjJ&identifier2=6B5xQScPQrRDT5gL5Q4/CXjh1dfx1BVhI4ndv6V8Ivk=",
    "cu ims":           "https://students.cuchd.in/Login.aspx?identifier1=JSt5qqbQXb6auAjKCgkfW2TMPALrIPALiI3FTuB9c5zJt4jz+Vy0uCvv1yqdFEjJ&identifier2=6B5xQScPQrRDT5gL5Q4/CXjh1dfx1BVhI4ndv6V8Ivk=",
    "student portal":   "https://students.cuchd.in/Login.aspx?identifier1=JSt5qqbQXb6auAjKCgkfW2TMPALrIPALiI3FTuB9c5zJt4jz+Vy0uCvv1yqdFEjJ&identifier2=6B5xQScPQrRDT5gL5Q4/CXjh1dfx1BVhI4ndv6V8Ivk=",
    "lms":              "https://lms.cuchd.in/",
    "learning management": "https://lms.cuchd.in/",
    "chandigarh university": "https://lms.cuchd.in/",

    # Coding / Dev
    "leetcode":         "https://leetcode.com",
    "leet code":        "https://leetcode.com",
    "codechef":         "https://codechef.com",
    "code chef":        "https://codechef.com",
    "codeforces":       "https://codeforces.com",
    "hackerrank":       "https://hackerrank.com",
    "hacker rank":      "https://hackerrank.com",
    "geeksforgeeks":    "https://geeksforgeeks.org",
    "geeks for geeks":  "https://geeksforgeeks.org",
    "gfg":              "https://geeksforgeeks.org",
    "indiabix":         "https://indiabix.com",
    "india bix":        "https://indiabix.com",
    "w3schools":        "https://w3schools.com",
    "stackoverflow":    "https://stackoverflow.com",
    "stack overflow":   "https://stackoverflow.com",
    "mdn":              "https://developer.mozilla.org",
    "npm":              "https://npmjs.com",
    "pypi":             "https://pypi.org",
    "replit":           "https://replit.com",
    "codepen":          "https://codepen.io",
    "vercel":           "https://vercel.com",
    "netlify":          "https://netlify.com",
    "heroku":           "https://heroku.com",

    # News / Info
    "wikipedia":        "https://wikipedia.org",
    "bbc":              "https://bbc.com",
    "cnn":              "https://cnn.com",
    "times of india":   "https://timesofindia.com",
    "ndtv":             "https://ndtv.com",

    # Shopping
    "flipkart":         "https://flipkart.com",
    "myntra":           "https://myntra.com",
    "meesho":           "https://meesho.com",
    "swiggy":           "https://swiggy.com",
    "zomato":           "https://zomato.com",
}

# ── TITLE_KEYWORDS: what appears in browser tab title for each site ──
# Used by _close_url_app to find the right window
TITLE_KEYWORDS = {
    "youtube":          ["youtube"],
    "gmail":            ["gmail", "google mail", "inbox"],
    "google":           ["google"],
    "instagram":        ["instagram"],
    "twitter":          ["twitter", "x.com"],
    "x":                ["x.com", "twitter"],
    "facebook":         ["facebook"],
    "whatsapp web":     ["whatsapp"],
    "linkedin":         ["linkedin"],
    "reddit":           ["reddit"],
    "netflix":          ["netflix"],
    "amazon":           ["amazon"],
    "amazon prime":     ["prime video"],
    "prime video":      ["prime video"],
    "hotstar":          ["hotstar", "disney"],
    "figma":            ["figma"],
    "notion":           ["notion"],
    "chatgpt":          ["chatgpt", "chat.openai"],
    "maps":             ["google maps"],
    "google maps":      ["google maps"],
    "github":           ["github"],
    "google drive":     ["google drive", "my drive"],
    "google docs":      ["google docs"],
    "google sheets":    ["google sheets"],
    "canva":            ["canva"],
    "trello":           ["trello"],
    "outlook":          ["outlook", "inbox"],
    "outlook web":      ["outlook", "inbox"],
    "outlook mail":     ["outlook", "inbox"],
    "mail":             ["outlook", "inbox"],
    "cuims":            ["cuchd", "cuims", "chandigarh university"],
    "cu ims":           ["cuchd", "cuims"],
    "student portal":   ["cuchd", "cuims"],
    "lms":              ["lms.cuchd", "learning management"],
    "leetcode":         ["leetcode"],
    "leet code":        ["leetcode"],
    "codechef":         ["codechef"],
    "code chef":        ["codechef"],
    "codeforces":       ["codeforces"],
    "hackerrank":       ["hackerrank"],
    "hacker rank":      ["hackerrank"],
    "geeksforgeeks":    ["geeksforgeeks", "geeks for geeks"],
    "geeks for geeks":  ["geeksforgeeks"],
    "gfg":              ["geeksforgeeks"],
    "indiabix":         ["indiabix"],
    "india bix":        ["indiabix"],
    "w3schools":        ["w3schools"],
    "stackoverflow":    ["stack overflow"],
    "stack overflow":   ["stack overflow"],
    "wikipedia":        ["wikipedia"],
    "flipkart":         ["flipkart"],
    "swiggy":           ["swiggy"],
    "zomato":           ["zomato"],
    "spotify web":      ["spotify"],
}

APP_MAP = {
    # Browsers
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "brave": "brave",
    "brave browser": "brave",
    "opera": "opera",
    # Office
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "paint": "mspaint",
    "word": "winword",
    "ms word": "winword",
    "microsoft word": "winword",
    "excel": "excel",
    "ms excel": "excel",
    "microsoft excel": "excel",
    "powerpoint": "powerpnt",
    "ms powerpoint": "powerpnt",
    "microsoft powerpoint": "powerpnt",
    "onenote": "onenote",
    "outlook": "outlook",
    "ms outlook": "outlook",
    "access": "msaccess",
    "publisher": "mspub",
    # Media
    "vlc": "vlc",
    "spotify": "spotify",
    "windows media player": "wmplayer",
    "media player": "wmplayer",
    "photos": "ms-photos:",
    "3d paint": "paint3d",
    "paint 3d": "paint3d",
    # Communication
    "discord": "discord",
    "whatsapp": "whatsapp",
    "telegram": "telegram",
    "teams": "teams",
    "ms teams": "teams",
    "microsoft teams": "teams",
    "zoom": "zoom",
    "skype": "skype",
    "slack": "slack",
    # Dev tools
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "visual studio": "devenv",
    "cmd": "cmd",
    "command prompt": "cmd",
    "powershell": "powershell",
    "git desktop": "__GITHUB_DESKTOP__",
    "github desktop": "__GITHUB_DESKTOP__",
    "postman": "postman",
    "android studio": "studio64",
    "pycharm": "pycharm64",
    "intellij": "idea64",
    # System
    "task manager": "taskmgr",
    "taskmgr": "taskmgr",
    "snipping tool": "snippingtool",
    "snip": "snippingtool",
    "file explorer": "explorer",
    "explorer": "explorer",
    "file manager": "explorer",
    "control panel": "control",
    "camera": "microsoft.windows.camera:",
    "settings": "ms-settings:",
    "store": "ms-windows-store:",
    "xbox": "xbox:",
    "clock": "ms-clock:",
    "sticky notes": "stikynot",
    "notepad++": "notepad++",
    "winrar": "winrar",
    "7zip": "7zfm",
    "7-zip": "7zfm",
    # Other
    "focusflow": "focusflow",
    "obs": "obs64",
    "obs studio": "obs64",
    "audacity": "audacity",
    "gimp": "gimp",
    "blender": "blender",
    "steam": "steam",
    "epic games": "epicgameslauncher",
    # Power tools
    "power bi": "PBIDesktop",
    "powerbi": "PBIDesktop",
    "power bi desktop": "PBIDesktop",
    "power automate": "ms-powerautomate:",
    "virtualbox": "virtualbox",
    "virtual box": "virtualbox",
    "oracle virtualbox": "virtualbox",
    # Microsoft Store & Settings (protocol)
    "microsoft store": "ms-windows-store:",
    "windows store": "ms-windows-store:",
    "store": "ms-windows-store:",
    "settings": "ms-settings:",
    "open settings": "ms-settings:",
    "windows settings": "ms-settings:",
    # WhatsApp (UWP — use shell:AppsFolder)
    "whatsapp": "__WHATSAPP__",
    # More common apps
    "anydesk": "anydesk",
    "teamviewer": "teamviewer",
    "winzip": "winzip64",
    "ccleaner": "ccleaner",
    "malwarebytes": "mbam",
    "avast": "avastui",
    "zoom": "zoom",
    "skype": "skype",
    "slack": "slack",
    "notion app": "notion",
    "figma app": "figma",
    "adobe reader": "acrord32",
    "pdf reader": "acrord32",
    "acrobat": "acrobat",
    "photoshop": "photoshop",
    "illustrator": "illustrator",
    "premiere": "premiere",
    "after effects": "afterfx",
    "lightroom": "lightroom",
    "autocad": "acad",
    "matlab": "matlab",
    "r studio": "rstudio",
    "rstudio": "rstudio",
    "jupyter": "__JUPYTER__",
    "anaconda": "anaconda-navigator",
    "filezilla": "filezilla",
    "putty": "putty",
    "winscp": "winscp",
    "wireshark": "wireshark",
    "xampp": "xampp-control",
    "wamp": "wampmanager",
    "mysql workbench": "mysqlworkbench",
    "mongodb compass": "mongodbcompass",
    "dbeaver": "dbeaver",
    "insomnia": "insomnia",
    "docker": "docker desktop",
    "docker desktop": "docker desktop",
    "unity": "unity hub",
    "unreal engine": "unrealengine",
    "epic games launcher": "epicgameslauncher",
    "origin": "origin",
    "battle.net": "battle.net",
    "twitch": "twitch",
    "handbrake": "handbrake",
    "kdenlive": "kdenlive",
    "davinci resolve": "resolve",
    "resolve": "resolve",
    "winamp": "winamp",
    "foobar": "foobar2000",
    "itunes": "itunes",
    "groove music": "ms-zune-music:",
    "movies and tv": "ms-zune-video:",
    "xbox game bar": "ms-gamebar:",
    "snip and sketch": "ms-screensketch:",
    "screen sketch": "ms-screensketch:",
    "voice recorder": "ms-callrecording:",
    "alarms": "ms-clock:",
    "weather": "bingweather:",
    "news": "bingnews:",
    "maps app": "bingmaps:",
    "onenote": "onenote",
    "teams": "teams",
    "ms teams": "teams",
    "microsoft teams": "teams",
}

# Apps using ms- protocol (startfile)
PROTOCOL_APPS = {"ms-photos:", "ms-windows-store:", "xbox:", "ms-clock:", "ms-settings:"}


def open_app(name: str):
    name_lower = name.lower().strip()

    # Direct URL passed
    if _is_url(name_lower):
        speaker.speak("Opening that website for you, sir.")
        try:
            webbrowser.open(name.strip())
        except Exception:
            speaker.speak("I could not open that URL, sir.")
        return

    # Known URL apps
    if name_lower in URL_APPS:
        speaker.speak(f"Opening {name} for you, sir.")
        try:
            webbrowser.open(URL_APPS[name_lower])
        except Exception:
            speaker.speak(f"I could not open {name}, sir.")
        return

    # Explorer
    if name_lower in ("file explorer", "explorer", "file manager", "files"):
        explorer.open_path(None)
        return

    exe = APP_MAP.get(name_lower)

    # Protocol apps
    if exe and exe.endswith(":"):
        speaker.speak(f"Opening {name} for you, sir.")
        try:
            os.startfile(exe)
        except Exception:
            subprocess.Popen(f"start {exe}", shell=True,
                             creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        return

    speaker.speak(f"Opening {name} for you, sir.")
    try:
        # Special UWP / protocol apps
        if exe == "__WHATSAPP__":
            subprocess.Popen(
                'explorer.exe shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App',
                shell=True, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        elif exe == "__GITHUB_DESKTOP__":
            subprocess.Popen(
                'explorer.exe shell:AppsFolder\\com.squirrel.GitHubDesktop.GitHubDesktop',
                shell=True, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        elif exe == "__JUPYTER__":
            subprocess.Popen("jupyter notebook", shell=True,
                             creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        elif exe == "ms-powerautomate:":
            subprocess.Popen(
                'explorer.exe shell:AppsFolder\\Microsoft.PowerAutomateDesktop_8wekyb3d8bbwe!PAD.Console',
                shell=True, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            launch = exe if exe else name
            subprocess.Popen(f"start {launch}", shell=True,
                             creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    except Exception:
        try:
            webbrowser.open(_name_to_url(name))
        except Exception:
            speaker.speak(f"I could not open {name}, sir.")


def _close_url_app(name: str, url_keyword: str):
    """Close a browser tab/window by finding it via window title matching."""
    import time
    import pyautogui

    BLACKLIST = ["localhost", "127.0.0.1", "jarvis"]

    # Get keywords from TITLE_KEYWORDS, fallback to the name itself
    keywords = TITLE_KEYWORDS.get(url_keyword.lower(), [url_keyword.lower()])

    try:
        import pygetwindow as gw
        matched_win = None

        for win in gw.getAllWindows():
            if not win.title:
                continue
            title_low = win.title.lower()
            if any(bl in title_low for bl in BLACKLIST):
                continue
            if any(kw in title_low for kw in keywords):
                matched_win = win
                break

        if matched_win:
            try:
                matched_win.activate()
                time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'w')
                return
            except Exception as e:
                print(f"[Apps] Window activate error: {e}")

        speaker.speak(f"I could not find an open {name} window, sir.")

    except Exception as e:
        print(f"[Apps] URL close error: {e}")
        speaker.speak(f"I could not close {name}, sir.")


def _is_url(text: str) -> bool:
    """Check if text looks like a URL."""
    return bool(_re.match(r'^(https?://|www\.)\S+', text.strip()))


def _name_to_url(name: str) -> str:
    """Convert an unknown site name to a best-guess URL."""
    n = name.lower().strip()
    # Remove common filler words
    n = _re.sub(r'\b(website|site|page|web|app)\b', '', n).strip()
    n = n.replace(' ', '')
    return f"https://www.{n}.com"


def close_app(name: str):
    name_lower = name.lower().strip()

    # Direct URL
    if _is_url(name_lower):
        speaker.speak("Closing that website, sir.")
        _close_url_app(name, name_lower)
        return

    # Known URL apps
    if name_lower in URL_APPS:
        speaker.speak(f"Closing {name}, sir.")
        _close_url_app(name, name_lower)
        return

    # Unknown name — try closing as website tab first
    # (handles "close leetcode", "close indiabix" etc. even if not in URL_APPS)
    # Check if it could be a website by trying title match
    if name_lower not in APP_MAP and not any(
        w in name_lower for w in ["explorer", "file explorer", "file manager"]
    ):
        # Try to close as browser tab
        _close_url_app(name, name_lower)
        return

    # Safe explorer close
    if any(w in name_lower for w in ["explorer", "file explorer", "file manager"]):
        explorer.close_explorer_windows()
        return

    exe = APP_MAP.get(name_lower, name_lower)
    # Strip protocol suffix
    if exe.endswith(":"):
        speaker.speak(f"I cannot close {name} this way, sir.")
        return
    if not exe.endswith(".exe"):
        exe = exe + ".exe"
    exe_lower = exe.lower()

    if exe_lower in PROTECTED_PROCESSES:
        speaker.speak(f"I cannot close {name} as it is a protected system process, sir.")
        return

    speaker.speak(f"Closing {name} now, sir.")
    try:
        subprocess.call(
            ["taskkill", "/f", "/im", exe],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        speaker.speak(f"I could not close {name}, sir.")
