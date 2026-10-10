"""
Pure-Python text engine. No AI required.
All store references come from Config (multi-client ready).
"""
import hashlib
import logging
import random
import re
from typing import List, Dict, Optional
from urllib.parse import quote

try:
    import nltk
    from nltk.tokenize import sent_tokenize
    from nltk.corpus import stopwords
    for _pkg in ["punkt", "punkt_tab", "stopwords"]:
        try: nltk.data.find(f"tokenizers/{_pkg}")
        except LookupError: nltk.download(_pkg, quiet=True)
    NLTK_OK = True
except Exception:
    NLTK_OK = False

try:
    import textstat
    TEXTSTAT_OK = True
except Exception:
    TEXTSTAT_OK = False

from config import Config

log = logging.getLogger(__name__)

_STOP = set()
if NLTK_OK:
    try: _STOP = set(stopwords.words("english"))
    except Exception: pass

SYN = {
    "important": ["significant", "notable", "key"],
    "benefit": ["advantage", "value", "gain"],
    "benefits": ["advantages", "values", "gains"],
    "use": ["application", "usage", "purpose"],
    "uses": ["applications", "purposes"],
    "herbal": ["natural", "plant-based", "botanical"],
    "traditional": ["classic", "conventional", "customary"],
    "natural": ["organic", "pure", "unrefined"],
    "product": ["item", "preparation", "formulation"],
    "products": ["items", "preparations"],
    "quality": ["standard", "grade", "caliber"],
    "good": ["excellent", "positive", "favorable"],
    "many": ["several", "numerous", "multiple"],
    "help": ["assist", "support"],
    "helps": ["assists", "supports"],
    "also": ["additionally", "furthermore", "moreover"],
    "very": ["highly", "extremely", "particularly"],
    "make": ["create", "produce", "prepare"],
    "people": ["individuals", "persons", "users"],
    "common": ["frequent", "typical", "widespread"],
    "used": ["utilized", "applied"],
    "often": ["frequently", "regularly"],
    "because": ["since", "as"],
    "however": ["nevertheless", "nonetheless"],
    "example": ["instance", "illustration"],
}

TRANSITIONS = [
    "", "", "", "",
    "Additionally, ", "Moreover, ", "In addition, ",
    "Furthermore, ", "Interestingly, ", "Notably, ",
]


# ============================================================
# WHATSAPP BUTTON (uses Config — no hardcoding)
# ============================================================
def build_whatsapp_button(topic, sku="", kind="product", price="", slug=""):
    store = Config.STORE_NAME
    wa_num = Config.STORE_WHATSAPP
    wa_disp = Config.STORE_WHATSAPP_DISPLAY
    currency = Config.STORE_CURRENCY

    if kind == "product":
        lines = [
            f"Assalam-o-Alaikum {store}!",
            "",
            "I want to order this product:",
            "",
            f"*Product:* {topic}",
        ]
        if sku: lines.append(f"*SKU:* {sku}")
        if price: lines.append(f"*Price:* {currency} {price}")
        lines.append("*Quantity:* 1")
        lines.append("")
        lines.append("Please confirm availability and delivery details.")
    else:
        lines = [
            f"Assalam-o-Alaikum {store}!",
            "",
            "I read your article and want to know more:",
            "",
            f"*Article:* {topic}",
        ]
        if slug: lines.append(f"*Link:* {slug}")
        lines.append("")
        lines.append("Please share related product details and pricing.")

    message = "\n".join(lines)
    wa_url = f"https://wa.me/{wa_num}?text={quote(message, safe='')}"

    return (
        '<div class="khs-wa-button" style="text-align:center;margin:32px 0;'
        'padding:22px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;">'
        '<p style="margin:0 0 14px;font-size:16px;color:#166534;font-weight:600;">'
        '&#128241; Want to order this product?</p>'
        f'<a href="{wa_url}" target="_blank" rel="noopener nofollow" '
        'style="display:inline-block;background:#25D366;color:#fff;'
        'padding:14px 34px;border-radius:8px;text-decoration:none;'
        'font-weight:bold;font-size:16px;'
        'box-shadow:0 4px 12px rgba(37,211,102,0.35);">'
        'Order on WhatsApp</a>'
        f'<p style="margin:14px 0 0;font-size:13px;color:#15803d;">'
        f'Direct WhatsApp: <strong>{wa_disp}</strong></p></div>'
    )


