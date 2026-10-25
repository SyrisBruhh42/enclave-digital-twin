"""Smallville Generative Agent Memory Stream & Evidence-Cited Reflection Engine.

Implements Park et al. (2023) retrieval scoring:
    score = 1.0 * (0.995 ** delta_h_since_access)
          + 1.0 * (importance / 10.0)
          + 1.0 * relevance(m, q)

Runs 100% offline in <1ms using deterministic hybrid TF-IDF word unigram +
character token-trigram cosine similarity, refreshes `last_accessed_hour`
on retrieved memories, provides LRU-by-usage memory bank eviction, and
enforces Law L08 (strict evidence-cited reflections).
"""

import hashlib
import math
import re
from collections import Counter
from typing import Any

RECENCY_DECAY_BASE: float = 0.995
WEIGHT_RECENCY: float = 1.0
WEIGHT_IMPORTANCE: float = 1.0
WEIGHT_RELEVANCE: float = 1.0
DEFAULT_MEMORY_BANK_CAP: int = 256

_TOKEN_RE = re.compile(r"[a-z0-9_]+")
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "his",
        "in",
        "into",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "she",
        "that",
        "the",
        "their",
        "them",
        "they",
        "this",
        "to",
        "was",
        "were",
        "with",
    }
)


def _extract_memory_text(memory: dict[str, Any]) -> str:
    """Extract all searchable text fields from a memory or event dictionary."""
    parts: list[str] = []
    for key in (
        "summary",
        "text",
        "content",
        "insight_text",
        "description",
        "location",
        "science_vegetable",
        "event_type",
    ):
        val = memory.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())

    for list_key in ("actors", "tags", "keywords"):
        items = memory.get(list_key)
        if isinstance(items, (list, tuple, set)):
            parts.extend(str(x) for x in items if x)

    return " ".join(parts)


def _tokenize_with_trigrams(text: str) -> Counter[str]:
    """Tokenize text into content word unigrams and character 3-grams."""
    if not text:
        return Counter()
    raw_tokens = _TOKEN_RE.findall(text.lower())
    features: Counter[str] = Counter()
    for tok in raw_tokens:
        if tok in _STOPWORDS:
            continue
        features[f"w:{tok}"] += 1.0
        if len(tok) >= 3:
            padded = f"^{tok}$"
            for i in range(len(padded) - 2):
                features[f"g:{padded[i : i + 3]}"] += 0.35
    return features


def compute_relevance_scores(
    memories: list[dict[str, Any]], query_text: str
) -> list[float]:
    """Compute deterministic TF-IDF + token-trigram cosine similarity in [0.0, 1.0]."""
    if not memories:
        return []
    q_counts = _tokenize_with_trigrams(query_text)
    if not q_counts:
        return [0.0 for _ in memories]

    doc_counters: list[Counter[str]] = [
        _tokenize_with_trigrams(_extract_memory_text(m)) for m in memories
    ]

    num_docs = len(doc_counters) + 1
    df: Counter[str] = Counter()
    for feat in q_counts:
        df[feat] += 1
    for dc in doc_counters:
        for feat in dc:
            df[feat] += 1

    idf: dict[str, float] = {
        feat: math.log(1.0 + (num_docs / float(freq))) + 1.0
        for feat, freq in df.items()
    }

    q_vec: dict[str, float] = {
        feat: (1.0 + math.log(cnt)) * idf[feat]
        for feat, cnt in q_counts.items()
        if cnt > 0
    }
    q_norm = math.sqrt(sum(v * v for v in q_vec.values()))
    if q_norm <= 1e-12:
        return [0.0 for _ in memories]

    scores: list[float] = []
    for dc in doc_counters:
        if not dc:
            scores.append(0.0)
            continue
        dot = 0.0
        d_norm_sq = 0.0
        for feat, cnt in dc.items():
            if cnt <= 0:
                continue
            w = (1.0 + math.log(cnt)) * idf.get(feat, 1.0)
            d_norm_sq += w * w
            if feat in q_vec:
                dot += w * q_vec[feat]
        if d_norm_sq <= 1e-12 or dot <= 0.0:
            scores.append(0.0)
        else:
            sim = dot / (q_norm * math.sqrt(d_norm_sq))
            scores.append(max(0.0, min(1.0, sim)))
    return scores


