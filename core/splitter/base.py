from abc import ABC, abstractmethod
from typing import List
from ..models.chunk import Chunk
from ..parser.base import Section


class BaseSplitter(ABC):
    """Base class for document splitters."""

    @abstractmethod
    def split(self, sections: List[Section]) -> List[Chunk]:
        """Split sections into chunks."""
        pass

    def count_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # More accurate estimation: Chinese ~2 chars/token, others ~4 chars/token
        import re
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(re.sub(r'[\u4e00-\u9fff]', '', text))
        return chinese_chars // 2 + other_chars // 4 + 1
