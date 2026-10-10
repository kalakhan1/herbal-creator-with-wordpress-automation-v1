"""Settings routes — full store branding + page URLs."""
from flask import Blueprint, render_template, request, jsonify
from config import Config, BASE_DIR
from services import page_service

bp = Blueprint("settings", __name__)


@bp.route("/settings")
def page():
    pages = page_service.get_all_pages()
    return render_template("settings.html", active="settings",
                           config=Config, pages=pages,
                           categories=Config.DEFAULT_CATEGORIES)


@bp.route("/api/settings/save", methods=["POST"])
def save():
    data = request.get_json(force=True) or {}
    env_path = BASE_DIR / ".env"
    existing = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()

    existing.update({k: str(v) for k, v in data.items() if v is not None})

    with open(env_path, "w", encoding="utf-8") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")

    # Apply to current process
    import os
    for k, v in data.items():
        if v is not None:
            os.environ[k] = str(v)

    Config.reload()
    return jsonify({"ok": True, "message": "Saved. Restart app to fully apply."})


@bp.route("/api/settings/test-pages", methods=["POST"])
def test_pages():
    """Try to resolve About/Contact pages."""
    result = {}
    for key in ["about", "contact", "privacy", "terms"]:
        p = page_service.resolve_page(key)
        result[key] = p or {"url": "", "found": False}
    return jsonify({"ok": True, "pages": result})


@bp.route("/api/settings/test-url", methods=["POST"])
def test_url():
    data = request.get_json(force=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"ok": False, "message": "Empty URL"})
    return jsonify(page_service.test_page_url(url))