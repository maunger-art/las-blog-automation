#!/usr/bin/env python3
"""
write_oqe.py
Run this from inside ~/Desktop/las-blog-automation/ to write all OQE files.
"""
import pathlib

ROOT = pathlib.Path(".")

def write(path, content):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    print(f"  ✓ {path}")

# ── base_source.py ────────────────────────────────────────────────────────────
write("oqe/sources/base_source.py", """from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib, re

@dataclass
class RawQuestion:
    text: str
    source: str
    source_url: str = ""
    source_context: str = ""
    upvotes: int = 0
    reply_count: int = 0
    harvested_at: str = ""

    def __post_init__(self):
        if not self.harvested_at:
            self.harvested_at = datetime.now(timezone.utc).isoformat()

    @property
    def id(self):
        return hashlib.sha256(self.normalized_text.encode()).hexdigest()[:16]

    @property
    def normalized_text(self):
        t = self.text.lower().strip()
        t = re.sub(r'[^\\w\\s]', ' ', t)
        return re.sub(r'\\s+', ' ', t).strip()

    def is_valid_question(self):
        t = self.text.strip()
        if len(t) < 15 or len(t) > 350:
            return False
        starters = ('how','what','when','why','should','can','is','are','do','does','will','would','which','who')
        return any(t.lower().startswith(s) for s in starters) or t.endswith('?')

class BaseSource(ABC):
    name = "base"
    def __init__(self, config):
        self.config = config
    @abstractmethod
    def harvest(self, keywords, **kwargs): pass
    def filter_valid(self, questions):
        return [q for q in questions if q.is_valid_question()]
    def deduplicate(self, questions):
        seen, unique = set(), []
        for q in questions:
            if q.id not in seen:
                seen.add(q.id)
                unique.append(q)
        return unique
""")

# ── reddit.py ─────────────────────────────────────────────────────────────────
write("oqe/sources/reddit.py", """import time, urllib.request, urllib.parse, json
from .base_source import BaseSource, RawQuestion

SUBREDDITS = ["startups","Entrepreneur","smallbusiness","SaaS","nonprofit","Consulting","freelance","business","EntrepreneurRideAlong"]
SIGNALS = ["COO","operations","systems","processes","delegate","team","hire","founder","CEO","scale","scaling","overwhelmed","burnout","structure","accountability","fractional","bottleneck","capacity","workflow"]

class RedditSource(BaseSource):
    name = "reddit"
    def __init__(self, config):
        super().__init__(config)
        self.subreddits = config.get("subreddits", SUBREDDITS)
        self.min_upvotes = config.get("min_upvotes", 3)

    def harvest(self, keywords, **kwargs):
        all_q = []
        for sub in self.subreddits:
            try: all_q.extend(self._fetch(sub)); time.sleep(1.5)
            except Exception as e: print(f"  Reddit [{sub}]: {e}")
        for kw in keywords[:5]:
            try: all_q.extend(self._search(kw)); time.sleep(2)
            except Exception as e: print(f"  Reddit search [{kw}]: {e}")
        result = self.deduplicate(self.filter_valid(all_q))
        print(f"  Reddit: {len(result)} questions")
        return result

    def _fetch(self, sub):
        url = f"https://www.reddit.com/r/{sub}/hot.json?limit=50"
        req = urllib.request.Request(url, headers={"User-Agent": "LayerAdvisoryOQE/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        qs = []
        for p in data.get("data", {}).get("children", []):
            d = p.get("data", {})
            title = d.get("title", "").strip()
            if d.get("score", 0) < self.min_upvotes: continue
            if not any(s.lower() in title.lower() for s in SIGNALS): continue
            qs.append(RawQuestion(text=title, source=self.name,
                source_url=f"https://reddit.com{d.get('permalink','')}",
                source_context=f"r/{sub}", upvotes=d.get("score", 0),
                reply_count=d.get("num_comments", 0)))
        return qs

    def _search(self, keyword):
        enc = urllib.parse.quote(keyword)
        url = f"https://www.reddit.com/search.json?q={enc}&type=link&sort=relevance&limit=25&t=year"
        req = urllib.request.Request(url, headers={"User-Agent": "LayerAdvisoryOQE/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        qs = []
        for p in data.get("data", {}).get("children", []):
            d = p.get("data", {})
            qs.append(RawQuestion(text=d.get("title", "").strip(), source=self.name,
                source_url=f"https://reddit.com{d.get('permalink','')}",
                source_context=f"r/{d.get('subreddit','')} search:{keyword}",
                upvotes=d.get("score", 0), reply_count=d.get("num_comments", 0)))
        return qs
""")

# ── google_paa.py ─────────────────────────────────────────────────────────────
write("oqe/sources/google_paa.py", """import urllib.request, urllib.parse, json, re, os
from .base_source import BaseSource, RawQuestion

class GooglePAASource(BaseSource):
    name = "google_paa"
    def __init__(self, config):
        super().__init__(config)
        self.serpapi_key = config.get("serpapi_key", "")
        self.max_per = config.get("max_per_keyword", 8)

    def harvest(self, keywords, **kwargs):
        all_q = []
        for kw in keywords:
            try:
                qs = self._via_serpapi(kw) if self.serpapi_key else self._via_claude(kw)
                all_q.extend(qs)
            except Exception as e:
                print(f"  Google PAA [{kw}]: {e}")
        result = self.deduplicate(self.filter_valid(all_q))
        print(f"  Google PAA: {len(result)} questions")
        return result

    def _via_serpapi(self, keyword):
        enc = urllib.parse.quote(keyword)
        url = f"https://serpapi.com/search.json?q={enc}&engine=google&api_key={self.serpapi_key}"
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read())
        return [RawQuestion(text=i.get("question", ""), source=self.name,
            source_url=f"https://google.com/search?q={urllib.parse.quote(i.get('question',''))}",
            source_context=f"Google PAA — {keyword}", upvotes=50)
            for i in data.get("related_questions", []) if i.get("question")][:self.max_per]

    def _via_claude(self, keyword):
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        resp = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=500,
            messages=[{"role": "user", "content": f'Generate 8 realistic "People Also Ask" questions for: "{keyword}". Focus on founders and operators. Return ONLY a JSON array of strings.'}])
        raw = re.sub(r'^```json\\s*', '', resp.content[0].text.strip())
        raw = re.sub(r'\\s*```$', '', raw)
        return [RawQuestion(text=t, source=self.name,
            source_url=f"https://google.com/search?q={urllib.parse.quote(t)}",
            source_context=f"Google PAA (synthesized) — {keyword}", upvotes=40)
            for t in json.loads(raw)]
""")

# ── indie_hackers.py ──────────────────────────────────────────────────────────
write("oqe/sources/indie_hackers.py", """import urllib.request, json, re, os
from .base_source import BaseSource, RawQuestion

SIGNALS = ["operations","team","hire","delegate","systems","scale","overwhelm","structure","fractional","founder","revenue","client","growth"]

class IndieHackersSource(BaseSource):
    name = "indie_hackers"
    def harvest(self, keywords, **kwargs):
        all_q = []
        try: all_q.extend(self._fetch())
        except: all_q.extend(self._synthesize())
        result = self.deduplicate(self.filter_valid(all_q))
        print(f"  Indie Hackers: {len(result)} questions")
        return result

    def _fetch(self):
        url = "https://www.indiehackers.com/posts.json?limit=50&type=question"
        req = urllib.request.Request(url, headers={"User-Agent": "LayerAdvisoryOQE/1.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        posts = data if isinstance(data, list) else data.get("posts", [])
        qs = []
        for p in posts[:40]:
            title = p.get("title", "").strip()
            if not title or not any(s.lower() in title.lower() for s in SIGNALS): continue
            qs.append(RawQuestion(text=title, source=self.name,
                source_url=f"https://indiehackers.com/post/{p.get('slug','')}",
                source_context="Indie Hackers", upvotes=p.get("votes", 0),
                reply_count=p.get("commentsCount", 0)))
        return qs

    def _synthesize(self):
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        resp = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=600,
            messages=[{"role": "user", "content": "Generate 10 realistic questions indie hackers and founders ask about operations, team building, and scaling. Return ONLY a JSON array of strings."}])
        raw = re.sub(r'^```json\\s*', '', resp.content[0].text.strip())
        raw = re.sub(r'\\s*```$', '', raw)
        return [RawQuestion(text=t, source=self.name,
            source_url="https://indiehackers.com",
            source_context="Indie Hackers (synthesized)", upvotes=15)
            for t in json.loads(raw)]
""")

# ── classifier.py ─────────────────────────────────────────────────────────────
write("oqe/pipeline/classifier.py", """CLUSTER_SIGNALS = {
    "founder-dependency": ["bottleneck","everything through me","cant delegate","doing everything","stop being the bottleneck","depends on me","founder dependency","letting go","micromanage","trust my team","step back"],
    "operational-clarity": ["process","processes","documentation","sop","standard operating","systems","workflow","how we work","consistency","documented","playbook","handbook"],
    "team-alignment": ["align","alignment","okr","goals","priorities","team meeting","quarterly","accountability","scorecard","decision","communication","same page"],
    "fractional-leadership": ["fractional coo","fractional executive","part time coo","what is a fractional","hire a fractional","need a coo","do i need a coo"],
    "sustainable-growth": ["scale","scaling","growing too fast","overwhelmed","burnout","sustainable","capacity","too much on my plate","prioritize","focus","growth feels chaotic"],
    "hiring-and-roles": ["hire","hiring","first hire","job description","role clarity","accountability chart","onboarding","retain","retention","turnover","right person","right seat"],
    "leadership-mindset": ["leadership","founder mindset","ceo mindset","confidence","burnout","work life balance","habits","productivity","decision making","slack time"],
}

CONTENT_TYPES = {
    "how-to": ["how do i","how to","how can i","how should i","steps to"],
    "what-is": ["what is","what are","what does","whats the difference","explain"],
    "when-to": ["when should","when do i","when is the right time"],
    "comparison": ["vs ","versus","difference between","which is"],
    "story": ["why does","why is","why do","why cant"],
}

TOOL_LINKS = {
    "fractional-leadership": {"tool_id":"diagnostic-assessment","tool_url":"https://layeradvisory.com/#diagnostic","cta_copy":"Not sure if you need a fractional COO? Take the 5-minute diagnostic."},
    "founder-dependency": {"tool_id":"diagnostic-assessment","tool_url":"https://layeradvisory.com/#diagnostic","cta_copy":"Find out where founder dependency is costing you most."},
    "operational-clarity": {"tool_id":"diagnostic-assessment","tool_url":"https://layeradvisory.com/#diagnostic","cta_copy":"Discover which operational gaps are slowing your team down."},
}

def match_cluster(text, taxonomy):
    tl = text.lower()
    scores = {}
    for cid, signals in CLUSTER_SIGNALS.items():
        h = sum(1 for s in signals if s in tl)
        if h > 0: scores[cid] = h
    if scores: return max(scores, key=scores.get)
    for c in taxonomy.get("clusters", []):
        h = sum(1 for k in c.get("keywords", []) if k.lower() in tl)
        if h > 0: scores[c["id"]] = h
    return max(scores, key=scores.get) if scores else None

def infer_content_type(text):
    tl = text.lower()
    for ct, signals in CONTENT_TYPES.items():
        if any(tl.startswith(s) or s in tl for s in signals): return ct
    return "how-to"

def classify_question(question, taxonomy):
    text = question.get("normalized_text", question.get("text", ""))
    cid = match_cluster(text, taxonomy)
    if not cid:
        question["status"] = "discarded"
        question["discard_reason"] = "no cluster match"
        return question
    question["cluster_id"] = cid
    question["content_type"] = infer_content_type(text)
    question["tool_link"] = TOOL_LINKS.get(cid)
    question["status"] = "classified"
    return question
""")

