"""
oqe/queue/queue_builder.py
Assembles the final prioritized question queue.
Applies cluster balance, content type diversity,
and generates suggested titles via Claude.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
import anthropic
import os


QUEUE_FILE = Path(__file__).parent / "question_queue.json"
ARCHIVE_DIR = Path(__file__).parent / "archive"
ARCHIVE_DIR.mkdir(exist_ok=True)

MINIMUM_SCORE = 45.0
MAX_PER_CLUSTER_IN_TOP_10 = 3


def enforce_cluster_balance(questions: list, top_n: int = 10) -> list:
    """
    Ensure no more than MAX_PER_CLUSTER_IN_TOP_10 questions
    from the same cluster appear in the top N.
    """
    cluster_counts = {}
    top = []
    rest = []

    for q in questions:
        cluster = q.get("cluster_id", "unknown")
        count = cluster_counts.get(cluster, 0)

        if len(top) < top_n and count < MAX_PER_CLUSTER_IN_TOP_10:
            top.append(q)
            cluster_counts[cluster] = count + 1
        else:
            rest.append(q)

    return top + rest


def enforce_content_diversity(questions: list, top_n: int = 10) -> list:
    """
    Ensure the top N has a mix of content types.
    At most 4 how-tos in the top 10.
    """
    top = questions[:top_n]
    rest = questions[top_n:]

    how_to_count = sum(1 for q in top if q.get("content_type") == "how-to")
    if how_to_count <= 4:
        return questions  # Already balanced

    # Move excess how-tos to the back
    rebalanced_top = []
    overflow = []
    current_how_to = 0

    for q in top:
        if q.get("content_type") == "how-to" and current_how_to >= 4:
            overflow.append(q)
        else:
            if q.get("content_type") == "how-to":
                current_how_to += 1
            rebalanced_top.append(q)

    # Fill remaining top spots from rest (non-how-to first)
    non_how_to_rest = [q for q in rest if q.get("content_type") != "how-to"]
    for q in non_how_to_rest:
        if len(rebalanced_top) < top_n:
            rebalanced_top.append(q)
            rest.remove(q)

    return rebalanced_top + overflow + rest


def generate_suggested_titles(questions: list, skill_text: str) -> list:
    """
    Use Claude to generate a compelling blog post title
    for each question in the queue.
    """
    if not questions:
        return questions

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Batch the title generation
    questions_text = "\n".join(
        f"{i+1}. [{q.get('cluster_id', '')}] {q.get('text', '')}"
        for i, q in enumerate(questions[:20])
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"""You are writing blog post titles for Layer Advisory Services in Erica Layer's voice.

Voice notes: grounded, warm, quietly confident. No clickbait. Lead with tension or insight.
Good examples: "The Real Cost of Being the Founder Bottleneck", "Slack Time Isn't Wasted Time. It's Leadership Time."

Generate one compelling blog title for each question below.

{questions_text}

Return ONLY a JSON array of title strings in the same order. No preamble."""
        }]
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    titles = json.loads(raw)
    for i, q in enumerate(questions[:20]):
        if i < len(titles):
            q["suggested_title"] = titles[i]

    return questions


def build_queue(scored_questions: list, taxonomy: dict, skill_text: str = "") -> dict:
    """
    Take scored questions, apply ranking rules, and write question_queue.json.
    """
    # Filter by minimum score
    passing = [q for q in scored_questions if q.get("score", 0) >= MINIMUM_SCORE]
    discarded = [q for q in scored_questions if q.get("score", 0) < MINIMUM_SCORE]

    print(f"  Scoring: {len(passing)} passed (≥{MINIMUM_SCORE}), {len(discarded)} discarded")

    # Sort by score descending
    ranked = sorted(passing, key=lambda q: q.get("score", 0), reverse=True)

    # Apply balance rules
    balanced = enforce_cluster_balance(ranked)
    diverse = enforce_content_diversity(balanced)

    # Generate suggested titles for top 20
    if skill_text:
        diverse = generate_suggested_titles(diverse[:20], skill_text) + diverse[20:]

    # Load existing queue and merge (avoid duplicates)
    existing_queue = {}
    if QUEUE_FILE.exists():
        existing_data = json.loads(QUEUE_FILE.read_text())
        for item in existing_data.get("queue", []):
            existing_queue[item.get("id", "")] = item

    # Add new questions, skip duplicates
    added = 0
    for q in diverse:
        qid = q.get("id", "")
        if qid not in existing_queue:
            q["rank"] = len(existing_queue) + added + 1
            existing_queue[qid] = q
            added += 1

    final_queue = sorted(
        existing_queue.values(),
        key=lambda q: q.get("score", 0),
        reverse=True
    )

    # Re-rank
    for i, q in enumerate(final_queue):
        q["rank"] = i + 1

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_questions": len(final_queue),
        "added_this_run": added,
        "sources_run": list({q.get("source", "") for q in diverse}),
        "queue": final_queue,
    }

    QUEUE_FILE.write_text(json.dumps(output, indent=2))
    print(f"  Queue: {len(final_queue)} total ({added} new)")

    # Archive discarded
    if discarded:
        archive_file = ARCHIVE_DIR / f"discarded_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        archive_file.write_text(json.dumps(discarded, indent=2))

    return output
