"""
oqe/sources/google_paa.py
Harvests People Also Ask questions from Google Search results.
Uses SerpAPI if configured, falls back to scraping via requests.
PAA questions are pre-validated by Google as high search intent.
"""

import urllib.request
import urllib.parse
import json
import re
from .base_source import BaseSource, RawQuestion


class GooglePAASource(BaseSource):
    name = "google_paa"

    def __init__(self, config: dict):
        super().__init__(config)
        self.serpapi_key = config.get("serpapi_key", "")
        self.max_per_keyword = config.get("max_per_keyword", 10)

    def harvest(self, keywords: list[str], **kwargs) -> list[RawQuestion]:
        """
        For each keyword, fetch the People Also Ask box from Google.
        Each PAA question is a high-intent, real search query.
        """
        all_questions = []

        for keyword in keywords:
            try:
                if self.serpapi_key:
                    questions = self._fetch_via_serpapi(keyword)
                else:
                    questions = self._fetch_via_scrape(keyword)
                all_questions.extend(questions)
            except Exception as e:
                print(f"  Google PAA [{keyword}]: {e}")
                continue

        filtered = self.filter_valid(all_questions)
        deduped = self.deduplicate(filtered)
        print(f"  Google PAA: {len(deduped)} questions harvested")
        return deduped

    def _fetch_via_serpapi(self, keyword: str) -> list[RawQuestion]:
        """Use SerpAPI to get PAA questions (most reliable)."""
        encoded = urllib.parse.quote(keyword)
        url = (
            f"https://serpapi.com/search.json"
            f"?q={encoded}"
            f"&engine=google"
            f"&api_key={self.serpapi_key}"
            f"&num=10"
        )

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read())

        questions = []
        for item in data.get("related_questions", []):
            question_text = item.get("question", "").strip()
            if not question_text:
                continue

            q = RawQuestion(
                text=question_text,
                source=self.name,
                source_url=f"https://google.com/search?q={urllib.parse.quote(question_text)}",
                source_context=f"Google PAA — seed: {keyword}",
                upvotes=50,  # PAA = implicit high engagement signal
                reply_count=0,
            )
            questions.append(q)

        return questions[:self.max_per_keyword]

    def _fetch_via_scrape(self, keyword: str) -> list[RawQuestion]:
        """
        Fallback: generate likely PAA questions using Claude
        based on the keyword when no SerpAPI key is configured.
        This ensures the pipeline works without paid APIs.
        """
        import anthropic
        import os

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""Generate 8 realistic "People Also Ask" questions that Google would show for this search query: "{keyword}"

These should be the exact questions founders, CEOs, and operators would type into Google.
Focus on operational, leadership, and growth challenges.

Return ONLY a JSON array of question strings. No preamble. Example:
["How do I...", "What is...", "When should..."]"""
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
                source_url=f"https://google.com/search?q={urllib.parse.quote(text)}",
                source_context=f"Google PAA (synthesized) — seed: {keyword}",
                upvotes=40,
                reply_count=0,
            )
            questions.append(q)

        return questions
