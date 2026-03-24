import re
from typing import List
from .base import BaseSplitter
from ..models.chunk import Chunk
from ..parser.base import Section


class SemanticSplitter(BaseSplitter):
    """Splits document based on semantic structure (chapters, clauses, etc.)."""

    # Patterns for legal document structure
    CHAPTER_PATTERN = re.compile(r'^第[一二三四五六七八九十百]+章')
    CLAUSE_PATTERN = re.compile(r'^第[一二三四五六七八九十百]+条')
    APPENDIX_PATTERN = re.compile(r'^附件[一二三四五六七八九十]+')

    def split(self, sections: List[Section]) -> List[Chunk]:
        """Split sections into semantic chunks."""
        chunks = []

        for idx, section in enumerate(sections):
            chunk = Chunk(
                content=section.content,
                metadata={
                    'title': section.title,
                    'level': section.level,
                    'page_number': section.page_number,
                    'type': section.metadata.get('type', 'unknown'),
                    'file_name': section.metadata.get('file_name', ''),
                },
                chunk_index=idx,
                token_count=self.count_tokens(section.content)
            )
            chunks.append(chunk)

        return chunks

    def identify_structure(self, text: str) -> dict:
        """Identify the structure type of a text block."""
        if self.CHAPTER_PATTERN.match(text):
            return {'type': 'chapter', 'level': 1}
        elif self.CLAUSE_PATTERN.match(text):
            return {'type': 'clause', 'level': 2}
        elif self.APPENDIX_PATTERN.match(text):
            return {'type': 'appendix', 'level': 1}
        else:
            return {'type': 'paragraph', 'level': 0}
