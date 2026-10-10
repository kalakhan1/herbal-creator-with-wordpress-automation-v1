"""CSV export with Rank Math + 10 keyword types + stock + pros/cons."""
import csv
import logging
from pathlib import Path
from typing import List, Dict
from config import Config

log = logging.getLogger(__name__)

PRODUCT_COLS = [
    "ID", "Type", "SKU", "Name", "Published", "Is featured?", "Visibility in catalog",
    "Short description", "Description", "Tax status", "Tax class",
    "In stock?", "Stock", "Manage stock?", "Stock status",
    "Regular price", "Sale price",
    "Categories", "Tags", "Shipping class", "Images", "Position",
    "Attribute 1 name", "Attribute 1 value(s)", "Attribute 1 visible", "Attribute 1 global",
    "Attribute 2 name", "Attribute 2 value(s)", "Attribute 2 visible", "Attribute 2 global",
    "Slug",
    "Meta: rank_math_focus_keyword",
    "Meta: rank_math_title",
    "Meta: rank_math_description",
    # 10 keyword types (audit trail)
    "Meta: _khs_primary_keyword",
    "Meta: _khs_short_tail",
    "Meta: _khs_long_tail",
    "Meta: _khs_navigational",
    "Meta: _khs_informational",
    "Meta: _khs_transactional",
    "Meta: _khs_commercial",
    "Meta: _khs_secondary",
    "Meta: _khs_semantic",
    # Pros/Cons
    "Meta: _khs_pros",
    "Meta: _khs_cons",
]

POST_COLS = [
    "post_title", "post_name", "post_content", "post_excerpt",
    "post_status", "post_type", "post_author",
    "post_category", "post_tags",
    "Images",
    "Meta: rank_math_focus_keyword",
    "Meta: rank_math_title",
    "Meta: rank_math_description",
    "Meta: _khs_primary_keyword",
    "Meta: _khs_short_tail",
    "Meta: _khs_long_tail",
    "Meta: _khs_navigational",
    "Meta: _khs_informational",
    "Meta: _khs_transactional",
    "Meta: _khs_commercial",
    "Meta: _khs_secondary",
    "Meta: _khs_semantic",
    "Meta: _khs_pros",
    "Meta: _khs_cons",
]


def _parse_attrs(attrs: str, max_cols: int = 2):
    if not attrs: return []
    out = []
    for chunk in attrs.split(";"):
        chunk = chunk.strip()
        if "=" in chunk:
            k, v = chunk.split("=", 1)
            out.append((k.strip(), v.strip()))
        elif chunk:
            out.append(("Attribute", chunk))
    return out[:max_cols]


def _strategy_from_json(js: str) -> dict:
    import json
    if not js: return {}
    try: return json.loads(js)
    except Exception: return {}