# ── scorer.py ─────────────────────────────────────────────────────────────────
write("oqe/scoring/scorer.py", """import json
from datetime import datetime, timezone
from pathlib import Path

WEIGHTS_FILE = Path(__file__).parent / "weights.json"
HIGH_INTENT = ["how do i","how to","how can i","what is","what are","when should","should i hire","do i need","is it worth"]
CONVERSION = ["should i hire","worth hiring","do i need a coo","what does a fractional","how much does a fractional","when to hire","need help with","overwhelmed"]
OPERATIONAL = ["operations","systems","processes","delegate","team","hire","coo","fractional","scale","accountability","okr","goals","align","bottleneck","founder","ceo","leadership","burnout","structure","workflow","capacity","client","revenue","growth","nonprofit","startup"]

def _weights():
    if WEIGHTS_FILE.exists(): return json.loads(WEIGHTS_FILE.read_text())
    return {k: 1.0 for k in ["search_intent","operational_relevance","conversion_potential","recency","source_credibility"]}

def score_search_intent(q):
    t = q.get("normalized_text", "").lower(); s = 0
    if any(t.startswith(x) for x in HIGH_INTENT): s += 12
    elif t.endswith("?"): s += 6
    if any(x in t for x in ["founder","ceo","startup","team","nonprofit","small business"]): s += 8
    if q.get("cluster_id"): s += 5
    return min(s, 25.0)

def score_relevance(q, taxonomy):
    t = q.get("normalized_text", "").lower(); s = 0
    if q.get("cluster_id"): s += 15
    s += min(sum(1 for k in OPERATIONAL if k in t) * 2, 6)
    if any(x in t for x in ["founder","ceo","our team","my team","i run","i own","i lead"]): s += 4
    return min(s, 25.0)

def score_conversion(q):
    t = q.get("normalized_text", "").lower(); s = 0
    if any(p in t for p in CONVERSION): s += 12
    if any(x in t for x in ["10 people","20 people","series a","growing","scaling","small team"]): s += 5
    if any(x in t for x in ["should i","do i need","worth it","help with"]): s += 3
    return min(s, 20.0)

def score_recency(q):
    ha = q.get("harvested_at", "")
    if not ha: return 5.0
    try:
        d = (datetime.now(timezone.utc) - datetime.fromisoformat(ha.replace("Z", "+00:00"))).days
        return 15.0 if d<=7 else 12.0 if d<=30 else 8.0 if d<=90 else 4.0 if d<=180 else 1.0
    except: return 5.0

def score_source(q):
    base = {"google_paa":12,"reddit":10,"indie_hackers":8,"quora":8,"podcast":8,"newsletter":5}.get(q.get("source",""), 3)
    u = q.get("upvotes", 0)
    return min(base + (3 if u>=100 else 2 if u>=20 else 1 if u>=5 else 0), 15.0)

def score_duplicate(q, posts):
    words = set(q.get("normalized_text", "").lower().split())
    max_ov = 0.0
    for p in posts:
        pw = set((p.get("title","") + " " + p.get("primary_keyword","")).lower().split())
        if pw: max_ov = max(max_ov, len(words & pw) / max(len(words), len(pw), 1))
    return -20.0 if max_ov>=0.80 else -10.0 if max_ov>=0.60 else -5.0 if max_ov>=0.40 else 0.0

def score_question(q, taxonomy, posts):
    w = _weights()
    sb = {
        "search_intent": round(score_search_intent(q) * w.get("search_intent",1), 1),
        "operational_relevance": round(score_relevance(q, taxonomy) * w.get("operational_relevance",1), 1),
        "conversion_potential": round(score_conversion(q) * w.get("conversion_potential",1), 1),
        "recency": round(score_recency(q) * w.get("recency",1), 1),
        "source_credibility": round(score_source(q) * w.get("source_credibility",1), 1),
        "duplicate_penalty": round(score_duplicate(q, posts), 1),
    }
    q["score"] = round(max(0.0, min(100.0, sum(sb.values()))), 1)
    q["score_breakdown"] = sb
    return q
""")

