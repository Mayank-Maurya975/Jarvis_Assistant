###############################################
# FILE: core/voice.py
# PURPOSE: Google Assistant-style always-on listening.
#          Uses PyAudio directly for continuous VAD (Voice Activity Detection).
#          Mic stays open permanently — no open/close overhead.
#          Detects speech start/end precisely, sends to Google SR instantly.
# DEPENDENCIES: SpeechRecognition, pyaudio, config.py, core/speaker.py
# CONNECTED TO: main.py starts this thread, core/intent.py receives commands
###############################################

import threading
import random
import time
import struct
import math
import pyaudio
import speech_recognition as sr
from config import WAKE_RESPONSES
import core.speaker as speaker
import core.intent as intent

# ── Audio config ───────────────────────────────────────────────
RATE        = 16000   # 16kHz — optimal for speech recognition
CHUNK       = 512     # ~32ms per chunk at 16kHz
FORMAT      = pyaudio.paInt16
CHANNELS    = 1

# ── VAD thresholds ─────────────────────────────────────────────
SILENCE_THRESHOLD   = 300    # RMS below this = silence (calibrated at start)
SPEECH_THRESHOLD    = 2.0    # multiplier above silence = speech detected
MIN_SPEECH_CHUNKS   = 2      # min chunks of speech before recording starts
SILENCE_CHUNKS      = 15     # chunks of silence after speech = end of utterance (~480ms)
MAX_RECORD_SECONDS  = 12     # max recording length

# ── State ──────────────────────────────────────────────────────
_awake          = False
_last_cmd_time  = 0.0
AWAKE_TIMEOUT   = 45
WAKE_WORDS  = ["jarvis", "hello jarvis", "hey jarvis", "ok jarvis", "hi jarvis",
               "davis", "travis", "service", "services", "jar vis", "jar-vis",
               "hey jarvis", "yo jarvis", "jarvis wake up"]
STOP_WORDS  = ["stop", "jarvis stop", "stop jarvis", "shut up", "be quiet", "pause", "cancel"]

# ── Mishearing corrections ─────────────────────────────────────
CORRECTIONS = {
    # Sites
    "element": "lms",   "elements": "lms",  "alms": "lms",
    "elms": "lms",      "l m s": "lms",     "l.m.s": "lms",
    "kwims": "cuims",   "q ims": "cuims",   "q.i.m.s": "cuims",
    "lead code": "leetcode",  "light code": "leetcode", "lee code": "leetcode",
    "code chef": "codechef",  "code check": "codechef",
    "india vix": "indiabix",  "india fix": "indiabix", "india bix": "indiabix",
    "geeks for": "geeks for geeks",
    # Apps
    "vs cold": "vs code",     "the code": "vs code",   "be code": "vs code",
    "power by": "power bi",   "power buy": "power bi", "power bee": "power bi",
    "what's up": "whatsapp",  "what sap": "whatsapp",  "what's app": "whatsapp",
    "wi fi": "wifi",          "wi-fi": "wifi",          "why fi": "wifi",
    "hot spot": "hotspot",    "hot-spot": "hotspot",
    "spot if i": "spotify",   "spot a fly": "spotify",
    "this cord": "discord",   "disc cord": "discord",
    "braid": "brave",         "brave browser": "brave",
    "note pad": "notepad",    "note-pad": "notepad",
    "calculate": "calculator","calculater": "calculator",
    "you tube": "youtube",    "u tube": "youtube",
    "git hub": "github",      "get hub": "github",
    "what's app": "whatsapp",
    # Commands
    "open up": "open",        "launch up": "launch",
    "turn on the": "turn on", "turn off the": "turn off",
    "set the volume": "set volume", "set the brightness": "set brightness",
}


def _correct(text: str) -> str:
    t = text.lower().strip()
    for wrong, right in CORRECTIONS.items():
        if wrong in t:
            t = t.replace(wrong, right)
    return t


def _rms(data: bytes) -> float:
    """Calculate RMS energy of audio chunk."""
    count = len(data) // 2
    if count == 0:
        return 0.0
    shorts = struct.unpack(f"{count}h", data)
    sum_sq = sum(s * s for s in shorts)
    return math.sqrt(sum_sq / count)


def _emit(event, data):
    if speaker._socketio:
        try:
            speaker._socketio.emit(event, data)
        except Exception:
            pass


def _wait_speaking():
    while speaker.is_speaking or not speaker._speak_queue.empty():
        time.sleep(0.05)
    time.sleep(0.2)


def _recognize_audio(audio_data: bytes) -> str:
    """Convert raw PCM bytes to text via Google SR with multiple fallbacks."""
    recognizer = sr.Recognizer()
    audio = sr.AudioData(audio_data, RATE, 2)
    # Try languages in order — en-IN first for Indian accent
    for lang in ["en-IN", "en-US", "en-GB"]:
        try:
            result = recognizer.recognize_google(audio, language=lang)
            return result.lower().strip()
        except sr.UnknownValueError:
            break  # clear audio but unrecognized — don't retry other langs
        except sr.RequestError:
            continue  # network issue — try next
    return ""


