"""Posts routes — batch system + content + multi-image slots + links."""
import logging
import json as _json
from flask import Blueprint, render_template, request, jsonify
import database
from services import (text_engine, seo_service, duplicate_service,
                      internal_link_service, keyword_strategy_service)
from config import Config

bp = Blueprint("posts", __name__)
log = logging.getLogger(__name__)


def _gen(pid: int, target_words: int) -> dict:
    p = database.get_post(pid)
    if not p:
        return {"ok": False, "error": "Not found"}
    database.update_post(pid, status="GENERATING")
    try:
        raw = p.get("source_content") or ""
        if len(raw) < 80:
            database.update_post(pid, status="FAILED", error="Source too short")
            return {"ok": False, "error": "Source too short"}

        article = text_engine.generate_article(
            topic=p["title"], raw=raw, target_words=target_words,
            h1=p["title"], pid=pid)
        if not article:
            database.update_post(pid, status="FAILED", error="Generation failed")
            return {"ok": False, "error": "Generation failed"}

        wa = text_engine.build_whatsapp_button(
            topic=p["title"], kind="post", slug=p.get("slug", ""))
        article["html"] = article["html"] + "\n" + wa

        strategy = keyword_strategy_service.build_strategy(
            p["title"], article.get("keywords", []))

        dup_score = 0.0
        if Config.MEMORY_DEDUP_ENABLED:
            mem = duplicate_service.check_against_memory(
                {"content": article["html"]}, "content", "post")
            dup_score = mem.get("max_similarity", 0.0)
            if dup_score >= Config.SIMILARITY_THRESHOLD:
                database.update_post(pid, status="FAILED",
                    error=f"Too similar ({dup_score:.2f})")
                return {"ok": False, "error": "Duplicate", "similarity": dup_score}

        focus_kw = strategy["focus_keyword"]
        seo_title = seo_service.build_seo_title(p["title"], focus_kw)
        meta = seo_service.build_meta_description(p["title"])
        article["word_count"] = text_engine.word_count(article["html"])

        seo = seo_service.validate(article["html"], seo_title, meta,
                                    focus_kw, p["slug"], target_words)
        pros_cons = article.get("pros_cons", {})

        # Initialize multi-image JSON slots
        existing_images = p.get("images_json")
        if not existing_images:
            slots = [{"index": i+1, "filename": "", "alt": "", "filter": "none"}
                     for i in range(Config.POST_IMAGES_COUNT)]
            existing_images = _json.dumps(slots)

        database.update_post(
            pid, status="READY",
            content_html=article["html"],
            excerpt=(raw[:180] + "...") if len(raw) > 180 else raw,
            word_count=article["word_count"],
            pros_json=_json.dumps(pros_cons.get("pros", [])),
            cons_json=_json.dumps(pros_cons.get("cons", [])),
            seo_title=seo_title, meta_description=meta,
            focus_keyword=focus_kw,
            secondary_keywords=strategy.get("secondary_keywords", ""),
            keyword_strategy_json=_json.dumps(strategy),
            seo_score=seo["score"], duplicate_score=dup_score,
            images_json=existing_images, error="",
        )
        duplicate_service.persist_to_memory(
            "post", pid, p["slug"], p["title"], article["html"])
        return {"ok": True, "seo_score": seo["score"],
                "word_count": article["word_count"],
                "duplicate_score": dup_score}
    except Exception as e:
        log.exception(f"Post gen failed {pid}")
        database.update_post(pid, status="FAILED", error=str(e)[:200])
        return {"ok": False, "error": str(e)[:200]}


@bp.route("/posts")
def page():
    return render_template("posts.html", active="posts",
                           default_words=Config.DEFAULT_POST_WORDS,
                           categories=Config.DEFAULT_CATEGORIES,
                           post_images_count=Config.POST_IMAGES_COUNT)


@bp.route("/api/posts")
def list_posts():
    return jsonify(database.get_all_posts())


@bp.route("/api/posts/batches")
def list_batches():
    return jsonify(database.get_all_batches("post"))


@bp.route("/api/posts/batch/create", methods=["POST"])
def create_batch():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    category = (data.get("category") or "").strip()
    tags = (data.get("tags") or "").strip()
    attributes = (data.get("attributes") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "Batch name required"}), 400
    if not category:
        return jsonify({"ok": False, "error": "At least 1 category required"}), 400
    bid = database.insert_batch(name, "post", category, tags, attributes)
    return jsonify({"ok": True, "batch_id": bid})