# ── weights.json ──────────────────────────────────────────────────────────────
write("oqe/scoring/weights.json", '{"search_intent":1.0,"operational_relevance":1.0,"conversion_potential":1.0,"recency":1.0,"source_credibility":1.0}')

# ── queue_builder.py ──────────────────────────────────────────────────────────
write("oqe/queue/queue_builder.py", """import json, re, os
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
        c = q.get("cluster_id", "x"); cnt = counts.get(c, 0)
        if len(top) < n and cnt < MAX_PER_CLUSTER:
            top.append(q); counts[c] = cnt + 1
        else: rest.append(q)
    return top + rest

def _gen_titles(qs, skill_text):
    if not qs: return qs
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    qtext = "\\n".join(f"{i+1}. [{q.get('cluster_id','')}] {q.get('text','')}" for i,q in enumerate(qs[:20]))
    resp = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=800,
        messages=[{"role":"user","content":f'Generate one compelling blog title for each question. Voice: grounded, warm, no clickbait. Good examples: "The Real Cost of Being the Founder Bottleneck", "Slack Time Is Not Wasted Time"\\n\\n{qtext}\\n\\nReturn ONLY a JSON array.'}])
    raw = re.sub(r'^```json\\s*', '', resp.content[0].text.strip())
    raw = re.sub(r'\\s*```$', '', raw)
    titles = json.loads(raw)
    for i, q in enumerate(qs[:20]):
        if i < len(titles): q["suggested_title"] = titles[i]
    return qs

def build_queue(scored, taxonomy, skill_text=""):
    passing = [q for q in scored if q.get("score",0) >= MIN_SCORE]
    discarded = [q for q in scored if q.get("score",0) < MIN_SCORE]
    print(f"  Scoring: {len(passing)} passed, {len(discarded)} discarded")
    ranked = sorted(passing, key=lambda q: q.get("score",0), reverse=True)
    balanced = _cluster_balance(ranked)
    if skill_text: balanced = _gen_titles(balanced[:20], skill_text) + balanced[20:]
    existing = {}
    if QUEUE_FILE.exists():
        for item in json.loads(QUEUE_FILE.read_text()).get("queue", []):
            existing[item.get("id","")] = item
    added = 0
    for q in balanced:
        qid = q.get("id","")
        if qid not in existing: existing[qid] = q; added += 1
    final = sorted(existing.values(), key=lambda q: q.get("score",0), reverse=True)
    for i, q in enumerate(final): q["rank"] = i + 1
    out = {"generated_at": datetime.now(timezone.utc).isoformat(), "total_questions": len(final), "added_this_run": added, "queue": final}
    QUEUE_FILE.write_text(json.dumps(out, indent=2))
    print(f"  Queue: {len(final)} total ({added} new)")
    if discarded:
        (ARCHIVE_DIR / f"disc_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json").write_text(json.dumps(discarded, indent=2))
    return out
""")

