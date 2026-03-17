"""
oqe/sources/base_source.py
Abstract base class all OQE source connectors inherit from.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import hashlib
import re


@dataclass
class RawQuestion:
    """A raw question harvested from any source before processing."""
    text: str
    source: str                          # "reddit" | "google_paa" | "quora" | "indie_hackers" | "podcast" | "newsletter"
    source_url: str = ""
    source_context: str = ""             # subreddit, thread title, episode name, etc.
    upvotes: int = 0
    reply_count: int = 0
    harvested_at: str = ""

    def __post_init__(self):
        if not self.harvested_at:
            self.harvested_at = datetime.now(timezone.utc).isoformat()

    @property
    def id(self) -> str:
        """SHA256 hash of normalized text — stable unique ID."""
        normalized = self._normalize(self.text)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    @property
    def normalized_text(self) -> str:
        return self._normalize(self.text)

    def _normalize(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def is_valid_question(self) -> bool:
        """Basic validation — is this actually a question worth processing?"""
        t = self.text.strip()
        if len(t) < 15 or len(t) > 350:
            return False
        question_starters = ('how', 'what', 'when', 'why', 'should', 'can', 'is', 'are', 'do', 'does', 'will', 'would', 'which', 'who')
        lower = t.lower()
        starts_with_question = any(lower.startswith(s) for s in question_starters)
        ends_with_question = t.endswith('?')
        return starts_with_question or ends_with_question


class BaseSource(ABC):
    """Abstract base for all OQE source connectors."""

    name: str = "base"

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def harvest(self, keywords: list[str], **kwargs) -> list[RawQuestion]:
        """
        Pull raw questions from this source.
        Args:
            keywords: List of seed keywords to search for
        Returns:
            List of RawQuestion objects
        """
        pass

    def filter_valid(self, questions: list[RawQuestion]) -> list[RawQuestion]:
        """Remove invalid questions."""
        return [q for q in questions if q.is_valid_question()]

    def deduplicate(self, questions: list[RawQuestion]) -> list[RawQuestion]:
        """Remove exact duplicates within this batch."""
        seen = set()
        unique = []
        for q in questions:
            if q.id not in seen:
                seen.add(q.id)
                unique.append(q)
        return unique