@bp.route("/api/posts/add", methods=["POST"])
def add_post():
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    batch_id = data.get("batch_id")

    if not title:
        return jsonify({"ok": False, "error": "Title required"}), 400
    if len(content) < 100:
        return jsonify({"ok": False, "error": "Content ≥ 100 chars"}), 400

    batch = database.get_batch(batch_id) if batch_id else None
    if batch_id and not batch:
        return jsonify({"ok": False, "error": "Batch not found"}), 404

    slug = text_engine.slugify(title)
    if not slug:
        return jsonify({"ok": False, "error": "Invalid title"}), 400
    if database.get_post_by_slug(slug):
        slug = f"{slug}-{int(__import__('time').time())}"

    pid = database.insert_post(title, slug, content, batch_id=batch_id)
    if pid and batch:
        database.update_post(
            pid,
            batch_category=batch["category"],
            batch_tags=batch.get("tags", ""),
            batch_attributes=batch.get("attributes", ""),
        )
        database.increment_batch_count(batch_id, 1)

    return jsonify({"ok": True, "id": pid, "slug": slug})


@bp.route("/api/posts/generate/<int:pid>", methods=["POST"])
def generate_one(pid):
    data = request.get_json(force=True) or {}
    tw = int(data.get("target_words") or Config.DEFAULT_POST_WORDS)
    r = _gen(pid, tw)
    return jsonify(r), (200 if r.get("ok") else 500)


@bp.route("/api/posts/generate-batch", methods=["POST"])
def generate_batch():
    data = request.get_json(force=True) or {}
    limit = int(data.get("limit", 5))
    tw = int(data.get("target_words") or Config.DEFAULT_POST_WORDS)
    bid = data.get("batch_id")
    pending = database.get_all_posts("PENDING", batch_id=bid)
    if not pending:
        return jsonify({"ok": True, "processed": 0, "failed": 0})
    ok, failed = 0, 0
    for p in pending[:limit]:
        r = _gen(p["id"], tw)
        if r.get("ok"): ok += 1
        else: failed += 1
    return jsonify({"ok": True, "processed": ok, "failed": failed})


@bp.route("/api/posts/retry-failed", methods=["POST"])
def retry_failed():
    failed = database.get_all_posts("FAILED")
    for p in failed:
        database.update_post(p["id"], status="PENDING", error="")
    return jsonify({"ok": True, "reset": len(failed)})


@bp.route("/api/posts/dedup", methods=["POST"])
def dedup():
    posts = database.get_all_posts()
    items = [{"id": p["id"], "content": p.get("content_html") or ""}
             for p in posts if p.get("content_html")]
    results = duplicate_service.check_duplicates(items, "content")
    for r in results:
        database.update_post(r["id"], duplicate_score=r["max_similarity"])
    return jsonify({"ok": True, "checked": len(results)})


@bp.route("/api/posts/build-links", methods=["POST"])
def build_links():
    r = internal_link_service.build_link_map(Config.WP_BASE_URL)
    if r.get("ok"):
        internal_link_service.inject_all()
    return jsonify(r)


@bp.route("/api/posts/delete/<int:pid>", methods=["POST"])
def delete(pid):
    database.delete_post(pid)
    return jsonify({"ok": True})


@bp.route("/api/posts/clear", methods=["POST"])
def clear():
    data = request.get_json(force=True) or {}
    database.clear_posts(batch_id=data.get("batch_id"))
    return jsonify({"ok": True})


@bp.route("/api/posts/images/<int:pid>")
def get_images(pid):
    p = database.get_post(pid)
    if not p:
        return jsonify({"ok": False, "error": "Not found"}), 404
    try:
        slots = _json.loads(p.get("images_json") or "[]")
    except Exception:
        slots = []
    return jsonify({"ok": True, "slots": slots})


@bp.route("/api/posts/images/update/<int:pid>", methods=["POST"])
def update_images(pid):
    data = request.get_json(force=True) or {}
    slots = data.get("slots", [])
    database.update_post(pid, images_json=_json.dumps(slots))
    return jsonify({"ok": True})