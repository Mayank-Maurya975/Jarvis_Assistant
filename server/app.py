###############################################
# FILE: server/app.py
# PURPOSE: Flask web server with SocketIO for real-time communication
#          between Python backend and the Tailwind CSS frontend UI.
#          Exposes REST API for stats and serves the main HTML page.
# DEPENDENCIES: flask, flask_socketio, core/, skills/
# CONNECTED TO: templates/index.html connects via WebSocket
###############################################

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
from config import FLASK_PORT
import skills.info as info
import skills.volume as volume
import skills.brightness as brightness

flask_app = Flask(
    __name__,
    template_folder="../templates",
)
flask_app.config["SECRET_KEY"] = "jarvis-secret-key-2024"

socketio = SocketIO(
    flask_app,
    async_mode="threading",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)


@flask_app.route("/")
def index():
    return render_template("index.html")


@flask_app.route("/api/stats")
def api_stats():
    data = info.get_dashboard_data()
    data["volume"] = volume.get_volume()
    data["brightness"] = brightness.get_brightness()
    return jsonify(data)


@flask_app.route("/api/command", methods=["POST"])
def api_command():
    import threading
    import core.intent as intent
    body = request.get_json(silent=True) or {}
    text = body.get("text", "").strip()
    if text:
        threading.Thread(target=intent.process, args=(text,), daemon=True).start()
        return jsonify({"status": "ok"})
    return jsonify({"status": "error", "message": "No text provided"}), 400


def create_app():
    """Initialize socketio bindings and return (flask_app, socketio)."""
    import core.speaker as speaker
    import server.events as events

    speaker.set_socketio(socketio)
    events.register(socketio)
    return flask_app, socketio