# ── run_oqe.py ────────────────────────────────────────────────────────────────
write("run_oqe.py", """#!/usr/bin/env python3
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

    print(f"\\nOQE — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  sources: {sources}\\n")
    print("Stage 1: Harvesting...")
    raw = []
    for s in sources:
        if s in source_map: raw.extend(source_map[s](config.get(s,{})).harvest(keywords[:10]))

    print(f"Stage 2: Deduplicating {len(raw)} raw...")
    seen, unique = set(), []
    for q in raw:
        if q.id not in seen: seen.add(q.id); unique.append(q)

    print(f"Stage 3: Classifying {len(unique)}...")
    classified, disc = [], 0
    for q in unique:
        d = {"id":q.id,"text":q.text,"normalized_text":q.normalized_text,"source":q.source,"source_url":q.source_url,"source_context":q.source_context,"upvotes":q.upvotes,"reply_count":q.reply_count,"harvested_at":q.harvested_at}
        r = classify_question(d, taxonomy)
        if r.get("status") == "discarded": disc += 1
        else: classified.append(r)
    print(f"  Classified: {len(classified)}, Discarded: {disc}")

    print("Stage 4: Scoring...")
    scored = [score_question(q, taxonomy, posts) for q in classified]
    avg = sum(q.get("score",0) for q in scored) / max(len(scored),1)
    print(f"  Avg score: {avg:.1f}")

    if dry_run:
        print("\\nDRY RUN — Top 10:")
        for i,q in enumerate(sorted(scored, key=lambda q: q.get("score",0), reverse=True)[:10]):
            print(f"  {i+1}. [{q.get('score',0):.0f}] [{q.get('cluster_id','')}] {q.get('text','')[:75]}")
        return

    print("Stage 5: Building queue...")
    result = build_queue(scored, taxonomy, skill_text)

    print("Stage 6: Merging into blog queue...")
    aqe = _load(ROOT/"aqe_queue.json") or {"queue":[]}
    existing_kws = {i.get("keyword","") for i in aqe.get("queue",[])}
    added = 0
    for q in result["queue"][:20]:
        kw = q.get("suggested_title") or q.get("text","")
        if kw not in existing_kws:
            aqe["queue"].append({"keyword":kw,"cluster":q.get("cluster_id",""),"priority":q.get("rank",99),"source":"oqe","oqe_score":q.get("score",0)})
            existing_kws.add(kw); added += 1
    aqe["last_updated"] = datetime.now(timezone.utc).isoformat()
    (ROOT/"aqe_queue.json").write_text(json.dumps(aqe, indent=2))
    print(f"\\n✓ OQE complete — {result['total_questions']} in queue, {added} added to blog queue")

def status():
    oqe = _load(ROOT/"oqe"/"queue"/"question_queue.json")
    aqe = _load(ROOT/"aqe_queue.json")
    manifest = _load(ROOT/"posts_manifest.json")
    print(f"\\nOQE: {len(oqe.get('queue',[]))} | Blog queue: {len(aqe.get('queue',[]))} | Published: {len(manifest.get('posts',[]))}")
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
""")

# ── GitHub Actions workflow ───────────────────────────────────────────────────
write(".github/workflows/oqe_pipeline.yml", """name: OQE Pipeline - Layer Advisory

on:
  schedule:
    - cron: '0 5 * * 6'
  workflow_dispatch:
    inputs:
      sources:
        description: 'Sources (space-separated)'
        required: false
        default: 'reddit google_paa indie_hackers'

jobs:
  run-oqe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install anthropic
      - name: Run OQE
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SERPAPI_KEY: ${{ secrets.SERPAPI_KEY }}
        run: python3 run_oqe.py --sources ${{ github.event.inputs.sources || 'reddit google_paa indie_hackers' }}
      - run: |
          git config --global user.name "Layer Advisory Bot"
          git config --global user.email "bot@layeradvisory.com"
          git add -A
          git diff --staged --quiet || git commit -m "OQE: harvest $(date +'%Y-%m-%d')"
          git push
""")

print("\n✓ All OQE files written successfully.")
print("\nNext steps:")
print("  1. Test:  ANTHROPIC_API_KEY=your-key python3 run_oqe.py --sources reddit google_paa --dry-run")
print("  2. Push:  git add -A && git commit -m 'Add: OQE' && git push origin main")
