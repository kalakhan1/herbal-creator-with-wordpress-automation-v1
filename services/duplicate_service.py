"""Duplicate detection — within batch + against persistent memory."""
import re
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import database

MEMORY_LIMIT = 500      # last N items kept in memory for comparison


def _clean(html: str) -> str:
    t = re.sub(r'<[^>]+>', ' ', html or '')
    return re.sub(r'\s+', ' ', t).lower().strip()


def check_duplicates(items: List[Dict], text_key: str = "content") -> List[Dict]:
    """Within-batch duplicate detection."""
    if len(items) < 2:
        return [{"id": it["id"], "max_similarity": 0.0, "most_similar_to": None} for it in items]

    texts = [_clean(it.get(text_key, "")) for it in items]
    valid = [i for i, t in enumerate(texts) if len(t) > 50]
    if len(valid) < 2:
        return [{"id": items[i]["id"], "max_similarity": 0.0, "most_similar_to": None}
                for i in range(len(items))]

    try:
        vec = TfidfVectorizer(max_features=5000, stop_words="english")
        m = vec.fit_transform([texts[i] for i in valid])
        sim = cosine_similarity(m)
    except Exception:
        return [{"id": it["id"], "max_similarity": 0.0, "most_similar_to": None} for it in items]

    results = []
    for idx_v, global_i in enumerate(valid):
        row = sim[idx_v].copy()
        row[idx_v] = 0
        max_sim = float(row.max()) if row.size else 0.0
        max_arg = int(row.argmax()) if row.size else 0
        similar_id = items[valid[max_arg]]["id"] if row.size else None
        results.append({
            "id": items[global_i]["id"],
            "max_similarity": round(max_sim, 3),
            "most_similar_to": similar_id,
        })
    done = {r["id"] for r in results}
    for it in items:
        if it["id"] not in done:
            results.append({"id": it["id"], "max_similarity": 0.0, "most_similar_to": None})
    return results


def check_against_memory(new_item: Dict, text_key: str = "content",
                         content_type: str = "product") -> Dict:
    """
    Compare a new item's content against persisted memory.
    Returns {max_similarity, most_similar_to (dict|None), memory_size}
    """
    new_text = _clean(new_item.get(text_key, ""))
    if len(new_text) < 50:
        return {"max_similarity": 0.0, "most_similar_to": None, "memory_size": 0}

    memory_items = database.get_memory(content_type, limit=MEMORY_LIMIT)
    if not memory_items:
        return {"max_similarity": 0.0, "most_similar_to": None, "memory_size": 0}

    texts = [new_text] + [m.get("clean_text", "") for m in memory_items]
    try:
        vec = TfidfVectorizer(max_features=5000, stop_words="english")
        m = vec.fit_transform(texts)
        sim = cosine_similarity(m[0:1], m[1:])[0]
    except Exception:
        return {"max_similarity": 0.0, "most_similar_to": None,
                "memory_size": len(memory_items)}

    if not len(sim):
        return {"max_similarity": 0.0, "most_similar_to": None,
                "memory_size": len(memory_items)}

    idx = int(sim.argmax())
    max_sim = float(sim[idx])
    most = memory_items[idx]
    return {
        "max_similarity": round(max_sim, 3),
        "most_similar_to": {
            "id": most.get("item_id"),
            "title": most.get("title"),
            "type": most.get("content_type"),
        },
        "memory_size": len(memory_items),
    }


def persist_to_memory(content_type: str, item_id: int, slug: str, title: str, html: str):
    """Save generated content into memory for future batch comparisons."""
    clean = _clean(html)
    if len(clean) < 50:
        return
    database.save_to_memory(content_type, item_id, slug, title, clean)