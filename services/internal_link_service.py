"""Internal linking between products, posts, and built-in pages."""
import logging
import re
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import database
from config import Config
from services import page_service

log = logging.getLogger(__name__)


def _clean(text):
    t = re.sub(r'<[^>]+>', ' ', text or '')
    return re.sub(r'\s+', ' ', t).lower().strip()


def _sim_matrix(texts):
    valid = [i for i, t in enumerate(texts) if len(t) > 40]
    if len(valid) < 2: return None, valid
    try:
        vec = TfidfVectorizer(max_features=4000, stop_words="english")
        m = vec.fit_transform([texts[i] for i in valid])
        return cosine_similarity(m), valid
    except Exception as e:
        log.warning(f"TF-IDF failed: {e}")
        return None, valid


def _top_matches(idx_v, sim, valid, max_n, exclude_idx):
    if sim is None: return []
    row = sim[idx_v].copy()
    row[idx_v] = 0
    order = row.argsort()[::-1]
    out = []
    for o in order:
        gi = valid[int(o)]
        if gi == exclude_idx: continue
        out.append(gi)
        if len(out) >= max_n: break
    return out


def build_link_map(base_url: str = ""):
    base = (base_url or Config.WP_BASE_URL).rstrip("/")
    products = [p for p in database.get_all_products("READY") if p.get("product_content")]
    posts = [p for p in database.get_all_posts("READY") if p.get("content_html")]

    log.info(f"Building links: {len(products)} products, {len(posts)} posts")

    max_prod = Config.MID_ARTICLE_LINKS + Config.END_ARTICLE_LINKS
    mid_n = Config.MID_ARTICLE_LINKS
    end_n = Config.END_ARTICLE_LINKS

    # PRODUCTS ↔ PRODUCTS
    if len(products) >= 2:
        texts = [_clean(p.get("product_content")) for p in products]
        sim, valid = _sim_matrix(texts)
        for idx_v, gi in enumerate(valid):
            p = products[gi]
            matches = _top_matches(idx_v, sim, valid, max_prod, gi)
            database.clear_internal_links_for("product", p["id"])
            for i, j in enumerate(matches):
                tgt = products[j]
                pos = "mid" if i < mid_n else "end"
                database.save_internal_link("product", p["id"], "product",
                                            tgt["id"], tgt["name"],
                                            f"{base}/product/{tgt['slug']}/", pos)

    # POSTS ↔ PRODUCTS
    if posts and products:
        prod_texts = [_clean(p.get("product_content")) for p in products]
        post_texts = [_clean(p.get("content_html")) for p in posts]
        all_texts = prod_texts + post_texts
        sim, valid = _sim_matrix(all_texts)
        if sim is not None:
            for idx_v, gi in enumerate(valid):
                if gi < len(products): continue
                post_idx = gi - len(products)
                post = posts[post_idx]
                matches = _top_matches(idx_v, sim, valid, mid_n + 1, gi)
                prod_matches = [m for m in matches if m < len(products)]
                for i, m in enumerate(prod_matches):
                    tgt = products[m]
                    pos = "mid" if i < mid_n else "end"
                    database.save_internal_link("post", post["id"], "product",
                                                tgt["id"], tgt["name"],
                                                f"{base}/product/{tgt['slug']}/", pos)

    # POSTS ↔ POSTS
    if len(posts) >= 2:
        texts = [_clean(p.get("content_html")) for p in posts]
        sim, valid = _sim_matrix(texts)
        for idx_v, gi in enumerate(valid):
            post = posts[gi]
            matches = _top_matches(idx_v, sim, valid, end_n, gi)
            for i, j in enumerate(matches):
                tgt = posts[j]
                pos = "mid" if i < 1 else "end"
                database.save_internal_link("post", post["id"], "post",
                                            tgt["id"], tgt["title"],
                                            f"{base}/{tgt['slug']}/", pos)

    # Product ↔ About Us (built-in page)
    if Config.LINK_ABOUT_PAGE:
        about = page_service.resolve_page("about")
        if about and about.get("url"):
            for p in products:
                database.save_internal_link("product", p["id"], "page", 0,
                                            f"About {Config.STORE_NAME}",
                                            about["url"], "end")
            for p in posts:
                database.save_internal_link("post", p["id"], "page", 0,
                                            f"About {Config.STORE_NAME}",
                                            about["url"], "end")

    total = database.count_internal_links("product") + database.count_internal_links("post")
    log.info(f"Internal links built: {total}")
    return {"ok": True, "total_links": total}


def _build_mid_block(links):
    if not links: return ""
    items = " ".join(f'<a href="{l["url"]}">{l["anchor"]}</a>' for l in links)
    return (
        '<div class="khs-mid-links" style="margin:20px 0;padding:14px 18px;'
        'background:#f0f9ff;border-left:4px solid #0ea5e9;border-radius:8px;">'
        '<strong>You may also find useful:</strong> ' + items + '</div>'
    )


def _build_end_block(links):
    if not links: return ""
    items = "\n".join(f'<li><a href="{l["url"]}">{l["anchor"]}</a></li>' for l in links)
    return '\n<h2>Related Reading</h2>\n<ul>\n' + items + '\n</ul>\n'


def inject_links(content_html, source_type, source_id):
    if not content_html: return content_html
    if "<!-- khs-links-injected -->" in content_html:
        return content_html

    mid_links = database.get_internal_links(source_type, source_id, position="mid")
    end_links = database.get_internal_links(source_type, source_id, position="end")

    if not mid_links and not end_links:
        return content_html

    mid_block = _build_mid_block(mid_links)
    end_block = _build_end_block(end_links)

    if mid_block:
        h2_matches = list(re.finditer(r'</h2>', content_html))
        if len(h2_matches) >= 2:
            insert_pos = h2_matches[1].end()
            content_html = (content_html[:insert_pos] + mid_block +
                            content_html[insert_pos:])
        else:
            content_html = mid_block + content_html

    return content_html + "\n<!-- khs-links-injected -->\n" + end_block


def inject_all():
    products = database.get_all_products("READY")
    for p in products:
        new_html = inject_links(p.get("product_content") or "", "product", p["id"])
        if new_html != (p.get("product_content") or ""):
            database.update_product(p["id"], product_content=new_html)

    posts = database.get_all_posts("READY")
    for p in posts:
        new_html = inject_links(p.get("content_html") or "", "post", p["id"])
        if new_html != (p.get("content_html") or ""):
            database.update_post(p["id"], content_html=new_html)

    return {"ok": True, "products": len(products), "posts": len(posts)}