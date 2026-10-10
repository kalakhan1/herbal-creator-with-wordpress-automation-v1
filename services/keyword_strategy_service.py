"""
10-type keyword strategy — Google 2026 intent-based.
Only 3 types injected in content (Focus, Long-tail, Semantic).
Rest stored in CSV meta for audit trail.
"""
import re
import random
from typing import Dict, List
from config import Config


def _base(topic: str) -> str:
    return re.sub(r'\s+', ' ', (topic or "").strip().lower())


def _location() -> str:
    return Config.STORE_COUNTRY or "Pakistan"


def build_strategy(topic: str, keywords_hint: List[str] = None) -> Dict[str, str]:
    """
    Build a 10-type keyword strategy for a topic.
    Returns dict with all 10 keyword types + placement map.
    """
    base = _base(topic)
    loc = _location()
    store = Config.STORE_NAME

    # If keywords extracted from source are available, use them
    hint = (keywords_hint or [])[:8]

    short_tail = base
    long_tail = f"buy {base} online in {loc}"
    primary = base
    focus = base
    secondary = ", ".join(hint[1:4]) if len(hint) > 1 else f"{base} price, {base} benefits"
    navigational = f"{store} {base}"
    informational = f"what is {base} used for"
    transactional = f"buy {base} online"
    commercial = f"best {base} in {loc}"
    semantic = ", ".join(hint[4:8]) if len(hint) > 4 else f"{base} herbal, {base} traditional"

    # Placement map — where each type goes in the article
    placement = {
        "focus": "title, intro (first 100 words), one H2, conclusion",
        "primary": "title and slug",
        "short_tail": "H2 headings and image alt",
        "long_tail": "first paragraph and FAQ section",
        "navigational": f"sidebar/CTA - '{store}' brand mention",
        "informational": "body paragraphs and 'What is' section",
        "transactional": "CTA block and WhatsApp button text",
        "commercial": "comparison section if present",
        "secondary": "scattered naturally in body",
        "semantic": "body paragraphs (natural context only)",
    }

    return {
        "focus_keyword": focus,
        "primary_keyword": primary,
        "short_tail": short_tail,
        "long_tail": long_tail,
        "navigational": navigational,
        "informational": informational,
        "transactional": transactional,
        "commercial": commercial,
        "secondary_keywords": secondary,
        "semantic_keywords": semantic,
        "placement": placement,
    }


def to_csv_columns(strategy: Dict[str, str]) -> Dict[str, str]:
    """Return meta columns for CSV export."""
    return {
        "Meta: _khs_focus_keyword": strategy.get("focus_keyword", ""),
        "Meta: _khs_primary_keyword": strategy.get("primary_keyword", ""),
        "Meta: _khs_short_tail": strategy.get("short_tail", ""),
        "Meta: _khs_long_tail": strategy.get("long_tail", ""),
        "Meta: _khs_navigational": strategy.get("navigational", ""),
        "Meta: _khs_informational": strategy.get("informational", ""),
        "Meta: _khs_transactional": strategy.get("transactional", ""),
        "Meta: _khs_commercial": strategy.get("commercial", ""),
        "Meta: _khs_secondary": strategy.get("secondary_keywords", ""),
        "Meta: _khs_semantic": strategy.get("semantic_keywords", ""),
    }


def inject_focus_in_content(html: str, strategy: Dict[str, str]) -> str:
    """
    Inject 3 keyword types (Focus, Long-tail, Semantic) into content naturally.
    Focus keyword density enforced to 1.0-1.8%.
    """
    from services import text_engine
    html = text_engine.tune_keyword_density(
        html,
        strategy.get("focus_keyword", ""),
        min_pct=1.0, max_pct=1.8
    )
    return html