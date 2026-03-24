from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class Section:
    """Represents a section of a document."""
    title: str
    content: str
    level: int = 0  # 0 = paragraph, 1 = chapter, 2 = clause, etc.
    page_number: int = 1
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseParser(ABC):
    """Base class for document parsers."""

    @abstractmethod
    def parse(self, file_path: str) -> List[Section]:
        """Parse file and return list of sections."""
        pass

    @abstractmethod
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from file."""
        pass

    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        return []
