###############################################
# FILE: core/speaker.py
# PURPOSE: Text-to-speech using Windows PowerShell System.Speech SAPI.
#          Supports stop() to interrupt speech mid-sentence.
#          Emits SocketIO events for UI waveform animation.
# DEPENDENCIES: subprocess, threading, queue, os, config.py
# CONNECTED TO: All skill files call speak(), brain.py calls speak()
###############################################

import subprocess
import threading
import queue
import os
import tempfile
from config import VOICE_RATE, VOICE_VOLUME

_socketio = None
_speak_queue = queue.Queue()
is_speaking = False
_current_proc = None   # track running powershell TTS process for kill

_SAPI_RATE = 1
_SAPI_VOLUME = 100


def set_socketio(sio):
    global _socketio
    _socketio = sio


def _emit(event, data):
    if _socketio:
        try:
            _socketio.emit(event, data)
        except Exception:
            pass


def _powershell_speak(text: str):
    global _current_proc
    safe_text = text.replace("'", "''")
    ps_content = f"""Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = {_SAPI_RATE}
$synth.Volume = {_SAPI_VOLUME}
$synth.Speak('{safe_text}')
"""
    tmp = tempfile.NamedTemporaryFile(
        mode='w', suffix='.ps1', delete=False, encoding='utf-8'
    )
    tmp.write(ps_content)
    tmp.close()
    try:
        proc = subprocess.Popen(
            ["powershell", "-ExecutionPolicy", "Bypass",
             "-WindowStyle", "Hidden", "-NonInteractive", "-File", tmp.name],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        _current_proc = proc
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except Exception:
            pass
    except Exception as e:
        print(f"[Speaker] TTS error: {e}")
    finally:
        _current_proc = None
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def _worker():
    global is_speaking
    while True:
        text = _speak_queue.get()
        if text is None:
            break
        is_speaking = True
        _emit("speaking_start", {})
        _powershell_speak(text)
        is_speaking = False
        _emit("speaking_end", {})
        _speak_queue.task_done()


def speak(text: str):
    print(f"[JARVIS] {text}")
    _emit("jarvis_message", {"text": text})
    _speak_queue.put(text)


def speak_async(text: str):
    speak(text)


def stop():
    """Immediately stop speaking and clear the queue."""
    global is_speaking, _current_proc
    # Drain the queue
    while not _speak_queue.empty():
        try:
            _speak_queue.get_nowait()
            _speak_queue.task_done()
        except Exception:
            break
    # Kill current TTS subprocess
    if _current_proc:
        try:
            _current_proc.kill()
        except Exception:
            pass
        _current_proc = None
    is_speaking = False
    _emit("speaking_end", {})
    # Short acknowledgement
    _speak_queue.put("Yes sir.")


def start():
    t = threading.Thread(target=_worker, daemon=True, name="TTS-Worker")
    t.start()
    print("[Speaker] TTS worker started (PowerShell SAPI).")
