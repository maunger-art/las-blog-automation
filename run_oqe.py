#!/usr/bin/env python3
import argparse, json, os, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from oqe.sources.reddit import RedditSource
from oqe.sources.google_paa import GooglePAASource
from oqe.sources.indie_hackers import IndieHackersSource
from oqe.pipeline.classifier import classify_question
from oqe.scoring.scorer import score_question
from oqe.queue.queue_builder import build_queue

def _load(path):
    return json.loads(path.read_text()) if path.exists() else {}

def _keywords(taxonomy):
    kws = []
    for c in taxonomy.get("clusters",[]): kws.extend(c.get("keywords",[])); kws.append(c.get("pillar_keyword",""))
    return [k for k in kws if k]

def run(sources, dry_run=False):
    taxonomy = _load(ROOT/"taxonomy.json")
    manifest = _load(ROOT/"posts_manifest.json")
    skill_text = (ROOT/"SKILL.md").read_text() if (ROOT/"SKILL.md").exists() else ""
    posts = manifest.get("posts",[])
    keywords = _keywords(taxonomy)
    config = {
        "reddit": {"subreddits":["startups","Entrepreneur","smallbusiness","SaaS","nonprofit","Consulting","freelance","business"],"min_upvotes":3},
        "google_paa": {"serpapi_key":os.environ.get("SERPAPI_KEY",""),"max_per_keyword":8},
        "indie_hackers": {"max_results":40},
    }
    source_map = {"reddit":RedditSource,"google_paa":GooglePAASource,"indie_hackers":IndieHackersSource}
<<<<<<< HEAD
    print(f"\nOQE {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} sources:{sources}\n")
=======

    print(f"\nOQE — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  sources: {sources}\n")
>>>>>>> ab819d3 (OQE: first harvest)
    print("Stage 1: Harvesting...")
    raw = []
    for s in sources:
        if s in source_map: raw.extend(source_map[s](config.get(s,{})).harvest(keywords[:10]))
<<<<<<< HEAD
=======

>>>>>>> ab819d3 (OQE: first harvest)
    print(f"Stage 2: Deduplicating {len(raw)} raw...")
    seen, unique = set(), []
    for q in raw:
        if q.id not in seen: seen.add(q.id); unique.append(q)
<<<<<<< HEAD
=======

>>>>>>> ab819d3 (OQE: first harvest)
    print(f"Stage 3: Classifying {len(unique)}...")
    classified, disc = [], 0
    for q in unique:
        d = {"id":q.id,"text":q.text,"normalized_text":q.normalized_text,"source":q.source,"source_url":q.source_url,"source_context":q.source_context,"upvotes":q.upvotes,"reply_count":q.reply_count,"harvested_at":q.harvested_at}
        r = classify_question(d, taxonomy)
<<<<<<< HEAD
        if r.get("status")=="discarded": disc+=1
        else: classified.append(r)
    print(f"  Classified:{len(classified)} Discarded:{disc}")
    print("Stage 4: Scoring...")
    scored = [score_question(q,taxonomy,posts) for q in classified]
    avg = sum(q.get("score",0) for q in scored)/max(len(scored),1)
    print(f"  Avg score:{avg:.1f}")
    if dry_run:
        print("\nDRY RUN Top 10:")
        for i,q in enumerate(sorted(scored,key=lambda q:q.get("score",0),reverse=True)[:10]):
            print(f"  {i+1}.[{q.get('score',0):.0f}][{q.get('cluster_id','')}] {q.get('text','')[:75]}")
        return
    print("Stage 5: Building queue...")
    result = build_queue(scored, taxonomy, skill_text)
=======
        if r.get("status") == "discarded": disc += 1
        else: classified.append(r)
    print(f"  Classified: {len(classified)}, Discarded: {disc}")

    print("Stage 4: Scoring...")
    scored = [score_question(q, taxonomy, posts) for q in classified]
    avg = sum(q.get("score",0) for q in scored) / max(len(scored),1)
    print(f"  Avg score: {avg:.1f}")

    if dry_run:
        print("\nDRY RUN — Top 10:")
        for i,q in enumerate(sorted(scored, key=lambda q: q.get("score",0), reverse=True)[:10]):
            print(f"  {i+1}. [{q.get('score',0):.0f}] [{q.get('cluster_id','')}] {q.get('text','')[:75]}")
        return

    print("Stage 5: Building queue...")
    result = build_queue(scored, taxonomy, skill_text)

>>>>>>> ab819d3 (OQE: first harvest)
    print("Stage 6: Merging into blog queue...")
    aqe = _load(ROOT/"aqe_queue.json") or {"queue":[]}
    existing_kws = {i.get("keyword","") for i in aqe.get("queue",[])}
    added = 0
    for q in result["queue"][:20]:
        kw = q.get("suggested_title") or q.get("text","")
        if kw not in existing_kws:
<<<<<<< HEAD
            aqe["queue"].append({"keyword":kw,"cluster":q.get("cluster_id",""),"source":"oqe","oqe_score":q.get("score",0)})
            existing_kws.add(kw); added+=1
    aqe["last_updated"] = datetime.now(timezone.utc).isoformat()
    (ROOT/"aqe_queue.json").write_text(json.dumps(aqe,indent=2))
    print(f"\nOQE complete {result['total_questions']} in queue {added} added to blog queue")
=======
            aqe["queue"].append({"keyword":kw,"cluster":q.get("cluster_id",""),"priority":q.get("rank",99),"source":"oqe","oqe_score":q.get("score",0)})
            existing_kws.add(kw); added += 1
    aqe["last_updated"] = datetime.now(timezone.utc).isoformat()
    (ROOT/"aqe_queue.json").write_text(json.dumps(aqe, indent=2))
    print(f"\n✓ OQE complete — {result['total_questions']} in queue, {added} added to blog queue")
>>>>>>> ab819d3 (OQE: first harvest)

def status():
    oqe = _load(ROOT/"oqe"/"queue"/"question_queue.json")
    aqe = _load(ROOT/"aqe_queue.json")
    manifest = _load(ROOT/"posts_manifest.json")
<<<<<<< HEAD
    print(f"\nOQE:{len(oqe.get('queue',[]))} Blog queue:{len(aqe.get('queue',[]))} Published:{len(manifest.get('posts',[]))}")
=======
    print(f"\nOQE: {len(oqe.get('queue',[]))} | Blog queue: {len(aqe.get('queue',[]))} | Published: {len(manifest.get('posts',[]))}")
>>>>>>> ab819d3 (OQE: first harvest)
    for q in oqe.get("queue",[])[:5]:
        print(f"  [{q.get('score',0):.0f}] {q.get('text','')[:70]}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--sources", nargs="+", default=["reddit","google_paa","indie_hackers"])
    p.add_argument("--status", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if args.status: status()
    else:
        sources = ["reddit","google_paa","indie_hackers"] if "all" in args.sources else args.sources
        run(sources, dry_run=args.dry_run)
