import json
from datetime import datetime, timezone
from pathlib import Path

WEIGHTS_FILE = Path(__file__).parent / "weights.json"
HIGH_INTENT = ["how do i","how to","how can i","what is","what are","when should","should i hire","do i need"]
CONVERSION = ["should i hire","worth hiring","do i need a coo","what does a fractional","when to hire","need help with","overwhelmed"]
OPERATIONAL = ["operations","systems","processes","delegate","team","hire","coo","fractional","scale","accountability","okr","goals","align","bottleneck","founder","ceo","leadership","burnout","structure","workflow","capacity","client","revenue","growth","nonprofit","startup"]

def _weights():
    if WEIGHTS_FILE.exists(): return json.loads(WEIGHTS_FILE.read_text())
    return {k:1.0 for k in ["search_intent","operational_relevance","conversion_potential","recency","source_credibility"]}

def score_search_intent(q):
    t = q.get("normalized_text","").lower(); s = 0
    if any(t.startswith(x) for x in HIGH_INTENT): s += 12
    elif t.endswith("?"): s += 6
    if any(x in t for x in ["founder","ceo","startup","team","nonprofit","small business"]): s += 8
    if q.get("cluster_id"): s += 5
    return min(s, 25.0)

def score_relevance(q, taxonomy):
    t = q.get("normalized_text","").lower(); s = 0
    if q.get("cluster_id"): s += 15
    s += min(sum(1 for k in OPERATIONAL if k in t)*2, 6)
    if any(x in t for x in ["founder","ceo","our team","my team","i run","i own"]): s += 4
    return min(s, 25.0)

def score_conversion(q):
    t = q.get("normalized_text","").lower(); s = 0
    if any(p in t for p in CONVERSION): s += 12
    if any(x in t for x in ["10 people","20 people","growing","scaling","small team"]): s += 5
    if any(x in t for x in ["should i","do i need","worth it","help with"]): s += 3
    return min(s, 20.0)

def score_recency(q):
    ha = q.get("harvested_at","")
    if not ha: return 5.0
    try:
        d = (datetime.now(timezone.utc)-datetime.fromisoformat(ha.replace("Z","+00:00"))).days
        return 15.0 if d<=7 else 12.0 if d<=30 else 8.0 if d<=90 else 4.0 if d<=180 else 1.0
    except: return 5.0

def score_source(q):
    base = {"google_paa":12,"reddit":10,"indie_hackers":8,"quora":8,"podcast":8,"newsletter":5}.get(q.get("source",""),3)
    u = q.get("upvotes",0)
    return min(base+(3 if u>=100 else 2 if u>=20 else 1 if u>=5 else 0),15.0)

def score_duplicate(q, posts):
    words = set(q.get("normalized_text","").lower().split())
    max_ov = 0.0
    for p in posts:
        pw = set((p.get("title","")+" "+p.get("primary_keyword","")).lower().split())
        if pw: max_ov = max(max_ov, len(words&pw)/max(len(words),len(pw),1))
    return -20.0 if max_ov>=0.80 else -10.0 if max_ov>=0.60 else -5.0 if max_ov>=0.40 else 0.0

def score_question(q, taxonomy, posts):
    w = _weights()
    sb = {
        "search_intent": round(score_search_intent(q)*w.get("search_intent",1),1),
        "operational_relevance": round(score_relevance(q,taxonomy)*w.get("operational_relevance",1),1),
        "conversion_potential": round(score_conversion(q)*w.get("conversion_potential",1),1),
        "recency": round(score_recency(q)*w.get("recency",1),1),
        "source_credibility": round(score_source(q)*w.get("source_credibility",1),1),
        "duplicate_penalty": round(score_duplicate(q,posts),1),
    }
    q["score"] = round(max(0.0,min(100.0,sum(sb.values()))),1)
    q["score_breakdown"] = sb
    return q
