# 法律合同RAG切分工具 - API 文档

## 概述

本 API 服务用于将法律合同文档智能切分为适合检索增强生成（RAG）应用的文本块。

**Base URL**: `http://localhost:8000`

**API 文档**:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 认证

本 API 目前无需认证。

---

## 服务信息

### GET /api/v1/info

获取服务信息。

**响应示例**:

```json
{
  "name": "法律合同RAG切分工具",
  "version": "1.0.0",
  "supported_formats": [".pdf", ".docx", ".doc", ".txt", ".text"],
  "parameters": {
    "max_tokens": {"default": 500, "description": "每个chunk最大token数"},
    "overlap_tokens": {"default": 50, "description": "相邻chunk重叠token数"},
    "min_tokens": {"default": 100, "description": "最小token数"}
  }
}
```

---

### GET /api/v1/health

健康检查接口。

**响应示例**:

```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## 文档切分

### POST /api/v1/chunk

上传合同文件并获取切分结果。

**请求类型**: `multipart/form-data`

**请求参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| file | UploadFile | **是** | - | 合同文件（PDF/DOCX/TXT） |
| request_id | string | **是** | - | 请求唯一标识，用于异步通知/消息推送时标识chunk属于哪个请求 |
| max_tokens | int | 否 | 500 | 每个chunk最大token数 |
| overlap_tokens | int | 否 | 50 | 相邻chunk重叠token数 |
| min_tokens | int | 否 | 100 | 最小token数，小于此值会合并 |

**请求示例**:

```bash
curl -X POST "http://localhost:8000/api/v1/chunk" \
  -F "file=@contract.pdf" \
  -F "request_id=req_20260324_001" \
  -F "max_tokens=500" \
  -F "overlap_tokens=50" \
  -F "min_tokens=100"
```

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "request_id": "req_20260324_001",
    "file_name": "contract.pdf",
    "total_chunks": 10,
    "chunks": [
      {
        "request_id": "req_20260324_001",
        "chunk_index": 0,
        "content": "第一条 发包人向承包人提供...",
        "metadata": {
          "title": "第一条",
          "type": "clause",
          "level": 2,
          "page_number": 1,
          "file_name": "contract.pdf"
        },
        "token_count": 350,
        "previous_chunk_index": null,
        "next_chunk_index": 1
      }
    ]
  }
}
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码（200=成功） |
| message | string | 返回信息 |
| data.request_id | string | 请求标识（透传） |
| data.file_name | string | 文件名 |
| data.total_chunks | int | chunk总数 |
| data.chunks | array | chunk列表 |

**Chunk 对象字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| request_id | string | 请求标识 |
| chunk_index | int | chunk索引 |
| content | string | chunk文本内容 |
| metadata.title | string | 章节标题 |
| metadata.type | string | 类型：chapter/clause/section/appendix/table/image/preamble |
| metadata.level | int | 标题级别（1=章，2=条，0=其他） |
| metadata.page_number | int | 页码 |
| metadata.file_name | string | 原始文件名 |
| token_count | int | token数 |
| previous_chunk_index | int/null | 上一个chunk索引 |
| next_chunk_index | int/null | 下一个chunk索引 |

---

## 错误码

| code | 说明 |
|------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 413 | 文件过大 |
| 415 | 不支持的文件格式 |
| 500 | 服务器内部错误 |

---

## 使用示例

### Python 示例

```python
import requests

url = "http://localhost:8000/api/v1/chunk"

with open("contract.pdf", "rb") as f:
    files = {"file": f}
    data = {
        "request_id": "req_001",
        "max_tokens": 500,
        "overlap_tokens": 50,
        "min_tokens": 100
    }
    response = requests.post(url, files=files, data=data)

print(response.json())
```

### JavaScript 示例

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('request_id', 'req_001');
formData.append('max_tokens', '500');

fetch('http://localhost:8000/api/v1/chunk', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```
