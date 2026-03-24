from pydantic import BaseModel, Field
from typing import Optional, List


class ChunkMetadata(BaseModel):
    """chunk 元数据（API 返回用）"""
    title: str = ""
    type: str = ""
    level: int = 0
    page_number: int = 1
    file_name: str = ""


class ChunkResponse(BaseModel):
    """单个 chunk 的 API 响应实体"""
    request_id: str = Field(description="请求标识")
    chunk_index: int = Field(description="chunk 索引")
    content: str = Field(description="chunk 文本内容")
    metadata: ChunkMetadata
    token_count: int = Field(description="token 数")
    previous_chunk_index: Optional[int] = Field(default=None, description="上一个 chunk 索引")
    next_chunk_index: Optional[int] = Field(default=None, description="下一个 chunk 索引")


class ChunkResultData(BaseModel):
    """POST /api/v1/chunk 返回的 data 部分"""
    request_id: str
    file_name: str
    total_chunks: int
    chunks: List[ChunkResponse]


class ChunkResultResponse(BaseModel):
    """POST /api/v1/chunk 完整响应"""
    code: int
    message: str
    data: ChunkResultData


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str


class InfoResponse(BaseModel):
    """服务信息响应"""
    name: str
    version: str
    supported_formats: List[str]
    parameters: dict
