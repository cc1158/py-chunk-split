import fitz  # PyMuPDF
import re
from typing import List, Dict, Any, Tuple, Optional
from .base import BaseParser, Section
from .structure_detector import StructureDetector, create_detector


class PDFParser(BaseParser):
    """
    PDF文件解析器

    优先使用字体大小判断标题，无明显字体差异时使用结构特征检测
    支持多语言，不依赖具体格式
    表格和图片会作为完整结构保留
    """

    # 图片类型判断阈值
    SIGNATURE_SIZE_THRESHOLD = 0.05  # 占页面面积 < 5% 可能是签章
    SEAL_SIZE_THRESHOLD = 0.03  # 更小的可能是印章

    def get_supported_extensions(self) -> List[str]:
        return ['.pdf']

    def parse(self, file_path: str) -> List[Section]:
        """解析PDF文件并提取章节"""
        sections = []
        doc = fitz.open(file_path)

        current_section = None
        current_content = []

        # 收集文档级别的统计信息（用于字体大小判断）
        all_font_sizes = self._collect_font_sizes(doc)
        avg_font_size = sum(all_font_sizes) / len(all_font_sizes) if all_font_sizes else 12

        for page_num, page in enumerate(doc, start=1):
            # 提取页面中的表格和图片
            tables = self._extract_tables(page)
            images = self._extract_images(page)

            # 获取页面的文本块及字体信息
            page_text_blocks = self._extract_page_blocks(page)

            # 跟踪当前处理到的文本块索引
            text_block_idx = 0

            for table_data in tables:
                table_bbox = table_data['bbox']

                # 先处理表格前的文本块和图片
                while text_block_idx < len(page_text_blocks):
                    block = page_text_blocks[text_block_idx]
                    text = block['text'].strip()
                    if not text:
                        text_block_idx += 1
                        continue

                    # 检查这个文本块是否在表格之前
                    block_bbox = block.get('bbox')
                    if block_bbox and self._bbox_after_table(block_bbox, table_bbox):
                        break  # 这个文本块在表格之后，停止

                    font_size = block.get('font_size', avg_font_size)
                    is_heading, heading_level = self._detect_heading(text, font_size, avg_font_size)

                    if is_heading:
                        # 保存之前的section
                        if current_section:
                            current_section.content = '\n'.join(current_content).strip()
                            if current_section.content:
                                sections.append(current_section)

                        section_type = self._determine_section_type(text, heading_level)
                        current_section = Section(
                            title=text,
                            content='',
                            level=heading_level,
                            page_number=page_num,
                            metadata={
                                'type': section_type,
                                'font_size': font_size,
                                'is_font_based_heading': font_size > avg_font_size * 1.2,
                                'page_num': page_num,
                            }
                        )
                        current_content = []
                    else:
                        if current_section is None:
                            current_section = Section(
                                title='Preamble',
                                content='',
                                level=0,
                                page_number=page_num,
                                metadata={'type': 'preamble'}
                            )
                        current_content.append(text)

                    text_block_idx += 1

                # 插入表格作为独立section（表格不能拆分，需要完整保留）
                if current_section:
                    current_section.content = '\n'.join(current_content).strip()
                    if current_section.content:
                        sections.append(current_section)

                table_text = self._format_table_as_text(table_data)
                current_section = Section(
                    title='[表格]',
                    content=table_text,
                    level=0,
                    page_number=page_num,
                    metadata={
                        'type': 'table',
                        'page_num': page_num,
                        'row_count': len(table_data['rows']),
                        'col_count': len(table_data['rows'][0]) if table_data['rows'] else 0,
                    }
                )
                current_content = []

            # 处理图片（插入到当前section内容中或创建独立section）
            for img_info in images:
                # 在图片位置插入占位符
                placeholder = self._format_image_placeholder(img_info)
                current_content.append(placeholder)

            # 处理表格之后的剩余文本块
            while text_block_idx < len(page_text_blocks):
                block = page_text_blocks[text_block_idx]
                text = block['text'].strip()
                if not text:
                    text_block_idx += 1
                    continue

                font_size = block.get('font_size', avg_font_size)
                is_heading, heading_level = self._detect_heading(text, font_size, avg_font_size)

                if is_heading:
                    if current_section:
                        current_section.content = '\n'.join(current_content).strip()
                        if current_section.content:
                            sections.append(current_section)

                    section_type = self._determine_section_type(text, heading_level)
                    current_section = Section(
                        title=text,
                        content='',
                        level=heading_level,
                        page_number=page_num,
                        metadata={
                            'type': section_type,
                            'font_size': font_size,
                            'is_font_based_heading': font_size > avg_font_size * 1.2,
                            'page_num': page_num,
                        }
                    )
                    current_content = []
                else:
                    if current_section is None:
                        current_section = Section(
                            title='Preamble',
                            content='',
                            level=0,
                            page_number=page_num,
                            metadata={'type': 'preamble'}
                        )
                    current_content.append(text)

                text_block_idx += 1

        # 添加最后一个section
        if current_section:
            current_section.content = '\n'.join(current_content).strip()
            if current_section.content:
                sections.append(current_section)

        doc.close()
        return sections

    def _bbox_after_table(self, block_bbox, table_bbox) -> bool:
        """检查文本块是否在表格之后"""
        # 比较Y坐标（垂直位置）
        block_top = block_bbox[1] if len(block_bbox) >= 4 else 0
        table_bottom = table_bbox[3] if len(table_bbox) >= 4 else 0
        return block_top > table_bottom

    def _detect_heading(self, text: str, font_size: float, avg_font_size: float) -> Tuple[bool, int]:
        """检测文本是否为标题"""
        is_heading = False
        heading_level = 0

        # 策略1: 字体明显大于平均字体
        if font_size > avg_font_size * 1.2:
            is_heading = True
            heading_level = 1

        # 策略2: 使用结构检测
        if not is_heading:
            detector = create_detector()
            is_heading, reason = detector.is_likely_heading(text)
            if is_heading:
                heading_level = detector.detect_heading_level(text)

        return is_heading, heading_level

    def _extract_page_blocks(self, page) -> List[Dict[str, Any]]:
        """
        提取页面文本块及字体信息

        Returns:
            [{'text': str, 'font_size': float, 'font_name': str}, ...]
        """
        blocks = []

        # 获取页面文本，使用dict模式获取更详细的样式信息
        text_dict = page.get_text("dict")

        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:  # 非文本块
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if text:
                        blocks.append({
                            'text': text,
                            'font_size': span.get("size", 12),
                            'font_name': span.get("font", ""),
                        })

        return blocks

    def _extract_tables(self, page) -> List[Dict[str, Any]]:
        """
        从页面提取表格

        Returns:
            [{'bbox': (x0, y0, x1, y1), 'rows': [[cell1, cell2, ...], ...]}, ...]
        """
        tables = []

        try:
            # PyMuPDF 1.22+ 支持 find_tables()
            table_manager = page.find_tables()
            for table in table_manager.tables:
                bbox = table.bbox
                extracted = table.extract()

                if extracted and len(extracted) > 0:
                    # 清理表格数据
                    cleaned_rows = []
                    for row in extracted:
                        cleaned_row = [cell.strip() if cell else '' for cell in row]
                        if any(cleaned_row):  # 跳过空行
                            cleaned_rows.append(cleaned_row)

                    if cleaned_rows:
                        tables.append({
                            'bbox': bbox,
                            'rows': cleaned_rows
                        })
        except AttributeError:
            # 旧版本 PyMuPDF 不支持 find_tables，使用备选方案
            pass

        return tables

    def _format_table_as_text(self, table_data: Dict[str, Any]) -> str:
        """
        将表格格式化为带分隔符的文本

        Args:
            table_data: {'rows': [[cell1, cell2], [cell3, cell4], ...]}

        Returns:
            | cell1 | cell2 |
            | cell3 | cell4 |
        """
        rows = table_data['rows']
        if not rows:
            return ''

        # 计算每列的最大宽度
        col_widths = []
        for row in rows:
            for i, cell in enumerate(row):
                cell_len = len(cell)
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], cell_len)
                else:
                    col_widths.append(cell_len)

        # 格式化每一行
        formatted_rows = []
        for row in rows:
            cells = []
            for i, cell in enumerate(row):
                width = col_widths[i] if i < len(col_widths) else len(cell)
                cells.append(cell.ljust(width))
            formatted_rows.append('| ' + ' | '.join(cells) + ' |')

        return '\n'.join(formatted_rows)

    def _extract_images(self, page) -> List[Dict[str, Any]]:
        """
        从页面提取图片信息

        Returns:
            [{'bbox': (x0, y0, x1, y1), 'width': int, 'height': int, 'image_type': str}, ...]
        """
        images = []
        page_width = page.rect.width
        page_height = page.rect.height
        page_area = page_width * page_height

        # 获取页面中的图片
        image_list = page.get_images(full=True)

        for img_index, img in enumerate(image_list):
            # 获取图片的位置信息
            # xref 是图片的引用
            xref = img[0]

            try:
                # 获取图片尺寸
                base_image = page.parent.extract_image(xref)
                img_width = base_image.get('width', 0)
                img_height = base_image.get('height', 0)

                # 尝试获取图片在页面中的位置
                # 通过搜索图片附近的文本或使用其他方法定位
                img_bbox = self._find_image_bbox(page, xref)

                if img_bbox:
                    bbox = img_bbox
                else:
                    # 如果找不到位置，使用默认值
                    bbox = (0, 0, img_width, img_height)

                # 计算图片占页面面积的比例
                img_area = img_width * img_height
                area_ratio = img_area / page_area if page_area > 0 else 0

                # 判断图片类型
                image_type = self._classify_image(
                    img_width, img_height, page_width, page_height, area_ratio
                )

                images.append({
                    'bbox': bbox,
                    'width': img_width,
                    'height': img_height,
                    'image_type': image_type,
                    'area_ratio': area_ratio,
                    'page': page.number + 1,
                })

            except Exception:
                # 忽略无法提取的图片
                continue

        return images

    def _find_image_bbox(self, page, xref: int) -> Optional[Tuple]:
        """尝试找到图片在页面中的位置"""
        # PyMuPDF 不直接提供图片位置，需要通过其他方式推断
        # 一种方法是查找包含图像引用的textdict块
        try:
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                # 检查block是否包含图像
                if block.get("type") == 1:  # image block
                    if block.get("xref") == xref:
                        return block.get("bbox")
        except Exception:
            pass

        return None

    def _classify_image(self, img_width: int, img_height: int,
                        page_width: float, page_height: float,
                        area_ratio: float) -> str:
        """
        根据图片尺寸和位置判断图片类型

        Returns:
            image_type: 'signature' | 'seal' | 'photo' | 'image'
        """
        # 小图片可能是签章或印章
        if area_ratio < self.SEAL_SIZE_THRESHOLD:
            return 'seal'
        elif area_ratio < self.SIGNATURE_SIZE_THRESHOLD:
            # 根据长宽比进一步判断
            if img_height > img_width * 2:
                return 'signature'  # 长条形可能是签名
            else:
                return 'seal'  # 方形可能是印章

        # 大图片可能是附件照片
        if area_ratio > 0.3:
            return 'photo'

        return 'image'

    def _format_image_placeholder(self, image_info: Dict[str, Any]) -> str:
        """生成图片占位符文本"""
        image_type = image_info.get('image_type', 'image')

        placeholders = {
            'signature': '[签名]',
            'seal': '[印章]',
            'photo': '[图片附件]',
            'image': '[图片]'
        }

        return placeholders.get(image_type, '[图片]')

    def _collect_font_sizes(self, doc) -> List[float]:
        """收集文档中所有字体大小"""
        font_sizes = []

        for page in doc:
            blocks = self._extract_page_blocks(page)
            for block in blocks:
                font_sizes.append(block['font_size'])

        return font_sizes

    def _determine_section_type(self, title: str, level: int) -> str:
        """根据标题和级别判断section类型"""
        title_lower = title.lower()

        if 'appendix' in title_lower or '附件' in title:
            return 'appendix'
        if 'chapter' in title_lower or '第' in title and '章' in title:
            return 'chapter'
        if 'article' in title_lower or '第' in title and '条' in title:
            return 'clause'

        if level == 1:
            return 'chapter'
        elif level == 2:
            return 'clause'
        elif title == 'Preamble':
            return 'preamble'
        else:
            return 'section'

    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取PDF文件的元数据"""
        doc = fitz.open(file_path)
        metadata = {
            'file_name': file_path,
            'total_pages': len(doc),
            'file_type': 'pdf'
        }

        # 提取PDF元数据
        pdf_metadata = doc.metadata
        if pdf_metadata:
            metadata['title'] = pdf_metadata.get('title', '')
            metadata['author'] = pdf_metadata.get('author', '')
            metadata['subject'] = pdf_metadata.get('subject', '')
            metadata['creator'] = pdf_metadata.get('creator', '')

        doc.close()
        return metadata
