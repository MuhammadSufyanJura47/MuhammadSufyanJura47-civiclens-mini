"""
Duplicate / near-duplicate detection for CivicLens Mini.

Two strategies, chosen automatically at runtime:

1. SEMANTIC (preferred) -- uses the open-source `sentence-transformers`
   embedding model `all-MiniLM-L6-v2` (Apache-2.0) if it is installed and can
   be loaded. Compares cosine similarity of complaint embeddings.

2. LEXICAL FALLBACK -- if sentence-transformers is not available, we fall back
   to a transparent token Jaccard / difflib ratio. This is CLEARLY LABELLED in
   the UI as a fallback so no one mistakes it for semantic matching.

The active method is reported via `active_method()` so the dashboard can tell
the user exactly what is running.
"""

from __future__ import annotations

import difflib
import re
from functools import lru_cache
from typing import Any

SIMILARITY_THRESHOLD = 0.72  # tune: above this => flagged as likely duplicate

_SEMANTIC_AVAILABLE: bool | None = None
_MODEL = None


def _try_load_model():
    global _SEMANTIC_AVAILABLE, _MODEL
    if _SEMANTIC_AVAILABLE is not None:
        return
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        _SEMANTIC_AVAILABLE = True
    except Exception:
        # Not installed, no network to download weights, or load failed.
        _SEMANTIC_AVAILABLE = False
        _MODEL = None


def active_method() -> str:
    _try_load_model()
    if _SEMANTIC_AVAILABLE:
        return "semantic"
    return "lexical"


def active_method_label() -> str:
    if active_method() == "semantic":
        return "Semantic (all-MiniLM-L6-v2 embeddings)"
    return "Lexical fallback (token overlap) — install sentence-transformers for semantic matching"


# --------------------------- lexical fallback ---------------------------------

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _lexical_similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    jaccard = len(ta & tb) / len(ta | tb)
    # Blend Jaccard with sequence ratio for a slightly smarter lexical score.
    seq = difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()
    return round(0.6 * jaccard + 0.4 * seq, 4)


# --------------------------- semantic path ------------------------------------


def _cosine(u: list[float], v: list[float]) -> float:
    dot = sum(x * y for x, y in zip(u, v))
    nu = sum(x * x for x in u) ** 0.5
    nv = sum(y * y for y in v) ** 0.5
    if nu == 0 or nv == 0:
        return 0.0
    return dot / (nu * nv)


@lru_cache(maxsize=512)
def _embed(text: str) -> tuple[float, ...]:
    _try_load_model()
    vec = _MODEL.encode(text, normalize_embeddings=True)  # type: ignore[union-attr]
    return tuple(float(x) for x in vec)


def _semantic_similarity(a: str, b: str) -> float:
    return round(_cosine(list(_embed(a)), list(_embed(b))), 4)


# --------------------------- public API ---------------------------------------


def similarity(a: str, b: str) -> float:
    if active_method() == "semantic":
        return _semantic_similarity(a, b)
    return _lexical_similarity(a, b)


def find_duplicates(
    text: str,
    existing: list[dict[str, Any]],
    *,
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """
    Compare `text` against each existing complaint's raw text.

    Returns a list of {id, score, title} for matches at/above threshold,
    sorted most-similar first.
    """
    matches: list[dict[str, Any]] = []
    for item in existing:
        other = item.get("text", "")
        if not other:
            continue
        score = similarity(text, other)
        if score >= threshold:
            matches.append(
                {
                    "id": item.get("id"),
                    "score": score,
                    "summary": (item.get("analysis") or {}).get("summary", ""),
                }
            )
    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches
