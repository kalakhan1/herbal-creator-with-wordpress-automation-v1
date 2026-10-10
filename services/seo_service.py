"""SEO validation with strict Rank Math limits."""
import re
from typing import Dict, List
from config import Config


def _strip(html: str) -> str:
    return re.sub(r'<[^>]+>', ' ', html or '')


def validate(content_html, seo_title, meta_desc, focus_kw, slug, target_words=800):
    checks = []
    text = _strip(content_html).lower()
    kw = (focus_kw or "").lower().strip()
    words = len(text.split())

    # 1. Word count
    checks.append({"name": f"Word count ≥ {target_words}",
                   "passed": words >= target_words,
                   "hint": f"Current: {words}"})

    # 2. Focus keyword in title
    checks.append({"name": "Focus keyword in SEO title",
                   "passed": bool(kw) and kw in (seo_title or "").lower(),
                   "hint": f"KW: '{focus_kw}'"})

    # 3. Focus keyword in slug
    slug_l = (slug or "").lower().replace("-", " ")
    checks.append({"name": "Focus keyword in URL slug",
                   "passed": bool(kw) and all(w in slug_l for w in kw.split()),
                   "hint": f"Slug: {slug}"})

    # 4. Focus keyword in intro
    intro = " ".join(_strip(content_html).split()[:100]).lower()
    checks.append({"name": "Focus keyword in introduction",
                   "passed": bool(kw) and kw in intro,
                   "hint": "First 100 words"})

    # 5. Density
    density = 0.0
    if words and kw:
        density = (text.count(kw) / words) * 100
    checks.append({"name": "Keyword density 0.5% – 2.5%",
                   "passed": 0.5 <= density <= 2.5,
                   "hint": f"Current: {density:.2f}%"})

    # 6. SEO title length
    tlen = len(seo_title or "")
    checks.append({"name": f"SEO title length {Config.SEO_TITLE_MIN}-{Config.SEO_TITLE_MAX} chars",
                   "passed": Config.SEO_TITLE_MIN <= tlen <= Config.SEO_TITLE_MAX,
                   "hint": f"Current: {tlen}"})

    # 7. Meta description length
    mlen = len(meta_desc or "")
    checks.append({"name": f"Meta description {Config.META_DESC_MIN}-{Config.META_DESC_MAX} chars",
                   "passed": Config.META_DESC_MIN <= mlen <= Config.META_DESC_MAX,
                   "hint": f"Current: {mlen}"})

    # 8. Slug max words
    slug_words = len((slug or "").split("-"))
    checks.append({"name": f"Slug ≤ {Config.SLUG_MAX_WORDS} words",
                   "passed": slug_words <= Config.SLUG_MAX_WORDS,
                   "hint": f"Current: {slug_words}"})

    # 9. H1
    checks.append({"name": "Has H1 heading",
                   "passed": "<h1" in (content_html or "").lower(),
                   "hint": "One H1 required"})

    # 10. H2
    h2 = (content_html or "").lower().count("<h2")
    checks.append({"name": "Has 2+ H2 headings",
                   "passed": h2 >= 2, "hint": f"Found: {h2}"})

    # 11. Internal links
    internal = content_html.count('<a href="')
    checks.append({"name": "Has internal link",
                   "passed": internal >= 1, "hint": f"Found: {internal}"})

    # 12. FAQ
    has_faq = "faq" in text or "frequently asked" in text
    checks.append({"name": "Has FAQ section",
                   "passed": has_faq, "hint": "3-5 FAQs"})

    # 13. Pros & Cons
    has_pros = "pros" in text or "advantages" in text
    checks.append({"name": "Has Pros & Cons",
                   "passed": has_pros, "hint": "Add pros/cons block"})

    # 14. Readability
    sentences = [s for s in re.split(r'[.!?]+', _strip(content_html)) if len(s.strip()) > 10]
    avg = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
    checks.append({"name": "Avg sentence < 25 words",
                   "passed": avg < 25, "hint": f"Current: {avg:.1f}"})

    passed = sum(1 for c in checks if c["passed"])
    score = int((passed / len(checks)) * 100)
    return {"score": score, "passed": passed, "total": len(checks), "checks": checks}


def build_seo_title(topic: str, kw: str = "") -> str:
    base = (topic or "").strip().title()
    store = Config.STORE_NAME
    # Priority: keyword + brand + short tail
    t = f"{base} - Uses, Benefits & Price"
    if len(t) > Config.SEO_TITLE_MAX:
        t = t[:Config.SEO_TITLE_MAX - 3].rstrip() + "..."
    if len(t) < Config.SEO_TITLE_MIN:
        t = f"{base} | {store}"
        if len(t) > Config.SEO_TITLE_MAX:
            t = t[:Config.SEO_TITLE_MAX - 3].rstrip() + "..."
    return t


def build_meta_description(topic: str) -> str:
    country = Config.STORE_COUNTRY
    store = Config.STORE_NAME
    m = (f"{topic} in {country} — traditional uses, benefits, how to use, "
         f"precautions & where to buy. Order online from {store}.")
    if len(m) > Config.META_DESC_MAX:
        m = m[:Config.META_DESC_MAX - 3].rstrip() + "..."
    if len(m) < Config.META_DESC_MIN:
        m += " Fast delivery across the country."
    return m


def pick_focus_keyword(title: str, keywords: List[str]) -> str:
    if keywords:
        return keywords[0].lower()
    return (title or "").lower().split()[0] if title else ""