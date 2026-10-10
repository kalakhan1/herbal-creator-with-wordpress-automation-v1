"""WordPress REST API."""
import logging
import mimetypes
from pathlib import Path
from typing import Dict, Optional, Tuple
import requests
from requests.auth import HTTPBasicAuth
from config import Config

log = logging.getLogger(__name__)


def _auth():
    if not (Config.WP_BASE_URL and Config.WP_USERNAME and Config.WP_APP_PASSWORD):
        return None
    return HTTPBasicAuth(Config.WP_USERNAME, Config.WP_APP_PASSWORD)


def test_connection() -> Dict:
    if not Config.WP_BASE_URL:
        return {"ok": False, "message": "WP_BASE_URL not set"}
    auth = _auth()
    if not auth:
        return {"ok": False, "message": "WP credentials missing"}
    try:
        r = requests.get(f"{Config.WP_BASE_URL}/wp-json/wp/v2/users/me",
                         auth=auth, timeout=15)
        if r.status_code == 200:
            d = r.json()
            return {"ok": True, "message": f"Connected as {d.get('name', '?')}"}
        if r.status_code == 401:
            return {"ok": False, "message": "Auth failed (401)"}
        return {"ok": False, "message": f"HTTP {r.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "message": "Cannot reach WordPress"}
    except Exception as e:
        return {"ok": False, "message": str(e)[:150]}


def upload_media(file_path: Path, alt: str = "", title: str = "",
                 description: str = "") -> Tuple[bool, Dict]:
    auth = _auth()
    if not auth:
        return False, {"error": "WP not configured"}
    if not file_path.exists():
        return False, {"error": f"File not found: {file_path}"}

    url = f"{Config.WP_BASE_URL}/wp-json/wp/v2/media"
    mime = mimetypes.guess_type(file_path.name)[0] or "image/webp"
    try:
        with open(file_path, "rb") as f:
            r = requests.post(
                url, auth=auth,
                files={"file": (file_path.name, f, mime)},
                data={"title": title or file_path.name, "alt_text": alt,
                      "description": description, "status": "publish"},
                timeout=90,
            )
        if r.status_code in (200, 201):
            j = r.json()
            return True, {"id": j.get("id"), "url": j.get("source_url", "")}
        return False, {"error": f"HTTP {r.status_code}: {r.text[:150]}"}
    except Exception as e:
        return False, {"error": str(e)[:150]}


def create_draft(title: str, content: str, excerpt: str = "",
                 slug: str = "", featured_media: Optional[int] = None,
                 meta: Optional[Dict] = None) -> Tuple[bool, Dict]:
    auth = _auth()
    if not auth:
        return False, {"error": "WP not configured"}
    url = f"{Config.WP_BASE_URL}/wp-json/wp/v2/posts"
    payload = {
        "title": title, "content": content, "excerpt": excerpt,
        "slug": slug, "status": "draft",
    }
    if featured_media:
        payload["featured_media"] = featured_media
    if meta:
        payload["meta"] = meta
    try:
        r = requests.post(url, auth=auth, json=payload, timeout=60)
        if r.status_code in (200, 201):
            j = r.json()
            return True, {"id": j.get("id"), "url": j.get("link", "")}
        return False, {"error": f"HTTP {r.status_code}: {r.text[:150]}"}
    except Exception as e:
        return False, {"error": str(e)[:150]}


def find_post_by_slug(slug: str) -> Optional[Dict]:
    auth = _auth()
    if not auth:
        return None
    try:
        r = requests.get(
            f"{Config.WP_BASE_URL}/wp-json/wp/v2/posts",
            params={"slug": slug, "status": "any"},
            auth=auth, timeout=20,
        )
        if r.status_code == 200 and r.json():
            return r.json()[0]
    except Exception:
        pass
    return None


def update_post(post_id: int, **fields) -> Tuple[bool, Dict]:
    auth = _auth()
    if not auth:
        return False, {"error": "WP not configured"}
    try:
        r = requests.post(f"{Config.WP_BASE_URL}/wp-json/wp/v2/posts/{post_id}",
                          auth=auth, json=fields, timeout=60)
        if r.status_code == 200:
            j = r.json()
            return True, {"id": j.get("id"), "url": j.get("link", "")}
        return False, {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        return False, {"error": str(e)[:150]}