"""Configuration loader — no external deps. Multi-client ready."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

_env_path = BASE_DIR / ".env"
if _env_path.exists():
    try:
        for _line in _env_path.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())
    except Exception:
        pass


class Config:
    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"
    UPLOADS_DIR = BASE_DIR / "uploads"
    PRODUCT_IMG_DIR = UPLOADS_DIR / "products"
    POST_IMG_DIR = UPLOADS_DIR / "posts"
    OUTPUT_DIR = BASE_DIR / "output"
    DB_PATH = DATA_DIR / "herbal.db"

    # ---------- STORE IDENTITY (multi-client) ----------
    STORE_NAME = os.getenv("STORE_NAME", "Khan Herbal Stores")
    STORE_TAGLINE = os.getenv("STORE_TAGLINE", "Trusted Pakistani Herbal Store")
    STORE_WHATSAPP = os.getenv("STORE_WHATSAPP", "923218224219")
    STORE_WHATSAPP_DISPLAY = os.getenv("STORE_WHATSAPP_DISPLAY", "+92 321 8224219")
    STORE_COUNTRY = os.getenv("STORE_COUNTRY", "Pakistan")
    STORE_CURRENCY = os.getenv("STORE_CURRENCY", "PKR")
    STORE_ESTABLISHED = os.getenv("STORE_ESTABLISHED", "")
    STORE_ADDRESS = os.getenv("STORE_ADDRESS", "")
    STORE_EMAIL = os.getenv("STORE_EMAIL", "")

    # ---------- BUILT-IN PAGE URLS (About Us, Contact, etc.) ----------
    STORE_ABOUT_URL = os.getenv("STORE_ABOUT_URL", "").strip()
    STORE_CONTACT_URL = os.getenv("STORE_CONTACT_URL", "").strip()
    STORE_PRIVACY_URL = os.getenv("STORE_PRIVACY_URL", "").strip()
    STORE_TERMS_URL = os.getenv("STORE_TERMS_URL", "").strip()
    STORE_PAGE_AUTO_FETCH = os.getenv("STORE_PAGE_AUTO_FETCH", "true").lower() == "true"

    # ---------- WordPress ----------
    WP_BASE_URL = os.getenv("WP_BASE_URL", "").rstrip("/")
    WP_USERNAME = os.getenv("WP_USERNAME", "")
    WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")

    # ---------- Content ----------
    DEFAULT_PRODUCT_WORDS = int(os.getenv("DEFAULT_PRODUCT_WORDS", "800"))
    DEFAULT_POST_WORDS = int(os.getenv("DEFAULT_POST_WORDS", "1000"))
    MIN_SEO_SCORE = int(os.getenv("MIN_SEO_SCORE", "80"))
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.82"))
    MEMORY_DEDUP_ENABLED = os.getenv("MEMORY_DEDUP_ENABLED", "false").lower() == "true"

    # ---------- WooCommerce Stock ----------
    DEFAULT_STOCK = int(os.getenv("DEFAULT_STOCK", "100"))
    MANAGE_STOCK = os.getenv("MANAGE_STOCK", "true").lower() == "true"
    LOW_STOCK_AMOUNT = int(os.getenv("LOW_STOCK_AMOUNT", "5"))

    # ---------- Image Defaults ----------
    IMAGE_DEFAULT_WIDTH = int(os.getenv("IMAGE_DEFAULT_WIDTH", "800"))
    IMAGE_DEFAULT_HEIGHT = int(os.getenv("IMAGE_DEFAULT_HEIGHT", "800"))
    IMAGE_DEFAULT_MODE = os.getenv("IMAGE_DEFAULT_MODE", "fit")
    IMAGE_DEFAULT_BG = os.getenv("IMAGE_DEFAULT_BG", "#FFFFFF")
    IMAGE_DEFAULT_QUALITY = int(os.getenv("IMAGE_DEFAULT_QUALITY", "88"))
    IMAGE_DEFAULT_FILTER = os.getenv("IMAGE_DEFAULT_FILTER", "none")

    # ---------- Post images ----------
    POST_IMAGES_COUNT = int(os.getenv("POST_IMAGES_COUNT", "3"))

    # ---------- Internal Linking ----------
    MID_ARTICLE_LINKS = int(os.getenv("MID_ARTICLE_LINKS", "2"))
    END_ARTICLE_LINKS = int(os.getenv("END_ARTICLE_LINKS", "3"))
    LINK_ABOUT_PAGE = os.getenv("LINK_ABOUT_PAGE", "true").lower() == "true"

    # ---------- SEO limits (Rank Math) ----------
    SEO_TITLE_MAX = int(os.getenv("SEO_TITLE_MAX", "60"))
    SEO_TITLE_MIN = int(os.getenv("SEO_TITLE_MIN", "30"))
    META_DESC_MAX = int(os.getenv("META_DESC_MAX", "160"))
    META_DESC_MIN = int(os.getenv("META_DESC_MIN", "120"))
    SLUG_MAX_WORDS = int(os.getenv("SLUG_MAX_WORDS", "5"))

    # ---------- Flask ----------
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

    # ---------- Default Product Categories (batch UI) ----------
    DEFAULT_CATEGORIES = [
        "Oils", "Syrups", "Majoon", "Khamira", "Sharbat",
        "Vinegars", "Jari Bootiyan", "Dry Fruits",
        "Seeds", "Spices", "Powders", "Custom"
    ]

    @classmethod
    def ensure_dirs(cls):
        for d in [cls.DATA_DIR, cls.LOGS_DIR, cls.UPLOADS_DIR,
                  cls.PRODUCT_IMG_DIR, cls.POST_IMG_DIR, cls.OUTPUT_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def reload(cls):
        """Re-read .env at runtime (called from Settings save)."""
        env_path = cls.BASE_DIR / ".env"
        if not env_path.exists():
            return
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()


Config.ensure_dirs()