"""
oqe/sources/reddit.py
Harvests questions from founder/operator subreddits using Reddit's public JSON API.
No API key required for read-only access.
"""

import time
import urllib.request
import urllib.parse
import json
from .base_source import BaseSource, RawQuestion

# Subreddits most relevant to Layer Advisory's audience
DEFAULT_SUBREDDITS = [
    "startups",
    "Entrepreneur",
    "smallbusiness",
    "SaaS",
    "nonprofit",
    "Consulting",
    "freelance",
    "business",
    "Accounting",
    "legaladvice",
]

# Keywords that signal operational/leadership questions
SIGNAL_KEYWORDS = [
    "COO", "operations", "systems", "processes", "delegate", "delegation",
    "hire", "hiring", "team", "leadership", "founder", "CEO", "scale",
    "scaling", "overwhelmed", "burnout", "structure", "accountability",
    "fractional", "part-time", "consultant", "advisor", "OKR", "goals",
    "align", "alignment", "bottleneck", "capacity", "workflow",
]


class RedditSource(BaseSource):
    name = "reddit"

    def __init__(self, config: dict):
        super().__init__(config)
        self.subreddits = config.get("subreddits", DEFAULT_SUBREDDITS)
        self.max_per_subreddit = config.get("max_per_subreddit", 25)
        self.min_upvotes = config.get("min_upvotes", 3)

    def harvest(self, keywords: list[str], **kwargs) -> list[RawQuestion]:
        """
        Fetches top/hot posts from each subreddit and filters for
        questions that match our signal keywords.
        """
        all_questions = []

        for subreddit in self.subreddits:
            try:
                questions = self._fetch_subreddit(subreddit)
                all_questions.extend(questions)
                time.sleep(1.5)  # Be respectful of rate limits
            except Exception as e:
                print(f"  Reddit [{subreddit}]: {e}")
                continue

        # Also search for specific keywords
        for keyword in keywords[:5]:  # Limit to top 5 to avoid rate limits
            try:
                questions = self._search_reddit(keyword)
                all_questions.extend(questions)
                time.sleep(2)
            except Exception as e:
                print(f"  Reddit search [{keyword}]: {e}")
                continue

        filtered = self.filter_valid(all_questions)
        deduped = self.deduplicate(filtered)
        print(f"  Reddit: {len(deduped)} questions harvested")
        return deduped

    def _fetch_subreddit(self, subreddit: str) -> list[RawQuestion]:
        """Fetch hot posts from a subreddit."""
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=50"
        headers = {"User-Agent": "LayerAdvisoryOQE/1.0 (content research bot)"}

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())

        questions = []
        for post in data.get("data", {}).get("children", []):
            post_data = post.get("data", {})
            title = post_data.get("title", "").strip()
            upvotes = post_data.get("score", 0)
            num_comments = post_data.get("num_comments", 0)
            permalink = post_data.get("permalink", "")

            if upvotes < self.min_upvotes:
                continue

            # Check if title contains relevant signal keywords
            title_lower = title.lower()
            has_signal = any(kw.lower() in title_lower for kw in SIGNAL_KEYWORDS)
            if not has_signal:
                continue

            q = RawQuestion(
                text=title,
                source=self.name,
                source_url=f"https://reddit.com{permalink}",
                source_context=f"r/{subreddit}",
                upvotes=upvotes,
                reply_count=num_comments,
            )
            questions.append(q)

            # Also harvest top comments that are questions
            if post_data.get("url"):
                pass  # Could fetch comment questions in future

        return questions

    def _search_reddit(self, keyword: str) -> list[RawQuestion]:
        """Search Reddit for a specific keyword."""
        encoded = urllib.parse.quote(keyword)
        url = f"https://www.reddit.com/search.json?q={encoded}&type=link&sort=relevance&limit=25&t=year"
        headers = {"User-Agent": "LayerAdvisoryOQE/1.0 (content research bot)"}

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())

        questions = []
        for post in data.get("data", {}).get("children", []):
            post_data = post.get("data", {})
            title = post_data.get("title", "").strip()
            upvotes = post_data.get("score", 0)
            permalink = post_data.get("permalink", "")
            subreddit = post_data.get("subreddit", "")

            q = RawQuestion(
                text=title,
                source=self.name,
                source_url=f"https://reddit.com{permalink}",
                source_context=f"r/{subreddit} — search: {keyword}",
                upvotes=upvotes,
                reply_count=post_data.get("num_comments", 0),
            )
            questions.append(q)

        return questions
