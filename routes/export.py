"""Export CSV routes."""
from pathlib import Path
from flask import Blueprint, render_template, jsonify, send_file, abort
import database
from services import csv_service
from config import Config

bp = Blueprint("export", __name__)


@bp.route("/export")
def page():
    return render_template("export.html", active="export")


@bp.route("/api/export/products-without-images", methods=["POST"])
def p_wo():
    ps = database.get_all_products()
    path = csv_service.export_products(ps, "products_without_images.csv", False)
    return jsonify({"ok": True, "file": Path(path).name, "count": len(ps)})


@bp.route("/api/export/products-with-images", methods=["POST"])
def p_wi():
    ps = database.get_all_products()
    path = csv_service.export_products(ps, "products_with_images.csv", True)
    return jsonify({"ok": True, "file": Path(path).name, "count": len(ps)})


@bp.route("/api/export/posts-without-images", methods=["POST"])
def po_wo():
    ps = database.get_all_posts()
    path = csv_service.export_posts(ps, "posts_without_images.csv", False)
    return jsonify({"ok": True, "file": Path(path).name})


@bp.route("/api/export/posts-with-images", methods=["POST"])
def po_wi():
    ps = database.get_all_posts()
    path = csv_service.export_posts(ps, "posts_with_images.csv", True)
    return jsonify({"ok": True, "file": Path(path).name})


@bp.route("/api/export/manifest", methods=["POST"])
def manifest():
    products = database.get_all_products()
    posts = database.get_all_posts()
    path = csv_service.export_manifest(products, posts)
    return jsonify({"ok": True, "file": Path(path).name})


@bp.route("/download/<name>")
def download(name):
    safe = Path(name).name
    f = Config.OUTPUT_DIR / safe
    if not f.exists(): abort(404)
    return send_file(str(f), as_attachment=True, download_name=safe)