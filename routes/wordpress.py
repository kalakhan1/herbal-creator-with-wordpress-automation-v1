"""WordPress push."""
import logging
from flask import Blueprint, render_template, request, jsonify
from config import Config
from services import wordpress_service
import database

bp = Blueprint("wordpress", __name__)
log = logging.getLogger(__name__)


@bp.route("/wordpress")
def page():
    return render_template("wordpress.html", active="wordpress")


@bp.route("/api/wp/test", methods=["POST"])
def test():
    return jsonify(wordpress_service.test_connection())


@bp.route("/api/wp/upload-images", methods=["POST"])
def upload_images():
    data = request.get_json(force=True) or {}
    limit = int(data.get("limit", 20))
    products = database.get_all_products()
    posts = database.get_all_posts()
    uploaded = 0
    failed = []
    for p in products[:limit]:
        if not p.get("image"): continue
        fp = Config.PRODUCT_IMG_DIR / p["image"]
        ok, res = wordpress_service.upload_media(
            fp, alt=p.get("image_alt", ""),
            title=p["name"], description=f"Product image for {p['name']}")
        if ok: uploaded += 1
        else: failed.append({"kind": "product", "id": p["id"], "err": res.get("error", "")[:100]})
    for p in posts[:limit]:
        if not p.get("image"): continue
        fp = Config.POST_IMG_DIR / p["image"]
        ok, res = wordpress_service.upload_media(
            fp, alt=p.get("image_alt", ""),
            title=p["title"], description=f"Featured image for {p['title']}")
        if ok: uploaded += 1
        else: failed.append({"kind": "post", "id": p["id"], "err": res.get("error", "")[:100]})
    return jsonify({"ok": True, "uploaded": uploaded,
                    "failed_count": len(failed), "failed": failed[:10]})


@bp.route("/api/wp/push-posts", methods=["POST"])
def push_posts():
    data = request.get_json(force=True) or {}
    limit = int(data.get("limit", 5))
    dry_run = bool(data.get("dry_run", False))
    posts = database.get_all_posts()
    ready = [p for p in posts if p.get("content_html")]
    created = updated = 0
    failed = []
    previews = []
    for p in ready[:limit]:
        if dry_run:
            previews.append({"id": p["id"], "title": p["title"],
                             "slug": p["slug"], "action": "would_create"})
            continue
        existing = wordpress_service.find_post_by_slug(p["slug"])
        meta = {
            "rank_math_focus_keyword": p.get("focus_keyword", ""),
            "rank_math_title": p.get("seo_title", ""),
            "rank_math_description": p.get("meta_description", ""),
        }
        if existing:
            ok, res = wordpress_service.update_post(
                existing["id"], title=p["title"],
                content=p["content_html"], excerpt=p.get("excerpt", ""), meta=meta)
            if ok:
                updated += 1
                database.update_post(p["id"], wp_post_id=existing["id"])
            else:
                failed.append({"id": p["id"], "err": res.get("error", "")[:100]})
        else:
            ok, res = wordpress_service.create_draft(
                title=p["title"], content=p["content_html"],
                excerpt=p.get("excerpt", ""), slug=p["slug"], meta=meta)
            if ok:
                created += 1
                database.update_post(p["id"], wp_post_id=res.get("id"))
            else:
                failed.append({"id": p["id"], "err": res.get("error", "")[:100]})
    return jsonify({"ok": True, "created": created, "updated": updated,
                    "failed_count": len(failed), "failed": failed[:10],
                    "previews": previews[:10], "dry_run": dry_run})