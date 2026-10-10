"""
Fetch About Us / Contact / Privacy URLs from WordPress REST API.
Manual .env priority, auto-fetch fallback, cache in DB.
"""
import logging
import requests
from typing import Optional, Dict
from requests.auth import HTTPBasicAuth
from config import Config
import database

log = logging.getLogger(__name__)


PAGE_SLUGS = {
    "about": ["about-us", "about", "who-we-are", "our-story"],
    "contact": ["contact", "contact-us", "reach-us"],
    "privacy": ["privacy-policy", "privacy"],
    "terms": ["terms", "terms-and-conditions", "terms-of-service"],
}


def _auth():
    if not (Config.WP_BASE_URL and Config.WP_USERNAME and Config.WP_APP_PASSWORD):
        return None
    return HTTPBasicAuth(Config.WP_USERNAME, Config.WP_APP_PASSWORD)


def _fetch_page_by_slugs(slugs: list) -> Optional[Dict]:
    """Try each slug until one returns a page."""
    auth = _auth()
    if not auth:
        return None
    for slug in slugs:
        try:
            r = requests.get(
                f"{Config.WP_BASE_URL}/wp-json/wp/v2/pages",
                params={"slug": slug, "status": "publish"},
                auth=auth, timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                if data:
                    page = data[0]
                    return {"url": page.get("link", ""),
                            "title": page.get("title", {}).get("rendered", slug),
                            "slug": slug}
        except Exception as e:
            log.warning(f"fetch page {slug}: {e}")
    return None


def resolve_page(key: str) -> Optional[Dict]:
    """
    Resolve a page URL.
    Priority:
      1. Manual .env field
      2. Cached DB
      3. Auto-fetch from WP REST API
    Returns {url, title, slug, source} or None.
    """
    manual_map = {
        "about": Config.STORE_ABOUT_URL,
        "contact": Config.STORE_CONTACT_URL,
        "privacy": Config.STORE_PRIVACY_URL,
        "terms": Config.STORE_TERMS_URL,
    }
    manual = manual_map.get(key, "").strip()
    if manual:
        return {"url": manual, "title": key.title(), "slug": key, "source": "manual"}

    cached = database.get_cached_page(f"page_{key}")
    if cached and cached.get("url"):
        return {"url": cached["url"], "title": cached.get("title", key.title()),
                "slug": key, "source": "cache"}

    if not Config.STORE_PAGE_AUTO_FETCH:
        return None

    slugs = PAGE_SLUGS.get(key, [key])
    result = _fetch_page_by_slugs(slugs)
    if result:
        database.cache_page(f"page_{key}", result["url"], result["title"])
        result["source"] = "auto"
        return result
    return None


def get_all_pages() -> Dict[str, Optional[Dict]]:
    return {k: resolve_page(k) for k in ["about", "contact", "privacy", "terms"]}


def test_page_url(url: str) -> Dict:
    """Check if a URL is reachable (200)."""
    if not url or not url.startswith("http"):
        return {"ok": False, "message": "Invalid URL"}
    try:
        r = requests.head(url, timeout=10, allow_redirects=True)
        return {"ok": r.status_code < 400,
                "message": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "message": str(e)[:120]}