"""Products routes — batch system + content + memory dedup + links."""
import logging
import re
import random
from flask import Blueprint, render_template, request, jsonify
import database
from services import (text_engine, seo_service, duplicate_service,
                      internal_link_service, keyword_strategy_service)
from config import Config

bp = Blueprint("products", __name__)
log = logging.getLogger(__name__)


def _slug(text: str) -> str:
    return text_engine.slugify(text)


def _unique_source(name: str, pid: int) -> str:
    rng = random.Random(pid * 7919)
    angles = [
        "uses and benefits in traditional Pakistani herbal practice",
        "role in everyday wellness routines in Pakistan",
        "traditional Unani and herbal context in South Asia",
        "place in home remedies and daily herbal care",
        "history and traditional applications in Pakistani households",
        "sourcing, storage, and typical household usage",
        "precautions, storage, and general information",
        "herbal tradition, common questions, and modern use",
    ]
    angle = rng.choice(angles)
    sents = [
        f"{name} is a herbal product available from {Config.STORE_NAME} in {Config.STORE_COUNTRY}.",
        f"This guide focuses on the {angle}.",
        f"Traditional practitioners in {Config.STORE_COUNTRY} have discussed {name} for many years.",
        f"Households across {Config.STORE_COUNTRY} include {name} as part of their routines.",
        f"The following sections cover what {name} is and how it fits traditional herbal practice.",
        f"Always read the manufacturer's label before using {name}.",
        f"Individual experiences with {name} vary between users.",
        f"{name} is not a medicine and is not intended to diagnose, treat, cure, or prevent any disease.",
        f"Consult a qualified professional if pregnant, nursing, or taking medication.",
        f"Store {name} in a cool, dry place, away from direct sunlight.",
        f"{name} is available for delivery across {Config.STORE_COUNTRY} through standard couriers.",
        f"For specific questions about {name}, reach out to {Config.STORE_NAME} directly.",
        f"Traditional herbal practice values consistency and appropriate use of {name}.",
        f"Quality sourcing and proper storage preserve the characteristics of {name}.",
        f"Compare {name} with similar products from the same category before ordering.",
    ]
    rng.shuffle(sents)
    return " ".join(sents)


def _gen_content(pid: int, target_words: int) -> dict:
    p = database.get_product(pid)
    if not p:
        return {"ok": False, "error": "Not found"}
    database.update_product(pid, status="GENERATING")
    try:
        source = _unique_source(p["name"], pid)
        article = text_engine.generate_article(
            topic=p["name"], raw=source,
            target_words=target_words,
            h1=f"{p['name']} - Complete Guide", pid=pid)
        if not article:
            database.update_product(pid, status="FAILED", error="Generation failed")
            return {"ok": False, "error": "Generation failed"}

        # WhatsApp button
        sku = p.get("sku") or f"KHS-{p['id']:04d}"
        wa = text_engine.build_whatsapp_button(topic=p["name"], sku=sku, kind="product")
        article["html"] = article["html"] + "\n" + wa

        # Keyword strategy
        strategy = keyword_strategy_service.build_strategy(
            p["name"], article.get("keywords", []))

        # Memory dedup (optional)
        dup_score = 0.0
        if Config.MEMORY_DEDUP_ENABLED:
            mem = duplicate_service.check_against_memory(
                {"content": article["html"]}, "content", "product")
            dup_score = mem.get("max_similarity", 0.0)
            if dup_score >= Config.SIMILARITY_THRESHOLD:
                database.update_product(pid, status="FAILED",
                    error=f"Too similar ({dup_score:.2f})")
                return {"ok": False, "error": "Duplicate", "similarity": dup_score}

        focus_kw = strategy["focus_keyword"]
        seo_title = seo_service.build_seo_title(p["name"], focus_kw)
        meta = seo_service.build_meta_description(p["name"])
        article["word_count"] = text_engine.word_count(article["html"])

        seo = seo_service.validate(article["html"], seo_title, meta,
                                    focus_kw, p["slug"], target_words)

        pros_cons = article.get("pros_cons", {})
        import json as _json
        database.update_product(
            pid, status="READY",
            product_content=article["html"],
            product_excerpt=f"{p['name']} — herbal product from {Config.STORE_NAME}.",
            product_word_count=article["word_count"],
            pros_json=_json.dumps(pros_cons.get("pros", [])),
            cons_json=_json.dumps(pros_cons.get("cons", [])),
            seo_title=seo_title, meta_description=meta,
            focus_keyword=focus_kw,
            secondary_keywords=strategy.get("secondary_keywords", ""),
            keyword_strategy_json=_json.dumps(strategy),
            seo_score=seo["score"], duplicate_score=dup_score, error="",
        )
        duplicate_service.persist_to_memory(
            "product", pid, p["slug"], p["name"], article["html"])
        return {"ok": True, "seo_score": seo["score"],
                "word_count": article["word_count"],
                "duplicate_score": dup_score}
    except Exception as e:
        log.exception(f"Product gen failed {pid}")
        database.update_product(pid, status="FAILED", error=str(e)[:200])
        return {"ok": False, "error": str(e)[:200]}


