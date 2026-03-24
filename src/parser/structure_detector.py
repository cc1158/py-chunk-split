"""
结构检测模块 - 基于视觉特征检测文档标题，不依赖具体语言格式
"""

import re
from typing import List, Tuple, Optional


class StructureDetector:
    """
    基于文档结构特征检测标题

    检测策略（按优先级）：
    1. 样式标记（DOCX/PDF有样式信息时）
    2. 短行后面跟长行（典型的标题-正文模式）
    3. 独立成段的短行
    4. 符合通用编号模式的行
    """

    # 通用编号模式（多种语言）
    NUMBERING_PATTERNS = [
        # 中文: 第X条、第X章、第X节
        r'^第[一二三四五六七八九十百千零〇0-9]+[条章节款项个部]',
        # 纯数字编号: 1. 1, 1、 1)
        r'^[0-9]+[.、．、)）]',
        # 中文数字编号: 六、 七、 八、 (独立成段的章节标题，支持数字和符号之间有空格)
        r'^[一二三四五六七八九十百千零〇]+[　 \t]*[、.．、)）]',
        # 括号编号: (1) (一) ①
        r'^[（\(][0-9a-zA-Z一二三四五六七八九十]+[）\)]',
        # 罗马数字
        r'^[ivxlcIVXLC]+[.、]',
        # 英文: Article X, Section X, Chapter X
        r'^(Article|Section|Chapter|Clause|Item|Part|Subsection)[\s]+[0-9]',
        # 日文: 第X条
        r'^第[一二三四五六七八九十百千0-9]+条',
        # 韩文: 第X条 (类似中文)
        r'^제[一二三四五六七八九十百千0-9]+조',
        # 附件
        r'^附件[0-9一二三四五六七八九十]+',
        r'^Appendix\s+[0-9]',
        r'^Schedule\s+[0-9]',
    ]

    # 编译所有模式（每次调用时重新编译以支持动态修改NUMBERING_PATTERNS）
    @classmethod
    def _get_combined_pattern(cls):
        return re.compile(
            '|'.join(cls.NUMBERING_PATTERNS),
            re.IGNORECASE
        )

    def __init__(self, short_line_threshold: int = 50, long_line_ratio: float = 2.0):
        """
        Args:
            short_line_threshold: 短行阈值，超过此长度认为是正文（默认50字符）
            long_line_ratio: 长短行比例，当前一行长度 < 下一行长度/此值时，认为是标题（默认2.0）
        """
        self.short_line_threshold = short_line_threshold
        self.long_line_ratio = long_line_ratio

    # 检查下一行是否也是类似格式的编号行
    # 使用与COMBINED_PATTERN相同的编号定义
    NUMBERED_ITEM_PATTERN = re.compile(
        r'^[0-9]+[.、．、)）]|'
        r'^[（\(][0-9a-zA-Z一二三四五六七八九十]+[）\)]|'
        r'^[ivxlcIVXLC]+[.、]',
        re.IGNORECASE
    )

    # 中文数字标题模式（独立章节，支持数字和符号之间有空格）
    CHINESE_NUMERAL_HEADING_PATTERN = re.compile(
        r'^[一二三四五六七八九十百千零〇]+[　 \t]*[、.．、)）]',
        re.IGNORECASE
    )

    def _is_numbered_item(self, line: str) -> bool:
        """
        检查是否是多级编号列表项（如 "1." "2." "(1)" "(2)"）
        注意：中文数字 "一、" "二、" 等是章节标题，不是列表项
        """
        line = line.strip()
        # 先排除中文数字标题模式
        if self.CHINESE_NUMERAL_HEADING_PATTERN.match(line):
            return False
        return bool(self.NUMBERED_ITEM_PATTERN.match(line))

    def is_likely_heading(self, line: str, next_line: Optional[str] = None,
                          prev_line: Optional[str] = None,
                          prev_prev_line: Optional[str] = None) -> Tuple[bool, str]:
        """
        判断一行是否为标题

        Returns:
            (is_heading, reason) - 是否是标题及判断原因
        """
        line = line.strip()
        if not line:
            return False, "empty line"

        # 核心策略：
        # 1. 如果一个编号行后面紧跟另一个编号行（如 1., 2., 3.），说明这是列表，不是标题
        # 2. 如果前面有类似的编号项（例如 "1." 在 "2." 前面），说明这是列表，不是标题
        # 3. 如果一个编号行后面是普通正文，说明这是章节标题

        # 先检查是否是"第X条"风格的主要条款标题
        is_chapter_clause = re.match(r'^第[一二三四五六七八九十百千零〇0-9]+条', line)

        # 如果是"第X条"风格，这是明确的标题，不受后续列表项影响
        if is_chapter_clause:
            return True, "chapter_clause_heading"

        # 检查是否是编号行（包括列表项和子条款）
        if self._get_combined_pattern().match(line):
            # 优先检查是否是中文数字章节标题（一、二、三、等）
            # 中文数字标题是明确的章节标记，后面跟随的内容不管是列表还是正文都属于该章节
            if self.CHINESE_NUMERAL_HEADING_PATTERN.match(line):
                return True, "chinese_numeral_heading"

            # 如果下一行也是类似的编号行，说明这是列表项
            if next_line and self._is_numbered_item(next_line.strip()):
                return False, "numbered_list_item"

            # 如果前一行也是类似的编号行（当前项是列表的一部分）
            if prev_line and self._is_numbered_item(prev_line.strip()):
                return False, "numbered_list_item_in_sequence"

            # 否则，这可能是子条款标题
            return True, "numbering_pattern"

        # 策略2: 独立成段的短行 + 下一行是明确的长正文
        # 且这个短行不是以数字开头的编号
        if next_line is not None and prev_line is not None:
            next_line_stripped = next_line.strip()
            current_stripped = line

            # 如果当前行是纯数字开头（如 "1)"），可能是列表编号
            if re.match(r'^[0-9]+[.、））]', current_stripped):
                return False, "looks_like_list_number"

            # 如果当前行短、下一行长且是正文
            if (len(current_stripped) < self.short_line_threshold and
                len(next_line_stripped) > len(current_stripped) * 3 and
                len(next_line_stripped) > self.short_line_threshold * 2):
                return True, "isolated_heading_before_content"

        # 策略3: 纯数字或字母单独成行
        if re.match(r'^[0-9a-zA-Z]+$', line) and len(line) < 10:
            return True, "standalone_number"

        return False, "not_a_heading"

    def detect_sections(self, lines: List[str]) -> List[int]:
        """
        检测所有可能的标题行索引

        Returns:
            标题行的索引列表
        """
        heading_indices = []

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            prev_line = lines[i - 1] if i > 0 else None
            prev_prev_line = lines[i - 2] if i > 1 else None
            next_line = lines[i + 1] if i < len(lines) - 1 else None

            is_heading, reason = self.is_likely_heading(line, next_line, prev_line, prev_prev_line)
            if is_heading:
                heading_indices.append(i)

        return heading_indices

    def group_lines_into_sections(self, lines: List[str],
                                   heading_indices: List[int]) -> List[Tuple[str, List[str]]]:
        """
        将行分组为 (标题, 内容列表) 的形式

        Returns:
            [(title, [content_lines]), ...]
        """
        sections = []

        for i, heading_idx in enumerate(heading_indices):
            title = lines[heading_idx].strip()

            # 确定内容范围
            start = heading_idx + 1
            end = heading_indices[i + 1] if i + 1 < len(heading_indices) else len(lines)

            # 收集内容行
            content_lines = []
            for j in range(start, end):
                line = lines[j].strip()
                if line:  # 跳过空行
                    content_lines.append(line)

            sections.append((title, content_lines))

        # 处理开头的非标题内容（序言）
        first_heading_idx = heading_indices[0] if heading_indices else 0
        if first_heading_idx > 0:
            preamble_lines = [lines[i].strip() for i in range(first_heading_idx) if lines[i].strip()]
            if preamble_lines:
                sections.insert(0, ("Preamble", preamble_lines))

        return sections

    def detect_heading_level(self, title: str) -> int:
        """
        尝试检测标题级别（用于判断是章、条、款等）

        Returns:
            级别数字，0=序言/其他，1=章/部，2=条/款，3=项
        """
        title = title.strip()

        # 高层级标题模式
        high_level_patterns = [
            r'(Part|部|篇|卷|Part\s+[IVX0-9])',  # Part, 篇, 卷
            r'(Chapter|章|Chapter\s+[IVX0-9])',   # Chapter, 第X章
        ]

        # 低层级标题模式
        low_level_patterns = [
            r'(Article|条|Article\s+[0-9])',       # Article, 第X条
            r'(Section|节|Section\s+[0-9])',       # Section, 第X节
            r'(Clause|款|Clause\s+[0-9])',         # Clause, 第X款
            r'(Item|项|Item\s+[0-9])',              # Item, 第X项
        ]

        for p in high_level_patterns:
            if re.search(p, title, re.IGNORECASE):
                return 1

        for p in low_level_patterns:
            if re.search(p, title, re.IGNORECASE):
                return 2

        # 附件
        if re.search(r'(Appendix|附件|Schedule|Annex)', title, re.IGNORECASE):
            return 1

        # 默认根据长度判断（短的是标题，长的可能是序言）
        if len(title) < 30:
            return 2

        return 0


def create_detector() -> StructureDetector:
    """创建默认的结构检测器"""
    return StructureDetector(
        short_line_threshold=50,
        long_line_ratio=2.0
    )
