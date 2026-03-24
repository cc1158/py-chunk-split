# 文档目录

## API 文档

- [API 使用指南](README.md) - 中文 API 文档
- [OpenAPI 规范 (JSON)](openapi.json) - 机器可读的 API 规范
- [OpenAPI 规范 (YAML)](openapi.yaml) - 机器可读的 API 规范

## 在线文档

启动服务后可在浏览器中访问：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 快速开始

### 1. 启动服务

```bash
uvicorn app.api.main:app --reload --port 8000
```

### 2. 测试上传

```bash
curl -X POST "http://localhost:8000/api/v1/chunk" \
  -F "file=@your_contract.pdf" \
  -F "request_id=req_001" \
  -F "max_tokens=500"
```

### 3. 查看健康状态

```bash
curl http://localhost:8000/api/v1/health
```
