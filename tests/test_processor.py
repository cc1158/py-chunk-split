import pytest
import os
import tempfile
from core.processor import ContractProcessor


class TestContractProcessor:
    """Tests for the main processor."""

    def setup_method(self):
        self.processor = ContractProcessor(max_tokens=500)

    def test_unsupported_file_type(self):
        """Test handling of unsupported file types."""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = f.name
        try:
            with pytest.raises(ValueError):
                self.processor.process(temp_path)
        finally:
            os.unlink(temp_path)

    def test_nonexistent_file(self):
        """Test handling of non-existent files."""
        with pytest.raises(FileNotFoundError):
            self.processor.process("nonexistent_file.pdf")

    def test_file_not_found_error(self):
        """Test that FileNotFoundError is raised for missing files."""
        with pytest.raises(FileNotFoundError):
            self.processor.process("/path/to/missing/file.txt")

    def test_process_batch_empty_directory(self):
        """Test processing an empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            chunks = self.processor.process_batch(temp_dir)
            assert len(chunks) == 0

    def test_process_batch_with_txt_file(self):
        """Test batch processing with a TXT file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            test_content = """第一条 合同双方
本合同由甲方和乙方签订。

第二条 权利义务
甲方的权利包括...
"""
            test_path = os.path.join(temp_dir, "test.txt")
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(test_content)

            chunks = self.processor.process_batch(temp_dir)
            assert len(chunks) > 0
            # Check that file_name is set
            assert all(c.metadata.get('file_name') == 'test.txt' for c in chunks)
