import urllib.request, urllib.parse, json, re, os
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
            source_context=f"Google PAA", upvotes=50)
            for i in data.get("related_questions", []) if i.get("question")][:self.max_per]

    def _via_claude(self, keyword):
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        resp = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=500,
            messages=[{"role":"user","content":f'Generate 8 realistic People Also Ask questions for: "{keyword}". Founders and operators. Return ONLY a JSON array of strings.'}])
        raw = re.sub(r'^```json\s*', '', resp.content[0].text.strip())
        raw = re.sub(r'\s*```$', '', raw)
        return [RawQuestion(text=t, source=self.name,
            source_url=f"https://google.com/search?q={urllib.parse.quote(t)}",
            source_context=f"Google PAA synthesized", upvotes=40)
            for t in json.loads(raw)]
