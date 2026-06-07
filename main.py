###############################################
# FILE: main.py
# PURPOSE: Entry point for JARVIS. Auto-installs packages, starts Flask,
#          voice thread, and optionally creates an ngrok public tunnel.
#          Run: python main.py          (local only)
#          Run: python main.py --tunnel (public ngrok URL)
# DEPENDENCIES: Everything
# CONNECTED TO: All modules
###############################################

import subprocess
import sys
import os

# ── Auto-install missing packages ─────────────────────────────
_PACKAGES = [
    "groq", "SpeechRecognition", "pyaudio", "pyttsx3",
    "screen-brightness-control", "pycaw", "comtypes",
    "psutil", "pyautogui", "pillow", "flask", "flask-socketio", "pyngrok",
]
_IMPORT_MAP = {
    "SpeechRecognition": "speech_recognition",
    "pillow": "PIL",
    "screen-brightness-control": "screen_brightness_control",
    "flask-socketio": "flask_socketio",
    "pyngrok": "pyngrok",
}
for _pkg in _PACKAGES:
    _name = _IMPORT_MAP.get(_pkg, _pkg.replace("-", "_"))
    try:
        __import__(_name)
    except ImportError:
        print(f"[Setup] Installing {_pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", _pkg])

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import threading
import webbrowser
import time

from config import FLASK_PORT, NGROK_AUTH_TOKEN
from server.app import create_app
import core.speaker as speaker
import core.voice as voice


def _start_ngrok(port: int) -> str:
    """Start ngrok tunnel and return public URL. Returns empty string on failure."""
    try:
        from pyngrok import ngrok, conf

        # Set auth token if configured
        if NGROK_AUTH_TOKEN:
            conf.get_default().auth_token = NGROK_AUTH_TOKEN

        tunnel = ngrok.connect(port, "http")
        url = tunnel.public_url
        # Force HTTPS
        if url.startswith("http://"):
            url = "https://" + url[7:]
        return url
    except Exception as e:
        print(f"[Ngrok] Failed to start tunnel: {e}")
        print("[Ngrok] Get a free auth token at https://dashboard.ngrok.com")
        return ""


def _print_banner(local_url: str, public_url: str = ""):
    lines = [
        "╔══════════════════════════════════════════════╗",
        "║          J.A.R.V.I.S  ONLINE                ║",
        "║   Just A Rather Very Intelligent System      ║",
        "╠══════════════════════════════════════════════╣",
        f"║  Local:   {local_url:<35}║",
    ]
    if public_url:
        lines.append(f"║  Public:  {public_url:<35}║")
        lines.append("║  Share the Public URL with anyone!           ║")
    else:
        lines.append("║  Run with --tunnel for public URL            ║")
    lines += [
        "╠══════════════════════════════════════════════╣",
        "║  Say: JARVIS  to wake up                     ║",
        "╚══════════════════════════════════════════════╝",
    ]
    print("\n" + "\n".join(lines) + "\n")


def _greet(public_url: str = ""):
    time.sleep(2.5)
    msg = "Good day sir. JARVIS is now online. Say Jarvis to wake me up."
    if public_url:
        msg += " A public access link has been generated and printed in the terminal."
    speaker.speak(msg)


def main():
    use_tunnel = "--tunnel" in sys.argv or "-t" in sys.argv
    local_url = f"http://localhost:{FLASK_PORT}"
    public_url = ""

    flask_app, socketio = create_app()
    speaker.start()
    voice.start()

    # Start ngrok tunnel if requested
    if use_tunnel:
        print("[Ngrok] Starting tunnel...")
        public_url = _start_ngrok(FLASK_PORT)

    _print_banner(local_url, public_url)

    # Update SocketIO CORS to allow public URL
    if public_url:
        flask_app.config["CORS_ORIGINS"] = [local_url, public_url, "*"]

    threading.Thread(target=_greet, args=(public_url,), daemon=True).start()
    threading.Thread(target=lambda: (time.sleep(1.5), webbrowser.open(local_url)), daemon=True).start()

    socketio.run(
        flask_app,
        host="0.0.0.0",
        port=FLASK_PORT,
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )


if __name__ == "__main__":
    main()