# ============================================================
# PROS & CONS
# ============================================================
def build_pros_cons(topic: str, pid: int = 0) -> str:
    rng = random.Random(pid * 41)
    pros_pool = [
        "Traditional herbal product with a long history in Pakistani practice",
        "Available in consistent packaging from trusted suppliers",
        "Suitable for everyday household use",
        "Easy to store in a cool, dry place",
        "Sold at reasonable pricing with fast Pakistan-wide delivery",
        "Can be ordered directly via WhatsApp for convenience",
        "Belongs to a well-known herbal category",
    ]
    cons_pool = [
        "Not a medicine — no therapeutic claims are made",
        "Individual experiences may vary",
        "Should be stored carefully to maintain quality",
        "Always read the manufacturer's label before use",
        "Consult a qualified professional if pregnant or on medication",
    ]
    rng.shuffle(pros_pool); rng.shuffle(cons_pool)
    pros = pros_pool[:3]; cons = cons_pool[:2]

    html = ['<div class="khs-pros-cons" style="display:grid;'
            'grid-template-columns:1fr 1fr;gap:16px;margin:24px 0;">']
    html.append(
        '<div style="background:#f0fdf4;border:1px solid #bbf7d0;'
        'border-radius:10px;padding:16px;">'
        '<h3 style="margin:0 0 10px;color:#166534;">&#10004; Pros</h3>'
        '<ul style="margin:0;padding-left:20px;">')
    for p in pros:
        html.append(f'<li style="margin-bottom:6px;">{p}</li>')
    html.append('</ul></div>')
    html.append(
        '<div style="background:#fef2f2;border:1px solid #fecaca;'
        'border-radius:10px;padding:16px;">'
        '<h3 style="margin:0 0 10px;color:#991b1b;">&#10006; Cons</h3>'
        '<ul style="margin:0;padding-left:20px;">')
    for c in cons:
        html.append(f'<li style="margin-bottom:6px;">{c}</li>')
    html.append('</ul></div></div>')
    return "".join(html)


def get_pros_cons_data(topic: str, pid: int = 0) -> Dict:
    rng = random.Random(pid * 41)
    pros_pool = [
        "Traditional herbal product with a long history in Pakistani practice",
        "Available in consistent packaging from trusted suppliers",
        "Suitable for everyday household use",
        "Easy to store in a cool, dry place",
        "Sold at reasonable pricing with fast Pakistan-wide delivery",
        "Can be ordered directly via WhatsApp for convenience",
        "Belongs to a well-known herbal category",
    ]
    cons_pool = [
        "Not a medicine — no therapeutic claims are made",
        "Individual experiences may vary",
        "Should be stored carefully to maintain quality",
        "Always read the manufacturer's label before use",
        "Consult a qualified professional if pregnant or on medication",
    ]
    rng.shuffle(pros_pool); rng.shuffle(cons_pool)
    return {"pros": pros_pool[:3], "cons": cons_pool[:2]}


# ============================================================
# UTILS
# ============================================================
def strip_html(html):
    if not html: return ""
    t = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    t = re.sub(r'<style[^>]*>.*?</style>', '', t, flags=re.DOTALL | re.IGNORECASE)
    t = re.sub(r'<[^>]+>', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def clean_input(raw):
    if not raw: return ""
    t = raw.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r'\n{3,}', '\n\n', t)
    return re.sub(r'[ \t]{2,}', ' ', t).strip()


def word_count(text): return len(strip_html(text).split())


def split_sentences(text):
    text = strip_html(text)
    if not text: return []
    if NLTK_OK:
        try: sents = sent_tokenize(text)
        except Exception: sents = re.split(r'(?<=[.!?])\s+', text)
    else:
        sents = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sents if len(s.strip()) > 25]


def _seed(*parts):
    h = hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:8], 16)


def replace_synonyms(sent, prob, rng):
    tokens = re.findall(r'\b[\w-]+\b|[^\w\s]+|\s+', sent)
    out = []
    for tok in tokens:
        low = tok.lower()
        if low in SYN and rng.random() < prob:
            choice = rng.choice(SYN[low])
            if tok[0].isupper(): choice = choice.capitalize()
            out.append(choice)
        else:
            out.append(tok)
    return "".join(out)


