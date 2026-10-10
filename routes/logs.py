"""Logs."""
from flask import Blueprint, render_template, jsonify
from config import Config

bp = Blueprint("logs", __name__)


@bp.route("/logs")
def page():
    return render_template("logs.html", active="logs")


@bp.route("/api/logs")
def api_logs():
    log_file = Config.LOGS_DIR / "app.log"
    lines = []
    if log_file.exists():
        try:
            lines = log_file.read_text(encoding="utf-8").splitlines()[-300:]
        except Exception:
            lines = []
    return jsonify([{"line": l} for l in reversed(lines)])