def _calibrate_silence(stream) -> float:
    """Sample ambient noise for 2s using 95th percentile for robust threshold."""
    print("[Voice] Calibrating ambient noise...")
    samples = []
    for _ in range(int(RATE / CHUNK * 2.0)):
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            samples.append(_rms(data))
        except Exception:
            pass
    if not samples:
        return SILENCE_THRESHOLD
    samples.sort()
    p95 = samples[int(len(samples) * 0.95)]
    threshold = max(p95 * 2.2, 180)
    threshold = min(threshold, 1500)
    print(f"[Voice] Ambient p95 RMS: {p95:.0f} → Speech threshold: {threshold:.0f}")
    return threshold


def _voice_loop():
    global _awake, _last_cmd_time

    pa = pyaudio.PyAudio()

    # Open mic stream once — stays open forever
    try:
        stream = pa.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )
    except Exception as e:
        print(f"[Voice] Cannot open mic: {e}")
        _emit("mic_error", {"message": "Microphone not found. Text-only mode."})
        pa.terminate()
        return

    # Calibrate once
    silence_rms = _calibrate_silence(stream)
    speech_rms  = silence_rms * SPEECH_THRESHOLD
    print(f"[Voice] Ready. Listening...")

    # VAD state machine
    recording       = False
    frames          = []
    speech_count    = 0
    silence_count   = 0

    while True:
        # ── Don't listen while JARVIS is speaking ──────────────
        if speaker.is_speaking or not speaker._speak_queue.empty():
            _wait_speaking()
            # Flush mic buffer after speaking to avoid echo
            try:
                for _ in range(int(RATE / CHUNK * 0.5)):
                    stream.read(CHUNK, exception_on_overflow=False)
            except Exception:
                pass
            continue

        # ── Read one chunk ─────────────────────────────────────
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
        except Exception as e:
            print(f"[Voice] Read error: {e}")
            time.sleep(0.1)
            continue

        rms = _rms(data)
        is_speech = rms > speech_rms

        if not recording:
            if is_speech:
                speech_count += 1
                if speech_count >= MIN_SPEECH_CHUNKS:
                    # Speech confirmed — start recording
                    recording = True
                    silence_count = 0
                    frames = [data]
                    print(f"[Voice] Speech detected (RMS:{rms:.0f})")
            else:
                speech_count = max(0, speech_count - 1)

        else:
            frames.append(data)

            if is_speech:
                silence_count = 0
            else:
                silence_count += 1

            # Check max length
            max_chunks = int(RATE / CHUNK * MAX_RECORD_SECONDS)
            if silence_count >= SILENCE_CHUNKS or len(frames) >= max_chunks:
                # End of utterance — process
                recording = False
                speech_count = 0
                silence_count = 0

                audio_bytes = b"".join(frames)
                frames = []

                # Process in background thread
                threading.Thread(
                    target=_process_audio,
                    args=(audio_bytes,),
                    daemon=True
                ).start()


def _process_audio(audio_bytes: bytes):
    """Recognize audio and route to wake/command handler."""
    global _awake, _last_cmd_time

    raw = _recognize_audio(audio_bytes)
    if not raw:
        return

    text = _correct(raw)
    if raw != text:
        print(f"[Voice] '{raw}' → corrected → '{text}'")
    else:
        print(f"[Voice] Recognized: '{text}'")

    is_wake = any(w in text for w in WAKE_WORDS)
    is_stop = any(w in text for w in STOP_WORDS)

    if not _awake:
        if is_wake:
            _awake = True
            _last_cmd_time = time.time()
            _emit("status_change", {"status": "awake"})
            speaker.speak(random.choice(WAKE_RESPONSES))
            _wait_speaking()
    else:
        # Check timeout
        if time.time() - _last_cmd_time >= AWAKE_TIMEOUT:
            _awake = False
            _emit("status_change", {"status": "sleeping"})
            speaker.speak("Going to sleep, sir. Say Jarvis to wake me.")
            _wait_speaking()
            return

        if is_wake:
            # Re-wake: stop current speech, acknowledge
            speaker.stop()
            _last_cmd_time = time.time()
            speaker.speak(random.choice(WAKE_RESPONSES))
            _wait_speaking()
        elif is_stop:
            speaker.stop()
        else:
            _last_cmd_time = time.time()
            _emit("user_message", {"text": text})
            threading.Thread(
                target=_run_cmd, args=(text,), daemon=True
            ).start()
            _wait_speaking()


def _run_cmd(text):
    intent.process(text)
    _wait_speaking()


def _status_loop():
    """Periodically sync sleeping/awake status to UI."""
    last = None
    while True:
        # Also check idle timeout here
        if _awake and _last_cmd_time > 0:
            import time as _t
            if _t.time() - _last_cmd_time >= AWAKE_TIMEOUT:
                globals()['_awake'] = False
                _emit("status_change", {"status": "sleeping"})
                speaker.speak("Going to sleep, sir. Say Jarvis to wake me.")
                last = "sleeping"
                continue

        status = "awake" if _awake else "sleeping"
        if status != last:
            _emit("status_change", {"status": status})
            last = status
        import time as _t
        _t.sleep(0.5)


def start():
    threading.Thread(target=_voice_loop, daemon=True, name="Voice-VAD").start()
    threading.Thread(target=_status_loop, daemon=True, name="Voice-Status").start()
    print("[Voice] Always-on VAD listener started.")


def wake():
    global _awake, _last_cmd_time
    _awake = True
    _last_cmd_time = time.time()
    _emit("status_change", {"status": "awake"})


def sleep():
    global _awake
    _awake = False
    _emit("status_change", {"status": "sleeping"})
