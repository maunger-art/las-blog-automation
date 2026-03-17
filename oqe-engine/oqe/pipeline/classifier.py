"""
oqe/pipeline/classifier.py
Maps raw questions to taxonomy clusters and content types.
"""

import re

# Keyword signals per cluster — used for fast matching
CLUSTER_SIGNALS = {
    "founder-dependency": [
        "bottleneck", "everything through me", "can't delegate", "doing everything",
        "stop being the bottleneck", "depends on me", "relies on me", "founder dependency",
        "letting go", "micromanage", "control", "trust my team", "step back",
    ],
    "operational-clarity": [
        "process", "processes", "documentation", "sop", "standard operating",
        "systems", "workflow", "how we work", "consistency", "documented",
        "operations manual", "playbook", "handbook",
    ],
    "team-alignment": [
        "align", "alignment", "okr", "goals", "priorities", "team meeting",
        "l10", "quarterly", "accountability", "scorecard", "decision",
        "communication", "same page", "all hands",
    ],
    "fractional-leadership": [
        "fractional coo", "fractional executive", "part time coo", "part-time coo",
        "what is a fractional", "hire a fractional", "fractional leader",
        "fractional vs full time", "need a coo", "do i need a coo",
    ],
    "sustainable-growth": [
        "scale", "scaling", "growing too fast", "overwhelmed", "burnout",
        "sustainable", "capacity", "too much on my plate", "prioritize",
        "focus", "less is more", "what to cut", "growth feels chaotic",
    ],
    "hiring-and-roles": [
        "hire", "hiring", "first hire", "job description", "role clarity",
        "accountability chart", "onboarding", "retain", "retention", "turnover",
        "right person", "right seat", "org chart", "reporting structure",
    ],
    "leadership-mindset": [
        "leadership", "founder mindset", "ceo mindset", "imposter syndrome",
        "confidence", "burnout", "work life balance", "habits", "productivity",
        "decision making", "slack time", "rest", "energy management",
    ],
}

CONTENT_TYPES = {
    "how-to": ["how do i", "how to", "how can i", "how should i", "steps to", "ways to"],
    "what-is": ["what is", "what are", "what does", "what's the difference", "explain"],
    "when-to": ["when should", "when do i", "when is the right time", "at what point"],
    "comparison": ["vs", "versus", "difference between", "better", "which is"],
    "story": ["why does", "why is", "why do", "why can't", "reason why"],
}

TOOL_LINKS = {
    "fractional-leadership": {
        "tool_id": "diagnostic-assessment",
        "tool_name": "Operational Diagnostic",
        "tool_url": "https://layeradvisory.com/#diagnostic",
        "cta_copy": "Not sure if you need a fractional COO? Take the 5-minute diagnostic.",
    },
    "founder-dependency": {
        "tool_id": "diagnostic-assessment",
        "tool_name": "Operational Diagnostic",
        "tool_url": "https://layeradvisory.com/#diagnostic",
        "cta_copy": "Find out where founder dependency is costing you most.",
    },
    "operational-clarity": {
        "tool_id": "diagnostic-assessment",
        "tool_name": "Operational Diagnostic",
        "tool_url": "https://layeradvisory.com/#diagnostic",
        "cta_copy": "Discover which operational gaps are slowing your team down.",
    },
}


def match_cluster(text: str, taxonomy: dict) -> str | None:
    """
    Match a question to the best taxonomy cluster.
    First tries signal keywords, then falls back to taxonomy keywords.
    """
    text_lower = text.lower()

    # Score each cluster by keyword hits
    cluster_scores = {}
    for cluster_id, signals in CLUSTER_SIGNALS.items():
        hits = sum(1 for s in signals if s in text_lower)
        if hits > 0:
            cluster_scores[cluster_id] = hits

    if cluster_scores:
        return max(cluster_scores, key=cluster_scores.get)

    # Fall back to taxonomy keywords
    for cluster in taxonomy.get("clusters", []):
        cluster_keywords = cluster.get("keywords", [])
        hits = sum(1 for kw in cluster_keywords if kw.lower() in text_lower)
        if hits > 0:
            cluster_scores[cluster["id"]] = hits

    if cluster_scores:
        return max(cluster_scores, key=cluster_scores.get)

    return None


def infer_content_type(text: str) -> str:
    """Determine what kind of content this question maps to."""
    text_lower = text.lower()

    for content_type, signals in CONTENT_TYPES.items():
        if any(text_lower.startswith(s) or s in text_lower for s in signals):
            return content_type

    return "how-to"  # Default


def suggest_tool(cluster_id: str) -> dict | None:
    """Return a tool link suggestion for this cluster."""
    return TOOL_LINKS.get(cluster_id)


def classify_question(question: dict, taxonomy: dict) -> dict:
    """
    Add cluster_id, topic_id, content_type, and tool_link to a question dict.
    Returns None if question can't be classified.
    """
    text = question.get("normalized_text", question.get("text", ""))

    cluster_id = match_cluster(text, taxonomy)
    if not cluster_id:
        question["status"] = "discarded"
        question["discard_reason"] = "no cluster match"
        return question

    question["cluster_id"] = cluster_id
    question["content_type"] = infer_content_type(text)
    question["tool_link"] = suggest_tool(cluster_id)
    question["status"] = "classified"

    return question
