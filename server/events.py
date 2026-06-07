###############################################
# FILE: server/events.py
# PURPOSE: Registers all WebSocket (SocketIO) event handlers.
#          Wake button stops current speech and forces JARVIS awake.
# DEPENDENCIES: flask_socketio, core/intent.py, core/voice.py, core/speaker.py
# CONNECTED TO: server/app.py registers these handlers
###############################################

import threading
import random
import core.intent as intent
import core.voice as voice
import core.speaker as speaker
from config import WAKE_RESPONSES


def register(socketio):

    @socketio.on("connect")
    def on_connect():
        print("[Events] Client connected.")
        socketio.emit("status_change", {"status": "sleeping"})

    @socketio.on("disconnect")
    def on_disconnect():
        print("[Events] Client disconnected.")

    @socketio.on("text_command")
    def on_text_command(data):
        text = data.get("text", "").strip()
        if not text:
            return
        threading.Thread(
            target=intent.process,
            args=(text,),
            daemon=True,
        ).start()

    @socketio.on("confirm_action")
    def on_confirm():
        threading.Thread(target=intent.confirm_action, daemon=True).start()

    @socketio.on("cancel_action")
    def on_cancel():
        intent.cancel_action()

    @socketio.on("wake_jarvis")
    def on_wake():
        """Stop any current speech, wake JARVIS, speak response."""
        # Stop whatever is currently being said
        speaker.stop()
        # Small delay so stop clears queue before we add wake response
        import time
        time.sleep(0.3)
        voice.wake()
        response = random.choice(WAKE_RESPONSES)
        speaker.speak(response)

    @socketio.on("sleep_jarvis")
    def on_sleep():
        speaker.stop()
        voice.sleep()
        speaker.speak("Going to sleep, sir.")