def export_products(products: List[Dict], filename: str, include_images: bool) -> Path:
    out = Config.OUTPUT_DIR / filename
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PRODUCT_COLS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for i, p in enumerate(products, 1):
            attrs = _parse_attrs(p.get("batch_attributes") or "")
            a1 = attrs[0] if len(attrs) >= 1 else ("", "")
            a2 = attrs[1] if len(attrs) >= 2 else ("", "")
            strat = _strategy_from_json(p.get("keyword_strategy_json") or "")

            w.writerow({
                "ID": p["id"],
                "Type": "simple",
                "SKU": p.get("sku") or f"KHS-{p['id']:04d}",
                "Name": p["name"],
                "Published": 1,
                "Is featured?": 0,
                "Visibility in catalog": "visible",
                "Short description": p.get("product_excerpt", ""),
                "Description": p.get("product_content", ""),
                "Tax status": "taxable", "Tax class": "",
                "In stock?": 1,
                "Stock": Config.DEFAULT_STOCK,
                "Manage stock?": 1 if Config.MANAGE_STOCK else 0,
                "Stock status": "instock",
                "Regular price": "",
                "Sale price": "",
                "Categories": p.get("batch_category") or "Herbal Products",
                "Tags": p.get("batch_tags") or "herbal, pakistan",
                "Shipping class": "",
                "Images": p.get("image", "") if include_images else "",
                "Position": i,
                "Attribute 1 name": a1[0],
                "Attribute 1 value(s)": a1[1],
                "Attribute 1 visible": 1 if a1[0] else 0,
                "Attribute 1 global": 0,
                "Attribute 2 name": a2[0],
                "Attribute 2 value(s)": a2[1],
                "Attribute 2 visible": 1 if a2[0] else 0,
                "Attribute 2 global": 0,
                "Slug": p["slug"],
                "Meta: rank_math_focus_keyword": p.get("focus_keyword", ""),
                "Meta: rank_math_title": p.get("seo_title", ""),
                "Meta: rank_math_description": p.get("meta_description", ""),
                "Meta: _khs_primary_keyword": strat.get("primary_keyword", ""),
                "Meta: _khs_short_tail": strat.get("short_tail", ""),
                "Meta: _khs_long_tail": strat.get("long_tail", ""),
                "Meta: _khs_navigational": strat.get("navigational", ""),
                "Meta: _khs_informational": strat.get("informational", ""),
                "Meta: _khs_transactional": strat.get("transactional", ""),
                "Meta: _khs_commercial": strat.get("commercial", ""),
                "Meta: _khs_secondary": strat.get("secondary_keywords", ""),
                "Meta: _khs_semantic": strat.get("semantic_keywords", ""),
                "Meta: _khs_pros": p.get("pros_json", ""),
                "Meta: _khs_cons": p.get("cons_json", ""),
            })
    log.info(f"Exported {len(products)} products → {out}")
    return out


def export_posts(posts: List[Dict], filename: str, include_images: bool = False) -> Path:
    out = Config.OUTPUT_DIR / filename
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=POST_COLS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for p in posts:
            if not p.get("content_html"): continue
            images = p.get("images_json") or p.get("image") or ""
            strat = _strategy_from_json(p.get("keyword_strategy_json") or "")
            w.writerow({
                "post_title": p["title"],
                "post_name": p["slug"],
                "post_content": p.get("content_html", ""),
                "post_excerpt": p.get("excerpt", ""),
                "post_status": "draft",
                "post_type": "post", "post_author": 1,
                "post_category": p.get("batch_category") or "Herbal Guides",
                "post_tags": p.get("batch_tags") or "herbal, pakistan",
                "Images": images if include_images else "",
                "Meta: rank_math_focus_keyword": p.get("focus_keyword", ""),
                "Meta: rank_math_title": p.get("seo_title", ""),
                "Meta: rank_math_description": p.get("meta_description", ""),
                "Meta: _khs_primary_keyword": strat.get("primary_keyword", ""),
                "Meta: _khs_short_tail": strat.get("short_tail", ""),
                "Meta: _khs_long_tail": strat.get("long_tail", ""),
                "Meta: _khs_navigational": strat.get("navigational", ""),
                "Meta: _khs_informational": strat.get("informational", ""),
                "Meta: _khs_transactional": strat.get("transactional", ""),
                "Meta: _khs_commercial": strat.get("commercial", ""),
                "Meta: _khs_secondary": strat.get("secondary_keywords", ""),
                "Meta: _khs_semantic": strat.get("semantic_keywords", ""),
                "Meta: _khs_pros": p.get("pros_json", ""),
                "Meta: _khs_cons": p.get("cons_json", ""),
            })
    log.info(f"Exported posts → {out}")
    return out


def export_manifest(products: List[Dict], posts: List[Dict],
                    filename: str = "image_manifest.csv") -> Path:
    out = Config.OUTPUT_DIR / filename
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(["type", "name", "slug", "filename", "alt", "filter", "status"])
        for p in products:
            w.writerow(["product", p["name"], p["slug"],
                        p.get("image", ""), p.get("image_alt", ""),
                        p.get("image_filter", "none"),
                        "assigned" if p.get("image") else "missing"])
        for p in posts:
            w.writerow(["post", p["title"], p["slug"],
                        p.get("image", ""), p.get("image_alt", ""),
                        p.get("image_filter", "none"),
                        "assigned" if p.get("image") else "missing"])
    return out