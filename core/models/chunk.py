from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class Chunk(BaseModel):
    """Represents a chunk of text from a document."""

    content: str = Field(description="The text content of this chunk")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata associated with this chunk")
    chunk_index: int = Field(description="Index of this chunk in the original document")
    token_count: int = Field(description="Number of tokens in this chunk")
    previous_chunk_index: Optional[int] = Field(default=None, description="Index of the previous chunk for context retrieval")
    next_chunk_index: Optional[int] = Field(default=None, description="Index of the next chunk for context retrieval")

    def dict(self, **kwargs) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "metadata": self.metadata,
            "chunk_index": self.chunk_index,
            "token_count": self.token_count,
            "previous_chunk_index": self.previous_chunk_index,
            "next_chunk_index": self.next_chunk_index,
        }
