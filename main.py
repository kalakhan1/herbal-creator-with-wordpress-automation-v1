"""Herbal Creator — Main Flask app."""
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from config import Config
import database


def setup_logging():
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    h = logging.StreamHandler(); h.setFormatter(fmt); root.addHandler(h)
    f = RotatingFileHandler(Config.LOGS_DIR / "app.log",
                            maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    f.setFormatter(fmt); root.addHandler(f)


setup_logging()
log = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = Config.FLASK_SECRET_KEY
database.init_db()

from routes import (dashboard, products, posts, images,
                    export, wordpress, settings, logs, pages)

app.register_blueprint(dashboard.bp)
app.register_blueprint(products.bp)
app.register_blueprint(posts.bp)
app.register_blueprint(images.bp)
app.register_blueprint(export.bp)
app.register_blueprint(wordpress.bp)
app.register_blueprint(settings.bp)
app.register_blueprint(logs.bp)
app.register_blueprint(pages.bp)

if __name__ == "__main__":
    log.info("=" * 60)
    log.info(f"Herbal Creator — Store: {Config.STORE_NAME}")
    log.info(f"Open: http://127.0.0.1:{Config.FLASK_PORT}")
    log.info("=" * 60)
    app.run(host="127.0.0.1", port=Config.FLASK_PORT, debug=False, threaded=True)