# ==================== PAGES ====================
@bp.route("/products")
def page():
    return render_template("products.html", active="products",
                           default_words=Config.DEFAULT_PRODUCT_WORDS,
                           categories=Config.DEFAULT_CATEGORIES)


@bp.route("/api/products")
def list_products():
    return jsonify(database.get_all_products())


@bp.route("/api/products/batches")
def list_batches():
    return jsonify(database.get_all_batches("product"))


@bp.route("/api/products/batch/create", methods=["POST"])
def create_batch():
    """Create a new batch with category/tags/attributes."""
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    category = (data.get("category") or "").strip()
    tags = (data.get("tags") or "").strip()
    attributes = (data.get("attributes") or "").strip()

    if not name:
        return jsonify({"ok": False, "error": "Batch name required"}), 400
    if not category:
        return jsonify({"ok": False, "error": "At least 1 category required"}), 400

    bid = database.insert_batch(name, "product", category, tags, attributes)
    return jsonify({"ok": True, "batch_id": bid})


@bp.route("/api/products/add", methods=["POST"])
def add_products():
    """Add products — optionally with batch_id."""
    data = request.get_json(force=True) or {}
    raw = (data.get("names") or "").strip()
    batch_id = data.get("batch_id")

    if not raw:
        return jsonify({"ok": False, "error": "No names"}), 400

    batch = database.get_batch(batch_id) if batch_id else None
    if batch_id and not batch:
        return jsonify({"ok": False, "error": "Batch not found"}), 404

    names = [n.strip() for n in re.split(r'[,\n]+', raw) if n.strip()]
    seen, unique = set(), []
    for n in names:
        if n.lower() not in seen:
            seen.add(n.lower()); unique.append(n)

    added = 0
    for i, nm in enumerate(unique, 1):
        slug = _slug(nm)
        if not slug: continue
        pid = database.insert_product(nm, slug, f"KHS-{i:04d}", batch_id=batch_id)
        if pid:
            added += 1
            if batch:
                database.update_product(
                    pid,
                    batch_category=batch["category"],
                    batch_tags=batch.get("tags", ""),
                    batch_attributes=batch.get("attributes", ""),
                )
                database.increment_batch_count(batch_id, 1)

    return jsonify({"ok": True, "detected": len(names),
                    "unique": len(unique), "added": added})


@bp.route("/api/products/clear", methods=["POST"])
def clear():
    data = request.get_json(force=True) or {}
    bid = data.get("batch_id")
    database.clear_products(batch_id=bid)
    return jsonify({"ok": True})


@bp.route("/api/products/generate/<int:pid>", methods=["POST"])
def generate_one(pid):
    data = request.get_json(force=True) or {}
    tw = int(data.get("target_words") or Config.DEFAULT_PRODUCT_WORDS)
    r = _gen_content(pid, tw)
    return jsonify(r), (200 if r.get("ok") else 500)


@bp.route("/api/products/generate-batch", methods=["POST"])
def generate_batch():
    data = request.get_json(force=True) or {}
    limit = int(data.get("limit", 5))
    tw = int(data.get("target_words") or Config.DEFAULT_PRODUCT_WORDS)
    bid = data.get("batch_id")
    pending = database.get_all_products("PENDING", batch_id=bid)
    if not pending:
        return jsonify({"ok": True, "processed": 0, "failed": 0})
    ok, failed = 0, 0
    for p in pending[:limit]:
        r = _gen_content(p["id"], tw)
        if r.get("ok"): ok += 1
        else: failed += 1
    return jsonify({"ok": True, "processed": ok, "failed": failed})


@bp.route("/api/products/retry-failed", methods=["POST"])
def retry_failed():
    failed = database.get_all_products("FAILED")
    for p in failed:
        database.update_product(p["id"], status="PENDING", error="")
    return jsonify({"ok": True, "reset": len(failed)})


@bp.route("/api/products/dedup", methods=["POST"])
def dedup():
    products = database.get_all_products()
    items = [{"id": p["id"], "content": p.get("product_content") or ""}
             for p in products if p.get("product_content")]
    results = duplicate_service.check_duplicates(items, "content")
    for r in results:
        database.update_product(r["id"], duplicate_score=r["max_similarity"])
    return jsonify({"ok": True, "checked": len(results)})


@bp.route("/api/products/build-links", methods=["POST"])
def build_links():
    r = internal_link_service.build_link_map(Config.WP_BASE_URL)
    if r.get("ok"):
        internal_link_service.inject_all()
    return jsonify(r)


@bp.route("/api/products/delete/<int:pid>", methods=["POST"])
def delete(pid):
    database.delete_product(pid)
    return jsonify({"ok": True})