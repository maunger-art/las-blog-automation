#!/usr/bin/env python3
"""
Layer Advisory Services — Adaptive Question Engine (AQE)
Generates a prioritized queue of blog post keywords from the taxonomy.

Usage:
  python las_aqe_pipeline.py --generate --count 20
  python las_aqe_pipeline.py --status
"""

import os
import json
import argparse
import random
from datetime import datetime, timezone
from pathlib import Path
import anthropic

ROOT = Path(__file__).parent
TAXONOMY_FILE = ROOT / "taxonomy.json"
QUEUE_FILE = ROOT / "aqe_queue.json"
MANIFEST_FILE = ROOT / "posts_manifest.json"

def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def generate_queue(taxonomy, manifest, count=20):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    existing_keywords = {p.get("primary_keyword", "") for p in manifest.get("posts", [])}
    existing_slugs = {p.get("slug", "") for p in manifest.get("posts", [])}

    all_candidates = []
    for cluster in taxonomy.get("clusters", []):
        cluster_id = cluster["id"]
        for kw in cluster.get("keywords", []):
            if kw not in existing_keywords:
                all_candidates.append({
                    "keyword": kw,
                    "cluster": cluster_id,
                    "cluster_name": cluster["name"]
                })
        for q in cluster.get("question_types", []):
            all_candidates.append({
                "keyword": q,
                "cluster": cluster_id,
                "cluster_name": cluster["name"],
                "type": "question"
            })

    # Ask Claude to prioritize by SEO potential and content freshness
    candidates_text = "\n".join(
        f"- [{c['cluster']}] {c['keyword']}" for c in all_candidates[:60]
    )

    existing_text = "\n".join(f"- {k}" for k in list(existing_keywords)[:20]) or "None yet"

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": f"""You are an SEO content strategist for Layer Advisory Services, a Fractional COO practice.

Select the {count} best keywords/questions to publish as blog posts next, in priority order.

CRITERIA:
- Highest search intent match for founders and CEOs of growing startups/nonprofits
- Topical diversity (don't pick 5 from the same cluster in a row)
- Mix of informational (how-to, what-is) and navigational (best approach, when to)
- Prioritize keywords that show buying intent or high pain

ALREADY PUBLISHED (do not repeat):
{existing_text}

CANDIDATES:
{candidates_text}

Return ONLY a JSON array of objects like this, no preamble:
[
  {{"keyword": "exact keyword text", "cluster": "cluster-id", "priority": 1}},
  ...
]"""
        }]
    )

    raw = response.content[0].text.strip()
    import re
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    items = json.loads(raw)
    return items

def run(args):
    taxonomy = load_json(TAXONOMY_FILE)
    manifest = load_json(MANIFEST_FILE) or {"posts": []}
    queue = load_json(QUEUE_FILE) or {"queue": [], "last_updated": None}

    if args.status:
        print(f"Queue length: {len(queue.get('queue', []))}")
        print(f"Posts published: {len(manifest.get('posts', []))}")
        print(f"Last updated: {queue.get('last_updated', 'never')}")
        print("\nNext 5 in queue:")
        for item in queue.get("queue", [])[:5]:
            print(f"  [{item['cluster']}] {item['keyword']}")
        return

    if args.generate:
        count = args.count or 20
        print(f"Generating {count} prioritized keywords...")
        items = generate_queue(taxonomy, manifest, count)

        # Append to existing queue (avoid duplication)
        existing_kws = {i["keyword"] for i in queue.get("queue", [])}
        added = 0
        for item in items:
            if item["keyword"] not in existing_kws:
                queue["queue"].append(item)
                added += 1

        queue["last_updated"] = datetime.now(timezone.utc).isoformat()
        save_json(QUEUE_FILE, queue)
        print(f"✓ Added {added} items to queue. Total: {len(queue['queue'])}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Layer Advisory AQE Pipeline")
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--count", type=int, default=20)
    args = parser.parse_args()
    run(args)
