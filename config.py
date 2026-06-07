###############################################
# FILE: config.py
# PURPOSE: Central configuration for all JARVIS settings.
#          Change API keys, wake word, voice settings here.
# DEPENDENCIES: None
# CONNECTED TO: All files import from here
###############################################

GROQ_API_KEY = "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"
GROQ_MODEL = "llama-3.3-70b-versatile"

WAKE_WORD = "hello jarvis"
WAKE_RESPONSES = [
    "Yes sir, how can I help?",
    "Online and ready, sir.",
    "At your service, sir.",
    "Good day sir, what do you need?",
]

VOICE_RATE = 175
VOICE_VOLUME = 1.0

FLASK_PORT = 8080

# ── Ngrok tunnel (optional) ────────────────────────────────────
# Get your free auth token at: https://dashboard.ngrok.com/get-started/your-authtoken
# Paste it here to enable stable public URLs (otherwise ngrok works without it but with limits)
NGROK_AUTH_TOKEN = "3C2XMwMjd8b36udidXQHwUBcWky_2DQn3csVvmtT19cga12Qy"

CONVERSATION_MEMORY = 10

SCREENSHOT_DIR = "~/Desktop"

PROTECTED_PROCESSES = [
    "explorer.exe", "winlogon.exe", "csrss.exe", "svchost.exe",
    "lsass.exe", "smss.exe", "wininit.exe", "services.exe",
    "shellexperiencehost.exe", "startmenuexperiencehost.exe",
    "dwm.exe", "taskhostw.exe",
]
