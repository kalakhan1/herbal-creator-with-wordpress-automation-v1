"""Image manager — filters + custom size + rebuild."""
import logging
import json as _json
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, send_file, abort
from config import Config
from services import image_service
import database

bp = Blueprint("images", __name__)
log = logging.getLogger(__name__)

PAGE_SIZE = 20


@bp.route("/images")
def page():
    return render_template("images.html", active="images",
                           filters=image_service.AVAILABLE_FILTERS,
                           defaults={
                               "width": Config.IMAGE_DEFAULT_WIDTH,
                               "height": Config.IMAGE_DEFAULT_HEIGHT,
                               "mode": Config.IMAGE_DEFAULT_MODE,
                               "bg": Config.IMAGE_DEFAULT_BG,
                               "quality": Config.IMAGE_DEFAULT_QUALITY,
                               "filter": Config.IMAGE_DEFAULT_FILTER,
                           })


@bp.route("/api/images/list")
def list_images():
    page_num = max(1, int(request.args.get("page", 1)))
    kind = request.args.get("kind", "all")
    status = request.args.get("status", "all")
    slots = []
    if kind in ("all", "product"):
        for p in database.get_all_products():
            slots.append({"id": p["id"], "kind": "product",
                          "title": p["name"], "slug": p["slug"],
                          "image": p.get("image"),
                          "alt": p.get("image_alt"),
                          "filter": p.get("image_filter") or "none"})
    if kind in ("all", "post"):
        for p in database.get_all_posts():
            slots.append({"id": p["id"], "kind": "post",
                          "title": p["title"], "slug": p["slug"],
                          "image": p.get("image"),
                          "alt": p.get("image_alt"),
                          "filter": p.get("image_filter") or "none"})
    if status == "missing":
        slots = [s for s in slots if not s["image"]]
    elif status == "assigned":
        slots = [s for s in slots if s["image"]]
    total = len(slots)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page_num = min(page_num, pages)
    start = (page_num - 1) * PAGE_SIZE
    return jsonify({"page": page_num, "total_pages": pages,
                    "total_slots": total,
                    "items": slots[start:start + PAGE_SIZE]})


@bp.route("/api/images/stats")
def stats():
    products = database.get_all_products()
    posts = database.get_all_posts()
    total = len(products) + len(posts)
    assigned = (sum(1 for p in products if p.get("image")) +
                sum(1 for p in posts if p.get("image")))
    return jsonify({"total_slots": total, "assigned": assigned,
                    "missing": total - assigned})


@bp.route("/api/images/upload/<kind>/<int:pid>", methods=["POST"])
def upload(kind, pid):
    if kind not in ("product", "post"):
        return jsonify({"ok": False, "error": "Invalid kind"}), 400
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"ok": False, "error": "Empty filename"}), 400

    try:
        width = int(request.form.get("width", "0") or "0")
        height = int(request.form.get("height", "0") or "0")
    except Exception:
        width, height = 0, 0
    mode = request.form.get("mode", "fit")
    bg_color = request.form.get("bg_color", "#FFFFFF")
    quality = int(request.form.get("quality", "88") or "88")
    quality = max(60, min(95, quality))
    filter_name = request.form.get("filter", "none")
    image_index = int(request.form.get("image_index", "1") or "1")

    if kind == "product":
        obj = database.get_product(pid)
        target_dir = Config.PRODUCT_IMG_DIR
        name_key, slug_key = "name", "slug"
    else:
        obj = database.get_post(pid)
        target_dir = Config.POST_IMG_DIR
        name_key, slug_key = "title", "slug"

    if not obj:
        return jsonify({"ok": False, "error": "Not found"}), 404

    result = image_service.process_upload(
        f.read(), f.filename, obj[name_key], obj[slug_key], kind, target_dir,
        width=width, height=height, mode=mode, bg_color=bg_color,
        quality=quality, filter_name=filter_name, image_index=image_index)

    if not result.get("ok"):
        return jsonify(result), 400

    if kind == "product":
        database.update_product(pid, image=result["filename"],
                                image_alt=result["alt"], image_filter=filter_name)
    else:
        # Update post main image + slot
        try:
            slots = _json.loads(obj.get("images_json") or "[]")
        except Exception:
            slots = []
        while len(slots) < image_index:
            slots.append({"index": len(slots) + 1, "filename": "",
                          "alt": "", "filter": "none"})
        slots[image_index - 1] = {
            "index": image_index,
            "filename": result["filename"],
            "alt": result["alt"],
            "filter": filter_name,
        }
        database.update_post(pid, image=result["filename"],
                             image_alt=result["alt"],
                             image_filter=filter_name,
                             images_json=_json.dumps(slots))

    return jsonify({"ok": True, **result})


