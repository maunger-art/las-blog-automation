#!/usr/bin/env python3
"""
run_oqe.py
Main entry point for the Operational Question Engine.
Orchestrates harvest → parse → classify → score → queue.

Usage:
  python3 run_oqe.py --sources reddit google_paa indie_hackers
  python3 run_oqe.py --sources all
  python3 run_oqe.py --status
  python3 run_oqe.py --sources reddit --dry-run
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add repo root to path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from oqe.sources.base_source import RawQuestion
from oqe.sources.reddit import RedditSource
from oqe.sources.google_paa import GooglePAASource
from oqe.sources.indie_hackers import IndieHackersSource
from oqe.pipeline.classifier import classify_question
from oqe.scoring.scorer import score_question
from oqe.queue.queue_builder import build_queue

TAXONOMY_FILE = ROOT / "taxonomy.json"
MANIFEST_FILE = ROOT / "posts_manifest.json"
SKILL_FILE = ROOT / "SKILL.md"
OQE_QUEUE_FILE = ROOT / "oqe" / "queue" / "question_queue.json"
AQE_QUEUE_FILE = ROOT / "aqe_queue.json"  # Shared queue with AQE


def load_json(path):
    if path.exists():
        return json.loads(path.read_text())
    return {}


def load_text(path):
    if path.exists():
        return path.read_text()
    return ""


def get_all_seed_keywords(taxonomy: dict) -> list:
    """Extract all seed keywords from taxonomy clusters."""
    keywords = []
    for cluster in taxonomy.get("clusters", []):
        keywords.extend(cluster.get("keywords", []))
        keywords.append(cluster.get("pillar_keyword", ""))
    return [k for k in keywords if k]


def get_source_config(taxonomy: dict) -> dict:
    """Build source config from taxonomy and environment."""
    return {
        "reddit": {
            "subreddits": [
                "startups", "Entrepreneur", "smallbusiness",
                "SaaS", "nonprofit", "Consulting", "freelance",
                "business", "EntrepreneurRideAlong",
            ],
            "max_per_subreddit": 25,
            "min_upvotes": 3,
        },
        "google_paa": {
            "serpapi_key": os.environ.get("SERPAPI_KEY", ""),
            "max_per_keyword": 8,
        },
        "indie_hackers": {
            "max_results": 40,
        },
    }


def run_pipeline(sources: list, dry_run: bool = False):
    taxonomy = load_json(TAXONOMY_FILE)
    manifest = load_json(MANIFEST_FILE)
    skill_text = load_text(SKILL_FILE)
    existing_posts = manifest.get("posts", [])

    if not taxonomy:
        print("ERROR: taxonomy.json not found")
        return

    keywords = get_all_seed_keywords(taxonomy)
    config = get_source_config(taxonomy)

    print(f"\n{'='*50}")
    print(f"OQE Pipeline — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Sources: {', '.join(sources)}")
    print(f"Seed keywords: {len(keywords)}")
    print(f"Existing posts: {len(existing_posts)}")
    print(f"{'='*50}\n")

    # ── STAGE 1: HARVEST ──────────────────────────────────
    print("Stage 1: Harvesting...")
    all_raw = []

    source_map = {
        "reddit": RedditSource,
        "google_paa": GooglePAASource,
        "indie_hackers": IndieHackersSource,
    }

    for source_name in sources:
        if source_name not in source_map:
            print(f"  Unknown source: {source_name}")
            continue
        connector = source_map[source_name](config.get(source_name, {}))
        raw = connector.harvest(keywords[:10])  # Use top 10 keywords
        all_raw.extend(raw)

    print(f"  Total harvested: {len(all_raw)} raw questions\n")

    # ── STAGE 2: DEDUPLICATE ──────────────────────────────
    print("Stage 2: Deduplicating...")
    seen_ids = set()
    unique_raw = []
    for q in all_raw:
        if q.id not in seen_ids:
            seen_ids.add(q.id)
            unique_raw.append(q)
    print(f"  After dedup: {len(unique_raw)} unique questions\n")

    # ── STAGE 3: CLASSIFY ────────────────────────────────
    print("Stage 3: Classifying...")
    classified = []
    discarded_count = 0

    for raw_q in unique_raw:
        q_dict = {
            "id": raw_q.id,
            "text": raw_q.text,
            "normalized_text": raw_q.normalized_text,
            "source": raw_q.source,
            "source_url": raw_q.source_url,
            "source_context": raw_q.source_context,
            "upvotes": raw_q.upvotes,
            "reply_count": raw_q.reply_count,
            "harvested_at": raw_q.harvested_at,
        }
        result = classify_question(q_dict, taxonomy)
        if result.get("status") == "discarded":
            discarded_count += 1
        else:
            classified.append(result)

    print(f"  Classified: {len(classified)}, Discarded (no cluster): {discarded_count}\n")

    # ── STAGE 4: SCORE ───────────────────────────────────
    print("Stage 4: Scoring...")
    scored = []
    for q in classified:
        q = score_question(q, taxonomy, existing_posts)
        scored.append(q)

    avg_score = sum(q.get("score", 0) for q in scored) / max(len(scored), 1)
    print(f"  Average score: {avg_score:.1f}")
    print(f"  Score distribution:")
    print(f"    80+: {sum(1 for q in scored if q.get('score', 0) >= 80)}")
    print(f"    65-79: {sum(1 for q in scored if 65 <= q.get('score', 0) < 80)}")
    print(f"    45-64: {sum(1 for q in scored if 45 <= q.get('score', 0) < 65)}")
    print(f"    <45 (discarded): {sum(1 for q in scored if q.get('score', 0) < 45)}\n")

    if dry_run:
        print("DRY RUN — showing top 10 questions:")
        top = sorted(scored, key=lambda q: q.get("score", 0), reverse=True)[:10]
        for i, q in enumerate(top):
            print(f"  {i+1}. [{q.get('score', 0):.0f}] [{q.get('cluster_id', '')}] {q.get('text', '')[:80]}")
        return

    # ── STAGE 5: BUILD QUEUE ─────────────────────────────
    print("Stage 5: Building queue...")
    result = build_queue(scored, taxonomy, skill_text)

    # ── STAGE 6: MERGE INTO AQE QUEUE ───────────────────
    print("\nStage 6: Merging into shared queue...")
    aqe_queue = load_json(AQE_QUEUE_FILE) or {"queue": []}
    oqe_top = result["queue"][:20]  # Take top 20 from OQE

    existing_aqe_ids = {item.get("keyword", "") for item in aqe_queue.get("queue", [])}
    added_to_aqe = 0

    for q in oqe_top:
        keyword = q.get("suggested_title") or q.get("text", "")
        if keyword not in existing_aqe_ids:
            aqe_queue["queue"].append({
                "keyword": keyword,
                "cluster": q.get("cluster_id", ""),
                "priority": q.get("rank", 99),
                "source": "oqe",
                "oqe_score": q.get("score", 0),
            })
            existing_aqe_ids.add(keyword)
            added_to_aqe += 1

    aqe_queue["last_updated"] = datetime.now(timezone.utc).isoformat()

    with open(AQE_QUEUE_FILE, "w") as f:
        json.dump(aqe_queue, f, indent=2)

    print(f"  Added {added_to_aqe} OQE questions to shared blog queue")

    print(f"\n{'='*50}")
    print(f"✓ OQE complete")
    print(f"  Questions in OQE queue: {result['total_questions']}")
    print(f"  New this run: {result['added_this_run']}")
    print(f"  Added to blog queue: {added_to_aqe}")
    print(f"  Run 'python3 las_blog_build.py --from-queue --count 5' to publish")
    print(f"{'='*50}\n")


def show_status():
    """Show current queue status."""
    oqe_queue = load_json(OQE_QUEUE_FILE)
    aqe_queue = load_json(AQE_QUEUE_FILE)
    manifest = load_json(MANIFEST_FILE)

    print(f"\nOQE Status")
    print(f"  OQE queue: {len(oqe_queue.get('queue', []))} questions")
    print(f"  Blog queue (AQE+OQE): {len(aqe_queue.get('queue', []))} items")
    print(f"  Posts published: {len(manifest.get('posts', []))}")
    print(f"  Last updated: {oqe_queue.get('generated_at', 'never')}")

    print(f"\nTop 5 in OQE queue:")
    for q in oqe_queue.get("queue", [])[:5]:
        print(f"  [{q.get('score', 0):.0f}] [{q.get('cluster_id', '')}] {q.get('text', '')[:70]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Layer Advisory OQE Pipeline")
    parser.add_argument("--sources", nargs="+",
                        choices=["reddit", "google_paa", "indie_hackers", "all"],
                        default=["reddit", "google_paa", "indie_hackers"])
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run pipeline but don't write queue")
    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        sources = args.sources
        if "all" in sources:
            sources = ["reddit", "google_paa", "indie_hackers"]
        run_pipeline(sources, dry_run=args.dry_run)
