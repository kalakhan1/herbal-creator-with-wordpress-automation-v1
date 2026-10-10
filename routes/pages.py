"""Built-in pages management."""
from flask import Blueprint, render_template, jsonify, request
from services import page_service

bp = Blueprint("pages", __name__)


@bp.route("/pages")
def page():
    pages = page_service.get_all_pages()
    return render_template("pages.html", active="pages", pages=pages)


@bp.route("/api/pages/list")
def list_pages():
    return jsonify(page_service.get_all_pages())


@bp.route("/api/pages/refresh", methods=["POST"])
def refresh():
    """Force re-fetch all page URLs."""
    import database
    for key in ["about", "contact", "privacy", "terms"]:
        try:
            database.cache_page(f"page_{key}", "", "")  # clear
        except Exception:
            pass
    pages = page_service.get_all_pages()
    return jsonify({"ok": True, "pages": pages})