from abc import ABC, abstractmethod
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
        t = re.sub(r'[^\w\s]', ' ', t)
        return re.sub(r'\s+', ' ', t).strip()

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
