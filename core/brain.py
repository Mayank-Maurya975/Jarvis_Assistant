###############################################
# FILE: core/brain.py
# PURPOSE: Connects to Groq LLM API. Maintains conversation memory
#          for context-aware responses. Called when no local intent matches.
# DEPENDENCIES: groq, config.py, core/speaker.py
# CONNECTED TO: core/intent.py calls ask_groq() as fallback
###############################################

from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL, CONVERSATION_MEMORY
import core.speaker as speaker

_client = Groq(api_key=GROQ_API_KEY)

_conversation_history = []

_SYSTEM_PROMPT = (
    "You are JARVIS, Iron Man's AI assistant running on Windows. "
    "Respond in 1-2 sentences. Polite, formal British tone. "
    "No markdown. No bullet points. Plain text only. "
    "Be helpful, witty, and concise."
)


def _emit(event, data):
    if speaker._socketio:
        try:
            speaker._socketio.emit(event, data)
        except Exception:
            pass


def ask_groq(user_text: str) -> str:
    """Send user_text to Groq LLM and return the response string."""
    global _conversation_history

    _emit("status_change", {"status": "thinking"})

    _conversation_history.append({"role": "user", "content": user_text})
    if len(_conversation_history) > CONVERSATION_MEMORY * 2:
        _conversation_history = _conversation_history[-(CONVERSATION_MEMORY * 2):]

    messages = [{"role": "system", "content": _SYSTEM_PROMPT}] + _conversation_history

    try:
        response = _client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=256,
        )
        reply = response.choices[0].message.content.strip()
        _conversation_history.append({"role": "assistant", "content": reply})
        _emit("status_change", {"status": "awake"})
        return reply
    except Exception as e:
        print(f"[Brain] Groq error: {type(e).__name__}: {e}")
        _emit("status_change", {"status": "awake"})
        return "I'm having trouble connecting to my neural network, sir. Please try again."


def clear_history():
    global _conversation_history
    _conversation_history = []