def add_transition(sent, rng):
    if not sent: return sent
    t = rng.choice(TRANSITIONS)
    if not t: return sent
    if sent.lower().startswith(("additionally","moreover","furthermore","in addition","interestingly","notably")):
        return sent
    return t + sent[0].lower() + sent[1:]


def reformulate(sent, rng):
    s = replace_synonyms(sent, 0.20, rng)
    if rng.random() < 0.15: s = add_transition(s, rng)
    return s


def extract_keywords(text, n=10):
    low = strip_html(text).lower()
    words = re.findall(r'\b[a-z][a-z\-]{3,}\b', low)
    words = [w for w in words if w not in _STOP]
    freq = {}
    for w in words: freq[w] = freq.get(w, 0) + 1
    bigrams = {}
    for i in range(len(words) - 1):
        bg = f"{words[i]} {words[i+1]}"
        bigrams[bg] = bigrams.get(bg, 0) + 1
    top_bi = [k for k, v in sorted(bigrams.items(), key=lambda x: -x[1]) if v >= 2][:4]
    top_single = [k for k, v in sorted(freq.items(), key=lambda x: -x[1])][:n]
    result = top_bi + [k for k in top_single if k not in " ".join(top_bi)]
    return result[:n]


def slugify(text, max_words=None):
    if max_words is None:
        max_words = Config.SLUG_MAX_WORDS
    t = re.sub(r'[^a-z0-9\s-]', '', (text or "").lower())
    t = re.sub(r'[\s_]+', '-', t)
    t = '-'.join(t.strip('-').split('-')[:max_words])
    return t


# ============================================================
# KEYWORD DENSITY
# ============================================================
def keyword_density(html, kw):
    if not kw: return 0.0
    text = strip_html(html).lower()
    words = text.split()
    if not words: return 0.0
    return (text.count(kw.lower()) / len(words)) * 100


def tune_keyword_density(html, kw, min_pct=1.0, max_pct=1.8):
    if not kw: return html
    kw_lower = kw.lower()
    density = keyword_density(html, kw)

    if density > max_pct:
        total_words = len(strip_html(html).split())
        keep_count = max(2, int(total_words * (min_pct / 100)))
        parts = re.split(r'(<[^>]+>)', html)
        seen = 0
        for i, part in enumerate(parts):
            if part.startswith("<"): continue
            while kw_lower in part.lower():
                idx = part.lower().find(kw_lower)
                if idx < 0: break
                if seen < keep_count:
                    seen += 1
                    left = part[:idx + len(kw)]
                    right = part[idx + len(kw):]
                    part = left + "\x00" + right
                else:
                    part = part[:idx] + "the product" + part[idx + len(kw):]
            parts[i] = part.replace("\x00", "")
        html = "".join(parts)

    elif density < min_pct:
        headings = re.findall(r'<h2>(.*?)</h2>', html, flags=re.DOTALL)
        needed = max(2, int(min_pct * 2))
        injected = 0
        for h in headings:
            if injected >= needed: break
            clean_h = re.sub(r'<[^>]+>', '', h)
            if kw_lower in clean_h.lower(): continue
            if len(clean_h) > 55: continue
            new_h = f"{clean_h} — {kw.title()}"
            html = html.replace(f"<h2>{h}</h2>", f"<h2>{new_h}</h2>", 1)
            injected += 1

        if keyword_density(html, kw) < min_pct:
            m = re.search(r'<p>(.*?)</p>', html, flags=re.DOTALL)
            if m:
                p_text = m.group(1)
                if kw_lower not in p_text.lower():
                    new_p = f"{kw.title()} is a common herbal product. {p_text}"
                    html = html.replace(m.group(0), f"<p>{new_p}</p>", 1)

    return html


# ============================================================
# TRUST / E-E-A-T BLOCK
# ============================================================
def build_trust_block() -> str:
    """Small credibility block — no fake claims."""
    store = Config.STORE_NAME
    country = Config.STORE_COUNTRY
    est = Config.STORE_ESTABLISHED

    lines = [f"<p>{store} serves customers across {country} with traditional "
             f"herbal products."]
    if est:
        lines.append(f"Established in {est}.")
    lines.append("We describe every product honestly and factually — no "
                 "exaggerated health claims.")
    lines.append("For specific questions, contact us directly.</p>")

    return (
        '<div class="khs-trust-block" style="margin:24px 0;padding:16px;'
        'background:#f8fafc;border-left:4px solid #64748b;border-radius:8px;'
        'font-size:14px;color:#475569;">'
        '<strong>About ' + store + '</strong>'
        + "".join(lines) +
        '</div>'
    )


