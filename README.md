# 法律合同RAG切分工具

用于将法律合同文档智能切分为适合检索增强生成（RAG）应用的文本块。

## 功能特点

- **多格式支持**：支持 PDF、DOCX、TXT 等文档格式
- **混合切分策略**：先按语义（章节/条款）切分，超长时再按长度切分
- **法律文档感知**：自动识别中文法律文档结构（第X条、第X章、附件等）
- **多语言支持**：支持中文、英文、日文、韩文等多种语言的合同文档
- **表格完整保留**：表格作为完整结构保留，不拆分
- **图片占位符**：图片转换为 `[图片]` 占位符

## 安装

```bash
pip install -r requirements.txt
```

依赖说明：
- `PyMuPDF`：PDF 文档解析
- `python-docx`：Word 文档解析
- `pydantic`：数据验证
- `tiktoken`：Token 计数

## 使用方法

### 处理单个文件

```bash
python main.py contract.pdf -o output.json
python main.py contract.docx -o output.json
python main.py contract.txt -o output.json
```

### 批量处理目录

```bash
python main.py contracts/ -o output.json
```

### 自定义切分参数

```bash
# 设置最大token数（默认500）
python main.py contract.pdf -o output.json --max-tokens 800

# 设置重叠token数（默认50）
python main.py contract.pdf -o output.json --overlap-tokens 100

# 启用详细输出
python main.py contract.pdf -o output.json -v
```

## 输出格式

输出的 JSON 文件包含所有切分后的文本块，每个块包含：

```json
[
  {
    "content": "第一条 发包人向承包人提供...",
    "metadata": {
      "title": "第一条",
      "level": 2,
      "page_number": 1,
      "type": "clause",
      "file_name": "contract.pdf",
      "file_type": "pdf"
    },
    "chunk_index": 0,
    "token_count": 350,
    "previous_chunk_index": null,
    "next_chunk_index": 1
  }
]
```

### 字段说明

| 字段 | 说明 |
|------|------|
| content | 文本内容 |
| metadata.title | 章节标题（如"第一条"、"附件1"） |
| metadata.level | 标题级别（1=章，2=条，0=其他） |
| metadata.type | 类型：chapter/clause/section/appendix/table/image/preamble |
| metadata.page_number | 页码 |
| metadata.file_name | 原始文件名 |
| chunk_index | 块在文档中的索引 |
| token_count | 预估token数 |
| previous_chunk_index | 上一个块的索引（用于关联检索） |
| next_chunk_index | 下一个块的索引 |

### 类型说明

| type | 说明 |
|------|------|
| chapter | 章节（如"第一章"、"Part 1"） |
| clause | 条款（如"第一条"、"Article 1"） |
| section | 小节 |
| appendix | 附件（如"附件1"、"Appendix A"） |
| table | 表格（内容为Markdown格式） |
| image | 图片（内容为占位符） |
| preamble | 序言/正文 |

## 项目结构

```
py-chunk-split/
├── src/
│   ├── __init__.py
│   ├── parser/              # 文档解析模块
│   │   ├── __init__.py
│   │   ├── base.py         # 解析器基类
│   │   ├── pdf_parser.py   # PDF解析器
│   │   ├── docx_parser.py  # DOCX解析器
│   │   └── txt_parser.py   # TXT解析器
│   ├── splitter/            # 切分策略模块
│   │   ├── __init__.py
│   │   ├── base.py         # 切分器基类
│   │   ├── semantic_splitter.py   # 语义切分
│   │   └── length_splitter.py     # 长度切分
│   ├── models/              # 数据模型
│   │   ├── __init__.py
│   │   └── chunk.py        # Chunk数据模型
│   └── processor.py         # 主处理器
├── tests/                   # 单元测试
├── test_doc/               # 测试文档
├── main.py                 # 命令行入口
└── requirements.txt        # 依赖列表
```

## 切分策略

### 1. 语义切分

首先识别文档的语义结构：

- **条款识别**：`^第[一二三四五六七八九十百]+条`
- **章节识别**：`^第[一二三四五六七八九十百]+章`
- **附件识别**：`^附件[一二三四五六七八九十]+`
- **多语言支持**：支持中文、英文、日文、韩文等多种编号格式

### 2. 长度切分

当章节内容超过 `max_tokens` 时，触发长度切分：

- 按段落边界切分，避免在句子中间断开
- 保持语义完整性

### 3. 小块合并

当文本块小于 `min_tokens`（默认100）时，自动与后续块合并，直到达到最小阈值。

### 4. 特殊处理

- **表格**：作为完整语义单元保留，不拆分。表格内容格式化为标准 Markdown，包含标题行和分隔行。
- **图片**：作为独立语义单元，内容仅为 `[图片]` 占位符，不与其他内容合并。
- **图片分隔符**：图片会打断文本连续性，图片前后的文本分别成为独立的块。

## 支持的文件格式

| 格式 | 扩展名 | 解析器 |
|------|--------|--------|
| PDF | .pdf | PyMuPDF |
| Word | .docx, .doc | python-docx |
| 文本 | .txt, .text | 内置解析器 |

## 法律文档结构识别

工具自动识别以下法律文档结构模式：

```
第X条          # 条款（如：第一条、第二条）
第X章          # 章节（如：第一章、第二章）
附件X          # 附件（如：附件1、附件一）
Article X      # 英文条款
Chapter X     # 英文章节
Appendix X    # 英文附件
(1) (2)       # 子条款编号
1. 2. 3.      # 列表编号
一、二、三     # 中文数字列表
甲方/乙方      # 合同当事人
```

## 使用示例

### 处理 PDF 合同

```bash
python main.py contract.pdf -o output.json --max-tokens 500 -v
```

### 处理 DOCX 合同

```bash
python main.py "海南省装配式建设项目工程总承包合同.docx" -o output.json -v
```

### 批量处理

```bash
python main.py test_doc/ -o all_contracts.json
```

### Python API

```python
from src.processor import ContractProcessor

processor = ContractProcessor(max_tokens=500, overlap_tokens=50)
chunks = processor.process('contract.pdf')

for chunk in chunks:
    print(f"Title: {chunk.metadata.get('title')}")
    print(f"Type: {chunk.metadata.get('type')}")
    print(f"Content: {chunk.content[:100]}...")
    print()
```
