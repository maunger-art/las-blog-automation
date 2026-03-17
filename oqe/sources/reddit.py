import time, urllib.request, urllib.parse, json
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
