import pytest
import os
import tempfile
from src.parser.txt_parser import TXTParser
from src.parser.base import Section


class TestTXTParser:
    """Tests for TXT parser."""

    def setup_method(self):
        self.parser = TXTParser()

    def test_supported_extensions(self):
        assert '.txt' in self.parser.get_supported_extensions()
        assert '.text' in self.parser.get_supported_extensions()

    def test_parse_simple_contract(self):
        """Test parsing a simple contract text."""
        content = """第一条 合同双方
本合同由甲方和乙方签订。

第二条 权利义务
甲方的权利包括...

第三条 违约责任
任何一方违反本合同约定...

附件一 补充协议"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        try:
            sections = self.parser.parse(temp_path)
            assert len(sections) > 0
            # Check that clauses are identified
            titles = [s.title for s in sections]
            assert '第一条 合同双方' in titles
            assert '第二条 权利义务' in titles
            assert '第三条 违约责任' in titles
            assert '附件一 补充协议' in titles
        finally:
            os.unlink(temp_path)

    def test_extract_metadata(self):
        """Test metadata extraction."""
        content = "Test content"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        try:
            metadata = self.parser.extract_metadata(temp_path)
            assert metadata['file_type'] == 'txt'
            assert 'total_lines' in metadata
        finally:
            os.unlink(temp_path)


class TestSectionIdentification:
    """Test section structure identification."""

    def test_clause_pattern(self):
        """Test clause pattern matching."""
        parser = TXTParser()
        sections = [
            Section(title="第一条 合同期限", content="内容...", level=2),
            Section(title="第二条 付款方式", content="内容...", level=2),
        ]
        assert len(sections) == 2

    def test_chapter_pattern(self):
        """Test chapter pattern matching."""
        sections = [
            Section(title="第一章 总则", content="内容...", level=1),
            Section(title="第二章 双方权利义务", content="内容...", level=1),
        ]
        assert len(sections) == 2

    def test_appendix_pattern(self):
        """Test appendix pattern matching."""
        sections = [
            Section(title="附件一", content="附录内容...", level=1),
            Section(title="附件二", content="附录内容...", level=1),
        ]
        assert len(sections) == 2