# ============================================================
# SECTION TEMPLATES
# ============================================================
SECTION_HEADINGS = [
    "Introduction",
    "What is {topic}?",
    "Key Information About {topic}",
    "Traditional Uses and Benefits",
    "How {topic} Is Typically Used",
    "Precautions and Important Information",
    "Buying {topic} in {country}",
    "Storage and Care",
    "More to Know",
]

FAQ_TEMPLATES = [
    ("What is {topic}?",
     "{topic} is a herbal product available from {store}. It has been used in traditional practice for generations."),
    ("Is {topic} safe for daily use?",
     "As with any herbal product, use moderately and follow the label. Consult a qualified professional if pregnant, nursing, or taking medication."),
    ("What are the traditional uses of {topic}?",
     "Traditional households have used {topic} for various everyday purposes. Individual uses vary — always read the manufacturer's guidance."),
    ("Where can I buy {topic} in {country}?",
     "You can order {topic} online from {store} with delivery across {country}."),
    ("Can {topic} be combined with other herbal products?",
     "Many people do combine herbal products. Review related items from the same category and consult a practitioner if unsure."),
    ("How should I store {topic}?",
     "Keep it cool, dry, away from direct sunlight. Close the container tightly after use."),
    ("Is {topic} a medicine?",
     "No. {topic} is a herbal product, not a medicine, and it is not intended to diagnose, treat, cure, or prevent any disease."),
]


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_html(topic, sections, faqs, conclusion, h1="", pros_cons_html="", trust_html=""):
    store = Config.STORE_NAME
    parts = [f'<div class="khs-product-hero" style="text-align:center;'
             f'padding:20px 0 10px;border-bottom:1px solid #e5e7eb;margin-bottom:24px;">'
             f'<h1 style="font-size:28px;margin:0 0 8px;color:#0f172a;">{_esc(h1 or topic)}</h1>'
             f'<p style="color:#64748b;font-size:14px;margin:0;">'
             f'Available at {_esc(store)} · Fast delivery across {Config.STORE_COUNTRY}</p></div>']
    for s in sections:
        if s.get("heading"):
            parts.append(f'<h2 style="color:#0f172a;margin-top:28px;'
                         f'border-left:4px solid #16a34a;padding-left:12px;">{_esc(s["heading"])}</h2>')
        for p in s.get("paragraphs", []):
            if p.strip():
                parts.append(f'<p style="line-height:1.7;color:#1f2937;">{_esc(p)}</p>')

    # Insert pros/cons after 4th block
    if pros_cons_html:
        parts.insert(min(5, len(parts)), pros_cons_html)

    if faqs:
        parts.append('<h2 style="color:#0f172a;margin-top:28px;'
                     'border-left:4px solid #16a34a;padding-left:12px;">'
                     'Frequently Asked Questions</h2>')
        for f in faqs:
            parts.append(f'<h3 style="color:#166534;margin-top:16px;font-size:16px;">{_esc(f["q"])}</h3>')
            parts.append(f'<p style="line-height:1.7;color:#1f2937;">{_esc(f["a"])}</p>')

    if conclusion:
        parts.append('<h2 style="color:#0f172a;margin-top:28px;'
                     'border-left:4px solid #16a34a;padding-left:12px;">Conclusion</h2>')
        parts.append(f'<p style="line-height:1.7;color:#1f2937;">{_esc(conclusion)}</p>')

    if trust_html:
        parts.append(trust_html)

    return "\n".join(parts)


