import re
from typing import List, Dict, Any
from .base import BaseParser, Section
from .structure_detector import StructureDetector, create_detector


class TXTParser(BaseParser):
    """
    TXT文件解析器

    使用结构特征检测标题，不依赖具体语言格式
    """

    def get_supported_extensions(self) -> List[str]:
        return ['.txt', '.text']

    def parse(self, file_path: str) -> List[Section]:
        """解析TXT文件并提取章节"""
        sections = []

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')

        # 使用结构检测器
        detector = create_detector()
        heading_indices = detector.detect_sections(lines)
        section_groups = detector.group_lines_into_sections(lines, heading_indices)

        # 转换为Section对象
        for idx, (title, content_lines) in enumerate(section_groups):
            level = detector.detect_heading_level(title)

            # 确定section类型
            section_type = self._determine_section_type(title, level)

            section = Section(
                title=title,
                content='\n'.join(content_lines),
                level=level,
                page_number=1,  # TXT不保留页码
                metadata={
                    'type': section_type,
                    'line_number': self._find_line_number(lines, title),
                }
            )
            sections.append(section)

        return sections

    def _determine_section_type(self, title: str, level: int) -> str:
        """根据标题和级别判断section类型"""
        title_lower = title.lower()

        # 检查附件相关
        if 'appendix' in title_lower or '附件' in title or 'schedule' in title_lower:
            return 'appendix'

        # 检查章节相关
        if 'chapter' in title_lower or '第' in title and '章' in title:
            return 'chapter'

        # 检查条款相关
        if 'article' in title_lower or '第' in title and '条' in title:
            return 'clause'

        # 根据级别推断
        if level == 1:
            return 'chapter'
        elif level == 2:
            return 'clause'
        elif title == 'Preamble':
            return 'preamble'
        else:
            return 'section'

    def _find_line_number(self, lines: List[str], title: str) -> int:
        """查找标题在原文件中的行号"""
        for i, line in enumerate(lines):
            if line.strip() == title.strip():
                return i + 1
        return 1

    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取TXT文件的元数据"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        line_count = len([l for l in lines if l.strip()])

        metadata = {
            'file_name': file_path,
            'file_type': 'txt',
            'total_lines': len(lines),
            'non_empty_lines': line_count,
        }

        return metadata
