"""SQLite database — with batches, keyword strategies, page cache."""
import sqlite3
import logging
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from config import Config

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    content_type TEXT NOT NULL,      -- 'product' | 'post'
    category TEXT NOT NULL,
    tags TEXT,
    attributes TEXT,
    item_count INTEGER DEFAULT 0,
    notes TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    sku TEXT,
    status TEXT DEFAULT 'PENDING',
    product_content TEXT,
    product_excerpt TEXT,
    product_word_count INTEGER DEFAULT 0,
    pros_json TEXT,
    cons_json TEXT,
    seo_title TEXT,
    meta_description TEXT,
    focus_keyword TEXT,
    secondary_keywords TEXT,
    keyword_strategy_json TEXT,
    seo_score INTEGER DEFAULT 0,
    duplicate_score REAL DEFAULT 0,
    image TEXT,
    image_alt TEXT,
    image_filter TEXT,
    batch_category TEXT,
    batch_tags TEXT,
    batch_attributes TEXT,
    error TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER,
    title TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    source_content TEXT,
    content_html TEXT,
    excerpt TEXT,
    word_count INTEGER DEFAULT 0,
    pros_json TEXT,
    cons_json TEXT,
    seo_title TEXT,
    meta_description TEXT,
    focus_keyword TEXT,
    secondary_keywords TEXT,
    keyword_strategy_json TEXT,
    seo_score INTEGER DEFAULT 0,
    duplicate_score REAL DEFAULT 0,
    image TEXT,
    image_alt TEXT,
    image_filter TEXT,
    images_json TEXT,
    batch_category TEXT,
    batch_tags TEXT,
    batch_attributes TEXT,
    wp_post_id INTEGER,
    status TEXT DEFAULT 'PENDING',
    error TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS content_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_type TEXT NOT NULL,
    item_id INTEGER NOT NULL,
    slug TEXT,
    title TEXT,
    clean_text TEXT,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_memory_type ON content_memory(content_type);

