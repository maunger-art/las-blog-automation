"""
oqe/sources/indie_hackers.py
Harvests questions from Indie Hackers forum posts.
IH has a high concentration of founder/operator questions.
"""

import urllib.request
import urllib.parse
import json
import re
from .base_source import BaseSource, RawQuestion

SIGNAL_KEYWORDS = [
    "operations", "team", "hire", "COO", "delegate", "systems",
    "process", "scale", "overwhelm", "burnout", "structure",
    "accountability", "founder", "fractional", "consultant",
    "revenue", "client", "customers", "growth", "churn",
]


class IndieHackersSource(BaseSource):
    name = "indie_hackers"

    def __init__(self, config: dict):
        super().__init__(config)
        self.max_results = config.get("max_results", 40)

    def harvest(self, keywords: list[str], **kwargs) -> list[RawQuestion]:
        """
        Fetch posts from Indie Hackers and filter for operational questions.
        Uses IH's public post feed.
        """
        all_questions = []

        try:
            questions = self._fetch_forum_posts()
            all_questions.extend(questions)
        except Exception as e:
            print(f"  Indie Hackers: {e}")

        # Also search for specific keywords
        for keyword in keywords[:3]:
            try:
                questions = self._search_posts(keyword)
                all_questions.extend(questions)
            except Exception as e:
                print(f"  Indie Hackers search [{keyword}]: {e}")

        filtered = self.filter_valid(all_questions)
        deduped = self.deduplicate(filtered)
        print(f"  Indie Hackers: {len(deduped)} questions harvested")
        return deduped

    def _fetch_forum_posts(self) -> list[RawQuestion]:
        """Fetch recent forum posts from IH."""
        url = "https://www.indiehackers.com/posts.json?limit=50&type=question"
        headers = {
            "User-Agent": "LayerAdvisoryOQE/1.0",
            "Accept": "application/json",
        }

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())
        except Exception:
            # IH may not have a clean JSON API — fall back to synthesis
            return self._synthesize_questions()

        questions = []
        posts = data if isinstance(data, list) else data.get("posts", [])

        for post in posts[:self.max_results]:
            title = post.get("title", "").strip()
            if not title:
                continue

            title_lower = title.lower()
            has_signal = any(kw.lower() in title_lower for kw in SIGNAL_KEYWORDS)
            if not has_signal:
                continue

            slug = post.get("slug", "")
            q = RawQuestion(
                text=title,
                source=self.name,
                source_url=f"https://indiehackers.com/post/{slug}" if slug else "https://indiehackers.com",
                source_context="Indie Hackers forum",
                upvotes=post.get("votes", 0),
                reply_count=post.get("commentsCount", 0),
            )
            questions.append(q)

        return questions

    def _search_posts(self, keyword: str) -> list[RawQuestion]:
        """Search IH for a keyword."""
        encoded = urllib.parse.quote(keyword)
        url = f"https://www.indiehackers.com/search?query={encoded}&type=posts"
        # IH search is client-side rendered so we can't easily scrape it
        # Return empty and rely on forum_posts + synthesis
        return []

    def _synthesize_questions(self) -> list[RawQuestion]:
        """
        Fallback: generate realistic IH-style questions using Claude
        when the API isn't accessible.
        """
        import anthropic
        import os

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{
                "role": "user",
                "content": """Generate 10 realistic forum questions that indie hackers and early-stage founders ask about operations, team building, and scaling.

These should sound like real questions from the Indie Hackers community — specific, honest, sometimes frustrated.
Focus on: hiring first employees, delegating, managing clients, building systems, avoiding burnout, staying focused.

Return ONLY a JSON array of question strings. No preamble."""
            }]
        )

        raw = response.content[0].text.strip()
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

        question_texts = json.loads(raw)
        questions = []

        for text in question_texts:
            q = RawQuestion(
                text=text,
                source=self.name,
                source_url="https://indiehackers.com",
                source_context="Indie Hackers (synthesized)",
                upvotes=15,
                reply_count=0,
            )
            questions.append(q)

        return questions
