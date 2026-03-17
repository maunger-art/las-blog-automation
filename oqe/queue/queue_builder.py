import json, re, os
from datetime import datetime, timezone
from pathlib import Path

QUEUE_FILE = Path(__file__).parent / "question_queue.json"
ARCHIVE_DIR = Path(__file__).parent / "archive"
ARCHIVE_DIR.mkdir(exist_ok=True)
MIN_SCORE = 45.0
MAX_PER_CLUSTER = 3

def _cluster_balance(qs, n=10):
    counts, top, rest = {}, [], []
    for q in qs:
        c = q.get("cluster_id","x"); cnt = counts.get(c,0)
        if len(top)<n and cnt<MAX_PER_CLUSTER: top.append(q); counts[c]=cnt+1
        else: rest.append(q)
    return top+rest

def _gen_titles(qs, skill_text):
    if not qs: return qs
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    qtext = "\n".join(f"{i+1}. [{q.get('cluster_id','')}] {q.get('text','')}" for i,q in enumerate(qs[:20]))
    resp = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=800,
        messages=[{"role":"user","content":f'Generate one compelling blog title per question. Voice: grounded, warm, no clickbait. Example: "The Real Cost of Being the Founder Bottleneck"\n\n{qtext}\n\nReturn ONLY a JSON array.'}])
    raw = resp.content[0].text.strip().strip("`").replace("json","",1).strip()
    try:
        titles = json.loads(raw)
        for i,q in enumerate(qs[:20]):
            if i<len(titles): q["suggested_title"]=titles[i]
    except: pass
    return qs

def build_queue(scored, taxonomy, skill_text=""):
    passing = [q for q in scored if q.get("score",0)>=MIN_SCORE]
    discarded = [q for q in scored if q.get("score",0)<MIN_SCORE]
    print(f"  Scoring: {len(passing)} passed, {len(discarded)} discarded")
    ranked = sorted(passing, key=lambda q:q.get("score",0), reverse=True)
    balanced = _cluster_balance(ranked)
    if skill_text: balanced = _gen_titles(balanced[:20],skill_text)+balanced[20:]
    existing = {}
    if QUEUE_FILE.exists():
        for item in json.loads(QUEUE_FILE.read_text()).get("queue",[]):
            existing[item.get("id","")] = item
    added = 0
    for q in balanced:
        qid = q.get("id","")
        if qid not in existing: existing[qid]=q; added+=1
    final = sorted(existing.values(), key=lambda q:q.get("score",0), reverse=True)
    for i,q in enumerate(final): q["rank"]=i+1
    out = {"generated_at":datetime.now(timezone.utc).isoformat(),"total_questions":len(final),"added_this_run":added,"queue":final}
    QUEUE_FILE.write_text(json.dumps(out,indent=2))
    print(f"  Queue: {len(final)} total ({added} new)")
    if discarded:
        (ARCHIVE_DIR/f"disc_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json").write_text(json.dumps(discarded,indent=2))
    return out
