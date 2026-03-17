import urllib.request, json, re, os
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
<<<<<<< HEAD
        req = urllib.request.Request(url, headers={"User-Agent":"LayerAdvisoryOQE/1.0","Accept":"application/json"})
=======
        req = urllib.request.Request(url, headers={"User-Agent": "LayerAdvisoryOQE/1.0", "Accept": "application/json"})
>>>>>>> ab819d3 (OQE: first harvest)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        posts = data if isinstance(data, list) else data.get("posts", [])
        qs = []
        for p in posts[:40]:
            title = p.get("title", "").strip()
            if not title or not any(s.lower() in title.lower() for s in SIGNALS): continue
            qs.append(RawQuestion(text=title, source=self.name,
                source_url=f"https://indiehackers.com/post/{p.get('slug','')}",
<<<<<<< HEAD
                source_context="Indie Hackers", upvotes=p.get("votes",0),
                reply_count=p.get("commentsCount",0)))
=======
                source_context="Indie Hackers", upvotes=p.get("votes", 0),
                reply_count=p.get("commentsCount", 0)))
>>>>>>> ab819d3 (OQE: first harvest)
        return qs

    def _synthesize(self):
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
<<<<<<< HEAD
        resp = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=600,
            messages=[{"role":"user","content":"Generate 10 realistic questions founders and indie hackers ask about operations, team building, and scaling. Return ONLY a JSON array of strings."}])
        raw = resp.content[0].text.strip().strip('`').replace('json','',1).strip()
        return [RawQuestion(text=t, source=self.name,
            source_url="https://indiehackers.com",
            source_context="Indie Hackers synthesized", upvotes=15)
=======
        resp = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=600,
            messages=[{"role": "user", "content": "Generate 10 realistic questions indie hackers and founders ask about operations, team building, and scaling. Return ONLY a JSON array of strings."}])
        raw = re.sub(r'^```json\s*', '', resp.content[0].text.strip())
        raw = re.sub(r'\s*```$', '', raw)
        return [RawQuestion(text=t, source=self.name,
            source_url="https://indiehackers.com",
            source_context="Indie Hackers (synthesized)", upvotes=15)
>>>>>>> ab819d3 (OQE: first harvest)
            for t in json.loads(raw)]