def _get_memory_last_access_hour(
    memory: dict[str, Any], current_hour: float
) -> float:
    """Extract the last accessed hour from a memory record with safe fallbacks."""
    for key in ("last_accessed_hour", "created_hour", "hour", "tick_id"):
        if key in memory and memory[key] is not None:
            try:
                return float(memory[key])
            except (TypeError, ValueError):
                continue
    return float(current_hour)


def retrieve_top_memories(
    memories: list[dict],
    query_text: str,
    current_hour: float,
    top_k: int = 8,
) -> list[dict]:
    """Retrieve top-k memories using Park et al. (2023) Smallville scoring.

    Formula:
        score = 1.0 * (0.995 ** delta_h_since_access)
              + 1.0 * (importance / 10.0)
              + 1.0 * relevance(m, q)

    Refreshes `last_accessed_hour = current_hour` on all retrieved memories.
    """
    if not memories or top_k <= 0:
        return []

    curr_h = float(current_hour)
    relevances = compute_relevance_scores(memories, query_text or "")

    scored_entries: list[tuple[float, float, str, int, dict[str, Any]]] = []
    for idx, (mem, rel_score) in enumerate(zip(memories, relevances)):
        last_h = _get_memory_last_access_hour(mem, curr_h)
        delta_h = max(0.0, curr_h - last_h)
        recency_score = RECENCY_DECAY_BASE ** delta_h

        raw_importance = float(mem.get("importance", 5.0))
        importance_score = max(0.0, min(1.0, raw_importance / 10.0))

        total_score = (
            WEIGHT_RECENCY * recency_score
            + WEIGHT_IMPORTANCE * importance_score
            + WEIGHT_RELEVANCE * rel_score
        )
        mem_id = str(
            mem.get("event_id")
            or mem.get("memory_id")
            or mem.get("id")
            or f"mem_{idx:04d}"
        )
        scored_entries.append(
            (total_score, raw_importance, mem_id, idx, mem)
        )

    scored_entries.sort(key=lambda item: (-item[0], -item[1], item[2], item[3]))
    selected = scored_entries[: int(top_k)]

    retrieved: list[dict[str, Any]] = []
    for total_score, _raw_imp, _mem_id, _idx, mem in selected:
        last_h = _get_memory_last_access_hour(mem, curr_h)
        delta_h = max(0.0, curr_h - last_h)
        recency_score = RECENCY_DECAY_BASE ** delta_h
        importance_score = max(
            0.0, min(1.0, float(mem.get("importance", 5.0)) / 10.0)
        )
        rel_score = max(
            0.0, total_score - (recency_score + importance_score)
        )

        # Refresh access metadata in-place as required by Smallville memory physics
        mem["last_accessed_hour"] = curr_h
        mem["access_count"] = int(mem.get("access_count", 0)) + 1
        mem["retrieval_score"] = round(total_score, 6)
        mem["retrieval_components"] = {
            "recency": round(recency_score, 6),
            "importance": round(importance_score, 6),
            "relevance": round(rel_score, 6),
        }
        retrieved.append(mem)

    return retrieved


def evict_lru_memories(
    memories: list[dict],
    max_cap: int = DEFAULT_MEMORY_BANK_CAP,
) -> list[dict]:
    """LRU-by-usage eviction helper when memory bank exceeds cap.

    Retains pinned memories (`pinned=True` or `never_evict=True`) and evicts
    entries with the lowest `(last_accessed_hour, access_count, importance)`.
    """
    if max_cap <= 0:
        return []
    if len(memories) <= max_cap:
        return list(memories)

    pinned = [
        m
        for m in memories
        if bool(m.get("pinned", False) or m.get("never_evict", False))
    ]
    evictable = [
        m
        for m in memories
        if not bool(m.get("pinned", False) or m.get("never_evict", False))
    ]

    if len(pinned) >= max_cap:
        return pinned[:max_cap]

    remaining_slots = max_cap - len(pinned)
    evictable_sorted = sorted(
        evictable,
        key=lambda m: (
            float(m.get("last_accessed_hour", m.get("created_hour", 0.0))),
            int(m.get("access_count", 0)),
            float(m.get("importance", 0.0)),
        ),
        reverse=True,
    )
    kept_set = {id(m) for m in pinned} | {
        id(m) for m in evictable_sorted[:remaining_slots]
    }
    return [m for m in memories if id(m) in kept_set]