CREATE TABLE IF NOT EXISTS internal_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    source_id INTEGER NOT NULL,
    target_type TEXT NOT NULL,
    target_id INTEGER NOT NULL,
    anchor TEXT,
    url TEXT,
    position TEXT DEFAULT 'end',
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_links_source ON internal_links(source_type, source_id);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS page_cache (
    key TEXT PRIMARY KEY,
    url TEXT,
    title TEXT,
    fetched_at TEXT
);
"""


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)
    log.info("DB ready")


def _migrate(conn):
    def cols(table):
        try:
            return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        except Exception:
            return []

    migrations = {
        "products": [
            ("batch_id", "INTEGER"),
            ("pros_json", "TEXT"), ("cons_json", "TEXT"),
            ("keyword_strategy_json", "TEXT"),
            ("image_filter", "TEXT"),
            ("batch_category", "TEXT"), ("batch_tags", "TEXT"),
            ("batch_attributes", "TEXT"),
        ],
        "posts": [
            ("batch_id", "INTEGER"),
            ("pros_json", "TEXT"), ("cons_json", "TEXT"),
            ("keyword_strategy_json", "TEXT"),
            ("image_filter", "TEXT"), ("images_json", "TEXT"),
            ("batch_category", "TEXT"), ("batch_tags", "TEXT"),
            ("batch_attributes", "TEXT"),
        ],
        "internal_links": [("position", "TEXT DEFAULT 'end'")],
    }

    for table, columns in migrations.items():
        existing = cols(table)
        for c, t in columns:
            if c not in existing:
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {c} {t}")
                except Exception as e:
                    log.warning(f"migrate {table}.{c}: {e}")


@contextmanager
def get_conn():
    conn = sqlite3.connect(str(Config.DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _now():
    return datetime.utcnow().isoformat()


# ==================== BATCHES ====================
def insert_batch(name: str, content_type: str, category: str,
                 tags: str = "", attributes: str = "",
                 notes: str = "") -> int:
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO batches (name,content_type,category,tags,attributes,notes,created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (name, content_type, category, tags, attributes, notes, _now()))
        return cur.lastrowid or 0


def get_batch(bid: int) -> Optional[Dict]:
    with get_conn() as c:
        r = c.execute("SELECT * FROM batches WHERE id=?", (bid,)).fetchone()
        return dict(r) if r else None


def get_all_batches(content_type: Optional[str] = None) -> List[Dict]:
    with get_conn() as c:
        if content_type:
            rows = c.execute(
                "SELECT * FROM batches WHERE content_type=? ORDER BY id DESC",
                (content_type,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM batches ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]


def update_batch(bid: int, **f):
    if not f: return
    cols = ",".join(f"{k}=?" for k in f)
    with get_conn() as c:
        c.execute(f"UPDATE batches SET {cols} WHERE id=?", list(f.values()) + [bid])


def increment_batch_count(bid: int, delta: int = 1):
    with get_conn() as c:
        c.execute("UPDATE batches SET item_count = item_count + ? WHERE id=?",
                  (delta, bid))


def delete_batch(bid: int):
    with get_conn() as c:
        c.execute("DELETE FROM batches WHERE id=?", (bid,))


# ==================== PRODUCTS ====================
def insert_product(name, slug, sku, batch_id: Optional[int] = None) -> int:
    with get_conn() as c:
        cur = c.execute(
            "INSERT OR IGNORE INTO products (name,slug,sku,batch_id,status,created_at,updated_at) "
            "VALUES (?,?,?,?, 'PENDING', ?, ?)",
            (name, slug, sku, batch_id, _now(), _now()))
        return cur.lastrowid or 0


def get_product(pid) -> Optional[Dict]:
    with get_conn() as c:
        r = c.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        return dict(r) if r else None


def get_all_products(status=None, batch_id=None) -> List[Dict]:
    with get_conn() as c:
        q = "SELECT * FROM products WHERE 1=1"
        params = []
        if status:
            q += " AND status=?"; params.append(status)
        if batch_id is not None:
            q += " AND batch_id=?"; params.append(batch_id)
        q += " ORDER BY id"
        rows = c.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def update_product(pid, **f):
    if not f: return
    f["updated_at"] = _now()
    cols = ",".join(f"{k}=?" for k in f)
    with get_conn() as c:
        c.execute(f"UPDATE products SET {cols} WHERE id=?", list(f.values()) + [pid])


def delete_product(pid):
    with get_conn() as c:
        c.execute("DELETE FROM products WHERE id=?", (pid,))
        c.execute("DELETE FROM content_memory WHERE content_type='product' AND item_id=?", (pid,))
        c.execute("DELETE FROM internal_links WHERE source_type='product' AND source_id=?", (pid,))
        c.execute("DELETE FROM internal_links WHERE target_type='product' AND target_id=?", (pid,))


def clear_products(batch_id: Optional[int] = None):
    with get_conn() as c:
        if batch_id is not None:
            c.execute("DELETE FROM products WHERE batch_id=?", (batch_id,))
        else:
            c.execute("DELETE FROM products")
        c.execute("DELETE FROM content_memory WHERE content_type='product'")
        c.execute("DELETE FROM internal_links WHERE source_type='product' OR target_type='product'")


# ==================== POSTS ====================
def insert_post(title, slug, source, batch_id: Optional[int] = None) -> int:
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO posts (title,slug,source_content,batch_id,status,created_at,updated_at) "
            "VALUES (?,?,?,?,'PENDING',?,?)",
            (title, slug, source, batch_id, _now(), _now()))
        return cur.lastrowid or 0


def get_post(pid) -> Optional[Dict]:
    with get_conn() as c:
        r = c.execute("SELECT * FROM posts WHERE id=?", (pid,)).fetchone()
        return dict(r) if r else None


def get_post_by_slug(slug) -> Optional[Dict]:
    with get_conn() as c:
        r = c.execute("SELECT * FROM posts WHERE slug=?", (slug,)).fetchone()
        return dict(r) if r else None


def get_all_posts(status=None, batch_id=None) -> List[Dict]:
    with get_conn() as c:
        q = "SELECT * FROM posts WHERE 1=1"
        params = []
        if status:
            q += " AND status=?"; params.append(status)
        if batch_id is not None:
            q += " AND batch_id=?"; params.append(batch_id)
        q += " ORDER BY id"
        rows = c.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def update_post(pid, **f):
    if not f: return
    f["updated_at"] = _now()
    cols = ",".join(f"{k}=?" for k in f)
    with get_conn() as c:
        c.execute(f"UPDATE posts SET {cols} WHERE id=?", list(f.values()) + [pid])


def delete_post(pid):
    with get_conn() as c:
        c.execute("DELETE FROM posts WHERE id=?", (pid,))
        c.execute("DELETE FROM content_memory WHERE content_type='post' AND item_id=?", (pid,))
        c.execute("DELETE FROM internal_links WHERE source_type='post' AND source_id=?", (pid,))
        c.execute("DELETE FROM internal_links WHERE target_type='post' AND target_id=?", (pid,))


def clear_posts(batch_id: Optional[int] = None):
    with get_conn() as c:
        if batch_id is not None:
            c.execute("DELETE FROM posts WHERE batch_id=?", (batch_id,))
        else:
            c.execute("DELETE FROM posts")
        c.execute("DELETE FROM content_memory WHERE content_type='post'")
        c.execute("DELETE FROM internal_links WHERE source_type='post' OR target_type='post'")


# ==================== MEMORY ====================
def save_to_memory(content_type, item_id, slug, title, clean_text):
    with get_conn() as c:
        c.execute(
            "INSERT INTO content_memory (content_type,item_id,slug,title,clean_text,created_at) "
            "VALUES (?,?,?,?,?,?)",
            (content_type, item_id, slug, title, clean_text, _now()))


def get_memory(content_type=None, limit=500) -> List[Dict]:
    with get_conn() as c:
        if content_type:
            rows = c.execute(
                "SELECT * FROM content_memory WHERE content_type=? ORDER BY id DESC LIMIT ?",
                (content_type, limit)).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM content_memory ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


# ==================== INTERNAL LINKS ====================
def clear_internal_links_for(source_type: str, source_id: int):
    with get_conn() as c:
        c.execute("DELETE FROM internal_links WHERE source_type=? AND source_id=?",
                  (source_type, source_id))


def save_internal_link(source_type, source_id, target_type, target_id,
                       anchor, url, position="end"):
    with get_conn() as c:
        c.execute(
            "INSERT INTO internal_links "
            "(source_type,source_id,target_type,target_id,anchor,url,position,created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (source_type, source_id, target_type, target_id, anchor, url, position, _now()))


def get_internal_links(source_type, source_id, position=None) -> List[Dict]:
    with get_conn() as c:
        if position:
            rows = c.execute(
                "SELECT * FROM internal_links WHERE source_type=? AND source_id=? AND position=?",
                (source_type, source_id, position)).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM internal_links WHERE source_type=? AND source_id=?",
                (source_type, source_id)).fetchall()
        return [dict(r) for r in rows]


def count_internal_links(source_type: str) -> int:
    with get_conn() as c:
        return c.execute(
            "SELECT COUNT(*) FROM internal_links WHERE source_type=?",
            (source_type,)).fetchone()[0]


# ==================== PAGE CACHE ====================
def cache_page(key: str, url: str, title: str = ""):
    with get_conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO page_cache (key,url,title,fetched_at) VALUES (?,?,?,?)",
            (key, url, title, _now()))


def get_cached_page(key: str) -> Optional[Dict]:
    with get_conn() as c:
        r = c.execute("SELECT * FROM page_cache WHERE key=?", (key,)).fetchone()
        return dict(r) if r else None


# ==================== STATS ====================
def get_stats() -> Dict[str, Any]:
    with get_conn() as c:
        s = {}
        s["products_total"] = c.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        s["products_ready"] = c.execute("SELECT COUNT(*) FROM products WHERE status='READY'").fetchone()[0]
        s["products_pending"] = c.execute("SELECT COUNT(*) FROM products WHERE status='PENDING'").fetchone()[0]
        s["products_failed"] = c.execute("SELECT COUNT(*) FROM products WHERE status='FAILED'").fetchone()[0]
        s["products_with_image"] = c.execute("SELECT COUNT(*) FROM products WHERE image IS NOT NULL AND image != ''").fetchone()[0]

        s["posts_total"] = c.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        s["posts_ready"] = c.execute("SELECT COUNT(*) FROM posts WHERE status='READY'").fetchone()[0]
        s["posts_pending"] = c.execute("SELECT COUNT(*) FROM posts WHERE status='PENDING'").fetchone()[0]
        s["posts_failed"] = c.execute("SELECT COUNT(*) FROM posts WHERE status='FAILED'").fetchone()[0]
        s["posts_with_image"] = c.execute("SELECT COUNT(*) FROM posts WHERE image IS NOT NULL AND image != ''").fetchone()[0]
        s["posts_published"] = c.execute("SELECT COUNT(*) FROM posts WHERE wp_post_id IS NOT NULL").fetchone()[0]

        s["batches_total"] = c.execute("SELECT COUNT(*) FROM batches").fetchone()[0]
        s["seo_pass"] = c.execute("SELECT COUNT(*) FROM products WHERE seo_score >= 80").fetchone()[0]
        s["seo_fail"] = c.execute("SELECT COUNT(*) FROM products WHERE seo_score > 0 AND seo_score < 80").fetchone()[0]
        s["dup_fail"] = c.execute("SELECT COUNT(*) FROM products WHERE duplicate_score >= ?",
                                   (Config.SIMILARITY_THRESHOLD,)).fetchone()[0]
        s["memory_count"] = c.execute("SELECT COUNT(*) FROM content_memory").fetchone()[0]
        s["internal_links"] = c.execute("SELECT COUNT(*) FROM internal_links").fetchone()[0]
        return s


def get_setting(key: str, default: str = "") -> str:
    with get_conn() as c:
        r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default


def set_setting(key, value):
    with get_conn() as c:
        c.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (key, value))