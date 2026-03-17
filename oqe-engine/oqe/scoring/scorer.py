"""
oqe/scoring/scorer.py
Applies the OQE scoring model to each classified question.
Produces a score 0-100 based on six weighted factors.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

# Default weights — configurable in weights.json
DEFAULT_WEIGHTS = {
    "search_intent": 1.0,
    "operational_relevance": 1.0,
    "conversion_potential": 1.0,
    "recency": 1.0,
    "source_credibility": 1.0,
}

# Phrases that signal high search intent
HIGH_INTENT_STARTERS = [
    "how do i", "how to", "how can i", "how should i",
    "what is", "what are", "what does", "what should",
    "when should", "when do", "when is the right time",
    "should i hire", "should i", "do i need",
    "why does", "why is", "why do",
    "what's the best way", "what's the difference",
    "is it worth", "how much does",
]

# Phrases that signal conversion proximity
CONVERSION_PHRASES = [
    "should i hire", "worth hiring", "do i need a coo",
    "what does a fractional", "how much does a fractional",
    "when to hire", "cost of", "how to find",
    "should i bring in", "looking for someone",
    "need help with", "overwhelmed",
]

# Operational keywords that boost relevance
OPERATIONAL_KEYWORDS = [
    "operations", "systems", "processes", "delegate", "delegation",
    "team", "hire", "coo", "fractional", "scale", "scaling",
    "accountability", "okr", "goals", "priorities", "align",
    "bottleneck", "founder", "ceo", "leadership", "burnout",
    "overwhelmed", "structure", "workflow", "capacity",
    "client", "revenue", "growth", "nonprofit", "startup",
]


def load_weights() -> dict:
    weights_path = Path(__file__).parent / "weights.json"
    if weights_path.exists():
        return json.loads(weights_path.read_text())
    return DEFAULT_WEIGHTS


def score_search_intent(question: dict) -> float:
    """
    Max 25 points.
    Does this question map to something someone would Google?
    """
    text = question.get("normalized_text", "").lower()
    score = 0.0

    # Starts with question word
    for starter in HIGH_INTENT_STARTERS:
        if text.startswith(starter):
            score += 12
            break
    else:
        if text.endswith("?"):
            score += 6

    # Contains specific role/context
    context_signals = ["founder", "ceo", "startup", "team", "nonprofit", "small business", "10-person", "early stage"]
    if any(s in text for s in context_signals):
        score += 8

    # Maps to taxonomy keyword
    if question.get("cluster_id"):
        score += 5

    return min(score, 25.0)


def score_operational_relevance(question: dict, taxonomy: dict) -> float:
    """
    Max 25 points.
    How directly does this relate to what Layer Advisory solves?
    """
    text = question.get("normalized_text", "").lower()
    score = 0.0

    # Maps to a taxonomy cluster
    if question.get("cluster_id"):
        score += 15

    # Contains operational keywords
    keyword_hits = sum(1 for kw in OPERATIONAL_KEYWORDS if kw in text)
    score += min(keyword_hits * 2, 6)

    # Asked by someone who identifies as target audience
    audience_signals = ["founder", "ceo", "we're a", "our team", "my team", "i run", "i own", "i lead"]
    if any(s in text for s in audience_signals):
        score += 4

    return min(score, 25.0)


def score_conversion_potential(question: dict) -> float:
    """
    Max 20 points.
    How close is this to a buying or booking decision?
    """
    text = question.get("normalized_text", "").lower()
    score = 0.0

    # Contains high-conversion phrases
    for phrase in CONVERSION_PHRASES:
        if phrase in text:
            score += 12
            break

    # Specific growth stage mentioned
    stage_signals = ["10 people", "20 people", "series a", "series b", "raised", "growing", "scaling", "5 employees", "small team"]
    if any(s in text for s in stage_signals):
        score += 5

    # Can be answered with a CTA
    cta_signals = ["should i", "do i need", "worth it", "help with", "where do i"]
    if any(s in text for s in cta_signals):
        score += 3

    return min(score, 20.0)


def score_recency(question: dict) -> float:
    """
    Max 15 points.
    How recently was this question asked?
    """
    harvested_at = question.get("harvested_at", "")
    if not harvested_at:
        return 5.0

    try:
        harvested = datetime.fromisoformat(harvested_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days_ago = (now - harvested).days

        if days_ago <= 7:
            return 15.0
        elif days_ago <= 30:
            return 12.0
        elif days_ago <= 90:
            return 8.0
        elif days_ago <= 180:
            return 4.0
        else:
            return 1.0
    except Exception:
        return 5.0


def score_source_credibility(question: dict) -> float:
    """
    Max 15 points.
    Source quality × engagement signal.
    """
    source = question.get("source", "")
    upvotes = question.get("upvotes", 0)

    base_scores = {
        "google_paa": 12,     # Pre-validated by Google
        "reddit": 10,
        "indie_hackers": 8,
        "quora": 8,
        "podcast": 8,
        "newsletter": 5,
    }

    base = base_scores.get(source, 3)

    # Boost for engagement
    if upvotes >= 100:
        engagement_boost = 3
    elif upvotes >= 20:
        engagement_boost = 2
    elif upvotes >= 5:
        engagement_boost = 1
    else:
        engagement_boost = 0

    return min(base + engagement_boost, 15.0)


def score_duplicate_penalty(question: dict, existing_posts: list) -> float:
    """
    0 to -20 points.
    Semantic similarity to already-published posts.
    Uses simple keyword overlap as a lightweight proxy.
    """
    text_words = set(question.get("normalized_text", "").lower().split())

    max_overlap = 0.0
    for post in existing_posts:
        post_title_words = set(post.get("title", "").lower().split())
        post_kw_words = set(post.get("primary_keyword", "").lower().split())
        all_post_words = post_title_words | post_kw_words

        if not all_post_words:
            continue

        overlap = len(text_words & all_post_words) / max(len(text_words), len(all_post_words), 1)
        max_overlap = max(max_overlap, overlap)

    if max_overlap >= 0.80:
        return -20.0   # Near-exact match — discard
    elif max_overlap >= 0.60:
        return -10.0   # High overlap
    elif max_overlap >= 0.40:
        return -5.0    # Moderate overlap
    else:
        return 0.0     # Genuinely new


def score_question(question: dict, taxonomy: dict, existing_posts: list) -> dict:
    """
    Run all scoring factors and return updated question with scores.
    """
    weights = load_weights()

    s_intent = score_search_intent(question) * weights.get("search_intent", 1.0)
    s_relevance = score_operational_relevance(question, taxonomy) * weights.get("operational_relevance", 1.0)
    s_conversion = score_conversion_potential(question) * weights.get("conversion_potential", 1.0)
    s_recency = score_recency(question) * weights.get("recency", 1.0)
    s_credibility = score_source_credibility(question) * weights.get("source_credibility", 1.0)
    s_duplicate = score_duplicate_penalty(question, existing_posts)

    total = s_intent + s_relevance + s_conversion + s_recency + s_credibility + s_duplicate
    total = max(0.0, min(100.0, total))

    question["score"] = round(total, 1)
    question["score_breakdown"] = {
        "search_intent": round(s_intent, 1),
        "operational_relevance": round(s_relevance, 1),
        "conversion_potential": round(s_conversion, 1),
        "recency": round(s_recency, 1),
        "source_credibility": round(s_credibility, 1),
        "duplicate_penalty": round(s_duplicate, 1),
    }

    return question
