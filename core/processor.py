import os
from typing import List, Dict, Any
from .parser.base import BaseParser, Section
from .parser import PDFParser, DOCXParser, TXTParser
from .splitter.semantic_splitter import SemanticSplitter
from .splitter.length_splitter import LengthSplitter
from .models.chunk import Chunk


class ContractProcessor:
    """Main processor for legal contract documents."""

    def __init__(self, max_tokens: int = 500, overlap_tokens: int = 50, min_tokens: int = 100):
        """
        Initialize the contract processor.

        Args:
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of overlapping tokens for context
            min_tokens: Minimum tokens per chunk, smaller chunks will be merged with previous
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_tokens = min_tokens

        # Initialize parsers
        self.parsers: Dict[str, BaseParser] = {
            '.pdf': PDFParser(),
            '.docx': DOCXParser(),
            '.doc': DOCXParser(),
            '.txt': TXTParser(),
            '.text': TXTParser(),
        }

        # Initialize splitters
        self.semantic_splitter = SemanticSplitter()
        self.length_splitter = LengthSplitter(
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens
        )

    def process(self, file_path: str) -> List[Chunk]:
        """
        Process a single contract file.

        Args:
            file_path: Path to the contract file

        Returns:
            List of chunks
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get file extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if ext not in self.parsers:
            raise ValueError(f"Unsupported file type: {ext}")

        parser = self.parsers[ext]

        # Extract metadata
        metadata = parser.extract_metadata(file_path)
        metadata['file_name'] = os.path.basename(file_path)

        # Parse document into sections
        sections = parser.parse(file_path)

        # Add file metadata to each section
        for section in sections:
            section.metadata['file_name'] = metadata['file_name']
            section.metadata['file_type'] = metadata.get('file_type', ext[1:])

        # Step 1: Semantic splitting (by chapters/clauses)
        semantic_chunks = self.semantic_splitter.split(sections)

        # Step 2: Length splitting (for chunks that exceed max_tokens)
        final_chunks = []
        for chunk in semantic_chunks:
            if chunk.token_count > self.max_tokens:
                # Need to split this chunk further
                # Convert chunk back to section for length splitter
                section = Section(
                    title=chunk.metadata.get('title', ''),
                    content=chunk.content,
                    level=chunk.metadata.get('level', 0),
                    page_number=chunk.metadata.get('page_number', 1),
                    metadata=chunk.metadata
                )
                length_chunks = self.length_splitter.split([section])
                final_chunks.extend(length_chunks)
            else:
                final_chunks.append(chunk)

        # Merge small chunks with previous chunks
        final_chunks = self._merge_small_chunks(final_chunks)

        # Re-index chunks and add previous/next links
        for idx, chunk in enumerate(final_chunks):
            chunk.chunk_index = idx
            chunk.previous_chunk_index = idx - 1 if idx > 0 else None
            chunk.next_chunk_index = idx + 1 if idx < len(final_chunks) - 1 else None

        return final_chunks

    def _merge_small_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Merge consecutive small chunks to meet min_tokens threshold.

        Small chunks (under min_tokens) are merged with following chunks until
        the combined chunk reaches min_tokens.

        When merging, each chunk's title is prepended to its content to
        preserve the document structure.

        If merging would exceed max_tokens, still merge if the current chunk
        is below min_tokens (to ensure minimum token count at the cost of
        slightly exceeding max_tokens).
        """
        if not chunks or self.min_tokens <= 0:
            return chunks

        result = []
        i = 0

        while i < len(chunks):
            current = chunks[i]

            # If current chunk is large enough, keep it
            if current.token_count >= self.min_tokens:
                # Prepend title to content for clause/chapter/section types only
                # Not for table/image/preamble
                current_title = current.metadata.get('title', '')
                chunk_type = current.metadata.get('type', '')
                if current_title and current.content and chunk_type in ('clause', 'chapter', 'section'):
                    if not current.content.startswith(current_title):
                        current.content = f"{current_title}\n{current.content}"
                result.append(current)
                i += 1
                continue

            # Skip table and image chunks - they are standalone semantic units
            chunk_type = current.metadata.get('type', '')
            if chunk_type in ('table', 'image'):
                result.append(current)
                i += 1
                continue

            # Current chunk is small - need to merge
            # Build combined content with title+content for each merged section
            combined_parts = []

            # Add current chunk's title + content (only for clause/chapter/section)
            current_title = current.metadata.get('title', '')
            current_type = current.metadata.get('type', '')
            if current_title and current_type in ('clause', 'chapter', 'section'):
                combined_parts.append(f"{current_title}\n{current.content}" if current.content else current_title)
            elif current.content:
                combined_parts.append(current.content)

            current_tokens = current.token_count
            j = i + 1

            # Keep adding chunks until we reach min_tokens
            while j < len(chunks) and current_tokens < self.min_tokens:
                next_chunk = chunks[j]
                next_title = next_chunk.metadata.get('title', '')
                next_content = next_chunk.content or ""
                next_tokens = next_chunk.token_count

                new_tokens = current_tokens + next_tokens

                # Allow exceeding max_tokens if current is still below min_tokens
                # This ensures small chunks get merged even if it slightly exceeds the limit
                if new_tokens > self.max_tokens and current_tokens < self.min_tokens:
                    # Force merge to meet minimum threshold
                    pass
                elif new_tokens > self.max_tokens:
                    # Would exceed max_tokens and we already meet min, stop
                    break

                # Skip image/table chunks - they are standalone semantic units
                # Stop merging when we hit an image/table - don't merge content after it
                next_type = next_chunk.metadata.get('type', '')
                if next_type in ('image', 'table'):
                    break

                # Add this chunk's title + content (only for clause/chapter/section)
                next_type = next_chunk.metadata.get('type', '')
                if next_title and next_type in ('clause', 'chapter', 'section'):
                    combined_parts.append(f"{next_title}\n{next_content}" if next_content else next_title)
                elif next_content:
                    combined_parts.append(next_content)

                current_tokens = new_tokens
                j += 1

            # Combine all parts
            combined_content = "\n".join(combined_parts)

            # Update current chunk
            current.content = combined_content
            current.token_count = current_tokens

            # If this is the last chunk and it's still below min_tokens,
            # try to merge backwards with the previous chunk
            # Note: j >= len(chunks) means we've processed all remaining chunks
            # But don't merge into image/table chunks - keep small chunk as-is instead
            is_last_iteration = (j >= len(chunks))
            if is_last_iteration and current_tokens < self.min_tokens and len(result) > 0:
                prev_type = result[-1].metadata.get('type', '')
                if prev_type not in ('image', 'table'):
                    # Backward merge into previous non-image/table chunk
                    prev = result[-1]
                    combined = f"{prev.content}\n{combined_content}"
                    combined_tokens = self._count_tokens(combined)

                    prev.content = combined
                    prev.token_count = combined_tokens
                    prev.next_chunk_index = None
                else:
                    # Don't merge into image/table - keep small chunk as-is
                    result.append(current)
            else:
                # Add to result
                result.append(current)
            i = j

        return result

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text (approximate)."""
        # Simple approximation: ~4 characters per token for Chinese
        import re
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(re.sub(r'[\u4e00-\u9fff]', '', text))
        return chinese_chars // 2 + other_chars // 4 + 1

    def process_batch(self, dir_path: str) -> List[Chunk]:
        """
        Process all contract files in a directory.

        Args:
            dir_path: Path to directory containing contract files

        Returns:
            List of all chunks from all files
        """
        if not os.path.isdir(dir_path):
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        all_chunks = []
        global_index = 0

        # Get all supported files
        for file_name in os.listdir(dir_path):
            file_path = os.path.join(dir_path, file_name)

            # Skip directories
            if os.path.isdir(file_path):
                continue

            # Check if file type is supported
            _, ext = os.path.splitext(file_name)
            if ext.lower() not in self.parsers:
                continue

            try:
                chunks = self.process(file_path)
                # Update global index
                for chunk in chunks:
                    chunk.chunk_index = global_index
                    global_index += 1
                all_chunks.extend(chunks)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue

        return all_chunks