def should_trigger_reflection(
    recent_memories: list[dict],
    threshold: float = 150.0,
    is_sleep_tick: bool = False,
) -> bool:
    """Determine whether an agent should synthesize a higher-level reflection.

    Triggers when `is_sleep_tick` is True or when the cumulative importance
    of recent unreflected memories meets or exceeds `threshold` (150.0).
    """
    if is_sleep_tick:
        return True
    if not recent_memories:
        return False

    cumulative_importance = sum(
        float(m.get("importance", 0.0))
        for m in recent_memories
        if isinstance(m, dict) and not bool(m.get("reflected", False))
    )
    return cumulative_importance >= float(threshold)


def build_reflection_record(
    character_id: str,
    tick_id: int,
    colony_sol: int,
    insight_text: str,
    cited_event_ids: list[str],
    valid_event_ids: set[str],
) -> dict:
    """Build an evidence-cited reflection record enforcing Law L08.

    Law L08: MUST raise a ValueError if `cited_event_ids` is empty or contains
    any ID not present in `valid_event_ids`.
    """
    if not isinstance(character_id, str) or not character_id.strip():
        raise ValueError("character_id must be a non-empty string.")
    if not isinstance(insight_text, str) or not insight_text.strip():
        raise ValueError("insight_text must be a non-empty string.")

    if not cited_event_ids or not isinstance(cited_event_ids, (list, tuple, set)):
        raise ValueError(
            "Law L08 Violation: cited_event_ids must be a non-empty list of valid event IDs."
        )

    if valid_event_ids is None or not isinstance(
        valid_event_ids, (set, frozenset, list, tuple, dict)
    ):
        raise ValueError(
            "Law L08 Violation: valid_event_ids must be a non-empty set of known event IDs."
        )

    valid_set = set(valid_event_ids)
    normalized_citations: list[str] = []
    for eid in cited_event_ids:
        if not isinstance(eid, str) or not eid.strip():
            raise ValueError(
                f"Law L08 Violation: invalid empty or non-string cited event ID: {eid!r}"
            )
        if eid not in valid_set:
            raise ValueError(
                f"Law L08 Violation: cited event ID '{eid}' does not exist in valid_event_ids."
            )
        if eid not in normalized_citations:
            normalized_citations.append(eid)

    if not normalized_citations:
        raise ValueError(
            "Law L08 Violation: cited_event_ids resolved to zero valid citations."
        )

    clean_insight = insight_text.strip()
    digest = hashlib.sha256(
        f"{character_id}:{tick_id}:{colony_sol}:{clean_insight}:{','.join(normalized_citations)}".encode(
            "utf-8"
        )
    ).hexdigest()[:10]
    event_id = f"evt_refl_{character_id}_s{int(colony_sol):03d}_t{int(tick_id):04d}_{digest}"
    hour_val = float((int(colony_sol) - 1) * 24 + int(tick_id))

    return {
        "event_id": event_id,
        "memory_id": event_id,
        "character_id": character_id,
        "tick_id": int(tick_id),
        "colony_sol": int(colony_sol),
        "day_phase": "NIGHT_REFLECTION",
        "world_timestamp_iso": f"2026-10-{24 + max(1, int(colony_sol)):02d}T23:00:00Z",
        "base_snapshot_tick": int(tick_id),
        "event_type": "NIGHTLY_REFLECTION",
        "memory_type": "reflection",
        "location": "Enclave_Quarters",
        "actors": [character_id],
        "insight_text": clean_insight,
        "summary": clean_insight,
        "text": clean_insight,
        "importance": 8.0,
        "novelty_score": 0.75,
        "science_vegetable": "Autobiographical memory consolidation and schema synthesis",
        "state_deltas": {"stress_delta": -0.05},
        "relationship_deltas": {},
        "cited_event_ids": normalized_citations,
        "evidence_refs": list(normalized_citations),
        "created_hour": hour_val,
        "last_accessed_hour": hour_val,
        "access_count": 1,
        "reflected": True,
    }
