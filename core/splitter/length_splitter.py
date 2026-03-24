import re
from typing import List, Tuple
from .base import BaseSplitter
from ..models.chunk import Chunk
from ..parser.base import Section


class LengthSplitter(BaseSplitter):
    """Splits long content into smaller chunks based on length."""

    def __init__(self, max_tokens: int = 500, overlap_tokens: int = 50):
        """
        Initialize length splitter.

        Args:
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of overlapping tokens between chunks
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def split(self, sections: List[Section]) -> List[Chunk]:
        """Split sections into length-based chunks."""
        chunks = []
        chunk_index = 0

        for section in sections:
            content = section.content
            token_count = self.count_tokens(content)

            # If content is within limit, keep as single chunk
            if token_count <= self.max_tokens:
                chunk = Chunk(
                    content=content,
                    metadata={
                        'title': section.title,
                        'level': section.level,
                        'page_number': section.page_number,
                        'type': section.metadata.get('type', 'unknown'),
                        'file_name': section.metadata.get('file_name', ''),
                    },
                    chunk_index=chunk_index,
                    token_count=token_count
                )
                chunks.append(chunk)
                chunk_index += 1
            else:
                # Split the content
                sub_chunks = self._split_long_content(content, section)
                for sub_chunk in sub_chunks:
                    sub_chunk.chunk_index = chunk_index
                    chunks.append(sub_chunk)
                    chunk_index += 1

        return chunks

    def _split_long_content(self, content: str, section: Section) -> List[Chunk]:
        """Split long content into smaller chunks."""
        chunks = []

        # Try to split by paragraphs first
        paragraphs = self._split_into_paragraphs(content)

        current_chunk_content = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self.count_tokens(para)

            # If single paragraph exceeds limit, split by sentences
            if para_tokens > self.max_tokens:
                # Save current chunk if not empty
                if current_chunk_content:
                    chunks.append(self._create_chunk(
                        '\n'.join(current_chunk_content),
                        section,
                        current_tokens
                    ))
                    current_chunk_content = []
                    current_tokens = 0

                # Split the long paragraph
                sentence_chunks = self._split_by_sentences(para, section)
                chunks.extend(sentence_chunks)
            elif current_tokens + para_tokens > self.max_tokens:
                # Save current chunk and start new one
                if current_chunk_content:
                    chunks.append(self._create_chunk(
                        '\n'.join(current_chunk_content),
                        section,
                        current_tokens
                    ))

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk_content)
                current_chunk_content = [overlap_text, para] if overlap_text else [para]
                current_tokens = self.count_tokens('\n'.join(current_chunk_content))
            else:
                current_chunk_content.append(para)
                current_tokens += para_tokens

        # Don't forget the last chunk
        if current_chunk_content:
            chunks.append(self._create_chunk(
                '\n'.join(current_chunk_content),
                section,
                current_tokens
            ))

        return chunks

    def _split_into_paragraphs(self, content: str) -> List[str]:
        """Split content into paragraphs."""
        # Split by double newlines or single newlines
        paragraphs = re.split(r'\n\s*\n|\n', content)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_by_sentences(self, text: str, section: Section) -> List[Chunk]:
        """Split text by sentences while respecting sentence boundaries."""
        chunks = []

        # Chinese sentence ending patterns
        sentence_endings = re.compile(r'[。！？；\n]')
        sentences = []
        current_sentence = []

        for char in text:
            current_sentence.append(char)
            if sentence_endings.match(char):
                sentence_text = ''.join(current_sentence)
                sentences.append(sentence_text)
                current_sentence = []

        # Add remaining text
        if current_sentence:
            sentences.append(''.join(current_sentence))

        # Group sentences into chunks
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)

            if current_tokens + sentence_tokens > self.max_tokens and current_chunk:
                chunks.append(self._create_chunk(
                    ''.join(current_chunk),
                    section,
                    current_tokens
                ))
                # Add overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = [overlap_text] if overlap_text else []
                current_tokens = self.count_tokens(''.join(current_chunk))

            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        if current_chunk:
            chunks.append(self._create_chunk(
                ''.join(current_chunk),
                section,
                current_tokens
            ))

        return chunks

    def _create_chunk(self, content: str, section: Section, token_count: int) -> Chunk:
        """Create a chunk from content."""
        return Chunk(
            content=content,
            metadata={
                'title': section.title,
                'level': section.level,
                'page_number': section.page_number,
                'type': section.metadata.get('type', 'unknown'),
                'file_name': section.metadata.get('file_name', ''),
                'split': 'length'
            },
            chunk_index=0,  # Will be updated later
            token_count=token_count
        )

    def _get_overlap_text(self, previous_content: List[str]) -> str:
        """Get overlapping text from previous content for context."""
        if not previous_content or self.overlap_tokens == 0:
            return ''

        full_text = '\n'.join(previous_content)
        # Estimate characters based on tokens (~4 chars per token for Chinese)
        overlap_chars = self.overlap_tokens * 4

        if len(full_text) <= overlap_chars:
            return full_text

        return full_text[-overlap_chars:]
