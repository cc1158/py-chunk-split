import os
import tempfile
from typing import List
from fastapi import UploadFile

from core.processor import ContractProcessor
from core.models.chunk import Chunk
from .schemas import (
    ChunkMetadata,
    ChunkResponse,
    ChunkResultData,
    ChunkResultResponse,
)


class ChunkService:
    """文件处理和转换服务"""

    def __init__(self):
        self.processor = ContractProcessor()

    async def process_upload(
        self,
        file: UploadFile,
        request_id: str,
        max_tokens: int = 500,
        overlap_tokens: int = 50,
        min_tokens: int = 100,
    ) -> ChunkResultResponse:
        """
        处理上传的文件并返回切分结果。

        Args:
            file: 上传的文件
            request_id: 请求唯一标识
            max_tokens: 每个chunk最大token数
            overlap_tokens: 相邻chunk重叠token数
            min_tokens: 最小token数

        Returns:
            ChunkResultResponse: 包含切分结果的响应
        """
        # 创建临时文件保存上传内容
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".tmp"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # 使用新的参数创建processor实例
            processor = ContractProcessor(
                max_tokens=max_tokens,
                overlap_tokens=overlap_tokens,
                min_tokens=min_tokens,
            )

            # 处理文件
            chunks: List[Chunk] = processor.process(tmp_path)

            # 转换为API响应格式
            return self._build_response(
                request_id=request_id,
                file_name=file.filename or "unknown",
                chunks=chunks,
            )
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _build_response(
        self,
        request_id: str,
        file_name: str,
        chunks: List[Chunk],
    ) -> ChunkResultResponse:
        """构建API响应"""
        chunk_responses = []

        for chunk in chunks:
            metadata_dict = chunk.metadata

            chunk_response = ChunkResponse(
                request_id=request_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                metadata=ChunkMetadata(
                    title=metadata_dict.get("title", ""),
                    type=metadata_dict.get("type", ""),
                    level=metadata_dict.get("level", 0),
                    page_number=metadata_dict.get("page_number", 1),
                    file_name=metadata_dict.get("file_name", file_name),
                ),
                token_count=chunk.token_count,
                previous_chunk_index=chunk.previous_chunk_index,
                next_chunk_index=chunk.next_chunk_index,
            )
            chunk_responses.append(chunk_response)

        data = ChunkResultData(
            request_id=request_id,
            file_name=file_name,
            total_chunks=len(chunk_responses),
            chunks=chunk_responses,
        )

        return ChunkResultResponse(
            code=200,
            message="success",
            data=data,
        )


# 全局服务实例
chunk_service = ChunkService()