# ============================================================
# MAIN GENERATOR
# ============================================================
def generate_article(topic, raw, target_words=800, h1="", pid=0):
    raw = clean_input(raw or "")
    if len(raw) < 80: return None

    sents = split_sentences(raw)
    if not sents: sents = [raw]

    rng = random.Random(_seed(topic, raw[:200]))
    keywords = extract_keywords(raw, 10)
    reformulated = [reformulate(s, rng) for s in sents]

    n = len(reformulated)
    n_sections = min(len(SECTION_HEADINGS), max(4, n // 3))
    per = max(2, n // max(1, n_sections))

    sections = []
    idx = 0
    for i in range(n_sections):
        if idx >= n: break
        chunk = reformulated[idx:idx + per]
        idx += per
        paras, buf = [], []
        for s in chunk:
            buf.append(s)
            if len(buf) >= rng.randint(2, 4):
                paras.append(" ".join(buf)); buf = []
        if buf: paras.append(" ".join(buf))
        if paras:
            sections.append({"heading": SECTION_HEADINGS[i].format(
                topic=topic, country=Config.STORE_COUNTRY),
                "paragraphs": paras})

    if idx < n:
        leftover = reformulated[idx:]
        sections.append({"heading": "More to Know",
                         "paragraphs": [" ".join(leftover[i:i+3])
                                        for i in range(0, len(leftover), 3)]})

    current = sum(len(p.split()) for s in sections for p in s.get("paragraphs", []))
    if current < target_words:
        padding = [
            {"heading": f"Understanding {topic} Better",
             "paragraphs": [
                 f"When exploring {topic}, it helps to understand the broader context of traditional herbal practice in {Config.STORE_COUNTRY}. Generations of households have kept similar products on hand as part of everyday routines rather than isolated items.",
                 f"Individual experiences with {topic} vary, which is why reading the manufacturer's guidance is essential. The label provides the authoritative information on ingredients, quantity, and any precautions.",
             ]},
            {"heading": f"Why {topic} Matters",
             "paragraphs": [
                 f"Interest in {topic} reflects a wider movement toward traditional and plant-based options in {Config.STORE_COUNTRY}. Many buyers appreciate being able to compare products from the same category side by side.",
                 f"If you are new to herbal products, starting with one or two items from the same category — like {topic} — is a sensible approach.",
             ]},
            {"heading": "Choosing the Right Product",
             "paragraphs": [
                 f"Look for clear category information, stable availability, and honest product descriptions. These factors make it easier to compare and reorder the same {topic} when you need it.",
                 f"Reach out through the contact options on this page if you need further details about {topic} before ordering.",
             ]},
            {"heading": "Final Thoughts",
             "paragraphs": [
                 f"{topic} belongs to a rich tradition of herbal products in {Config.STORE_COUNTRY}. Understanding the basics helps you make an informed choice.",
                 f"Always read the manufacturer's label, store correctly, and consult a qualified professional if you have questions.",
             ]},
        ]
        for pad in padding:
            sections.append(pad)
            current = sum(len(p.split()) for s in sections
                          for p in s.get("paragraphs", []))
            if current >= target_words: break

    store = Config.STORE_NAME
    country = Config.STORE_COUNTRY

    faqs = []
    for q, a in FAQ_TEMPLATES[:5]:
        faqs.append({"q": q.format(topic=topic, store=store, country=country),
                     "a": a.format(topic=topic, store=store, country=country)})

    conclusion = (
        f"In summary, {topic} sits within {country}'s long-standing herbal tradition. "
        f"This guide covered the essentials — what it is, how it's typically used, "
        f"precautions, storage and where to buy. Always read the manufacturer's "
        f"guidance and consult a qualified professional if you have questions."
    )

    pros_cons_html = build_pros_cons(topic, pid)
    trust_html = build_trust_block()

    html = build_html(topic, sections, faqs, conclusion, h1=h1,
                      pros_cons_html=pros_cons_html, trust_html=trust_html)
    wc = word_count(html)

    if wc < target_words:
        html += ('<h2>Important Disclaimer</h2>'
                 '<p>This article is provided for general information only. '
                 'It is not medical advice. Always read the product label and '
                 'consult a qualified healthcare professional before use.</p>')

    focus_kw = keywords[0] if keywords else ""
    html = tune_keyword_density(html, focus_kw, min_pct=1.0, max_pct=1.8)

    return {
        "html": html,
        "word_count": word_count(html),
        "keywords": keywords,
        "faqs": faqs,
        "pros_cons": get_pros_cons_data(topic, pid),
    }


def readability(html):
    text = strip_html(html)
    if not text or not TEXTSTAT_OK: return {"flesch": 0, "grade": 0}
    try:
        return {"flesch": round(textstat.flesch_reading_ease(text), 1),
                "grade": round(textstat.flesch_kincaid_grade(text), 1)}
    except Exception:
        return {"flesch": 0, "grade": 0}