@bp.route("/api/images/remove/<kind>/<int:pid>", methods=["POST"])
def remove(kind, pid):
    data = request.get_json(force=True) or {}
    image_index = int(data.get("image_index", 1) or "1")
    if kind == "product":
        obj = database.get_product(pid)
        if obj and obj.get("image"):
            image_service.delete(obj["image"], "product")
        database.update_product(pid, image="", image_alt="", image_filter="")
    else:
        obj = database.get_post(pid)
        try:
            slots = _json.loads(obj.get("images_json") or "[]")
        except Exception:
            slots = []
        if 0 <= image_index - 1 < len(slots):
            fname = slots[image_index - 1].get("filename")
            if fname: image_service.delete(fname, "post")
            slots[image_index - 1] = {"index": image_index, "filename": "",
                                      "alt": "", "filter": "none"}
        database.update_post(pid, images_json=_json.dumps(slots))
    return jsonify({"ok": True})


@bp.route("/api/images/preview/<kind>/<int:pid>")
def preview(kind, pid):
    idx = int(request.args.get("index", "1") or "1")
    if kind == "product":
        obj = database.get_product(pid); folder = Config.PRODUCT_IMG_DIR
    else:
        obj = database.get_post(pid); folder = Config.POST_IMG_DIR
    if not obj: abort(404)
    if kind == "post" and idx > 1:
        try:
            slots = _json.loads(obj.get("images_json") or "[]")
        except Exception:
            slots = []
        if 0 <= idx - 1 < len(slots):
            fname = slots[idx - 1].get("filename")
            if fname:
                pth = folder / fname
                if pth.exists(): return send_file(str(pth), mimetype="image/webp")
        abort(404)
    fname = obj.get("image")
    if not fname: abort(404)
    pth = folder / fname
    if not pth.exists(): abort(404)
    return send_file(str(pth), mimetype="image/webp")


@bp.route("/api/images/search-term/<kind>/<int:pid>")
def search_term(kind, pid):
    if kind == "product":
        obj = database.get_product(pid)
        term = f"{obj['name']} product" if obj else "product"
    else:
        obj = database.get_post(pid)
        term = f"{obj['title']} illustration" if obj else "blog"
    return jsonify({"ok": True, "term": term})


@bp.route("/api/images/rebuild/<kind>/<int:pid>", methods=["POST"])
def rebuild(kind, pid):
    data = request.get_json(force=True) or {}
    width = int(data.get("width", 0) or 0)
    height = int(data.get("height", 0) or 0)
    mode = data.get("mode", "fit")
    bg_color = data.get("bg_color", "#FFFFFF")
    filter_name = data.get("filter", "none")
    image_index = int(data.get("image_index", 1) or "1")

    if kind == "product":
        obj = database.get_product(pid); folder = Config.PRODUCT_IMG_DIR
    else:
        obj = database.get_post(pid); folder = Config.POST_IMG_DIR
    if not obj: return jsonify({"ok": False, "error": "Not found"}), 404

    # Find which file to rebuild
    fname = obj.get("image")
    if kind == "post" and image_index > 1:
        try:
            slots = _json.loads(obj.get("images_json") or "[]")
        except Exception:
            slots = []
        if 0 <= image_index - 1 < len(slots):
            fname = slots[image_index - 1].get("filename")
    if not fname:
        return jsonify({"ok": False, "error": "No image to rebuild"}), 400

    orig = list(folder.glob(f"_{fname.rsplit('.', 1)[0]}.*"))
    if not orig:
        return jsonify({"ok": False, "error": "Original not found"}), 400

    dst = folder / fname
    ok = image_service.to_webp(orig[0], dst, width=width, height=height,
                                mode=mode, bg_color=bg_color,
                                filter_name=filter_name)
    if not ok:
        return jsonify({"ok": False, "error": "Rebuild failed"}), 500

    if kind == "product":
        database.update_product(pid, image_filter=filter_name)
    else:
        database.update_post(pid, image_filter=filter_name)
    return jsonify({"ok": True})