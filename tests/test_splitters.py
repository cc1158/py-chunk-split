import pytest
from src.splitter.semantic_splitter import SemanticSplitter
from src.splitter.length_splitter import LengthSplitter
from src.parser.base import Section


class TestSemanticSplitter:
    """Tests for semantic splitter."""

    def setup_method(self):
        self.splitter = SemanticSplitter()

    def test_split_sections(self):
        """Test splitting sections into chunks."""
        sections = [
            Section(
                title="第一条",
                content="这是第一条的内容。",
                level=2,
                page_number=1,
                metadata={'type': 'clause', 'file_name': 'test.pdf'}
            ),
            Section(
                title="第二条",
                content="这是第二条的内容。",
                level=2,
                page_number=1,
                metadata={'type': 'clause', 'file_name': 'test.pdf'}
            ),
        ]

        chunks = self.splitter.split(sections)
        assert len(chunks) == 2
        assert chunks[0].content == "这是第一条的内容。"
        assert chunks[1].content == "这是第二条的内容。"
        assert chunks[0].metadata['title'] == "第一条"
        assert chunks[0].chunk_index == 0

    def test_identify_structure(self):
        """Test structure identification."""
        result = self.splitter.identify_structure("第一章 总则")
        assert result['type'] == 'chapter'

        result = self.splitter.identify_structure("第一条 合同期限")
        assert result['type'] == 'clause'

        result = self.splitter.identify_structure("附件一")
        assert result['type'] == 'appendix'


class TestLengthSplitter:
    """Tests for length splitter."""

    def setup_method(self):
        self.splitter = LengthSplitter(max_tokens=100)

    def test_split_short_content(self):
        """Test that short content is kept as single chunk."""
        sections = [
            Section(
                title="第一条",
                content="短内容。",
                level=2,
                page_number=1,
                metadata={'type': 'clause'}
            ),
        ]

        chunks = self.splitter.split(sections)
        assert len(chunks) == 1

    def test_split_long_content(self):
        """Test splitting long content."""
        # Create content that exceeds max_tokens (100 tokens = ~400 chars)
        long_content = "这是很长的内容。" * 100

        sections = [
            Section(
                title="第一条",
                content=long_content,
                level=2,
                page_number=1,
                metadata={'type': 'clause'}
            ),
        ]

        chunks = self.splitter.split(sections)
        # Should be split into multiple chunks
        assert len(chunks) > 1

    def test_token_counting(self):
        """Test token counting."""
        text = "这是测试内容。"  # 8 characters
        # ~2 chars per token for Chinese (rough estimate)
        actual_tokens = self.splitter.count_tokens(text)
        assert actual_tokens >= 1  # At least some tokens counted
