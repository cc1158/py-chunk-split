from fastapi import APIRouter, File, Form, UploadFile

from .schemas import (
    ChunkResultResponse,
    HealthResponse,
    InfoResponse,
)
from .service import chunk_service


router = APIRouter(prefix="/api/v1")


@router.post("/chunk", response_model=ChunkResultResponse)
async def chunk_file(
    file: UploadFile = File(..., description="合同文件（PDF/DOCX/TXT）"),
    request_id: str = Form(..., description="请求唯一标识，用于异步通知/消息推送时标识chunk属于哪个请求"),
    max_tokens: int = Form(default=500, description="每个chunk最大token数"),
    overlap_tokens: int = Form(default=50, description="相邻chunk重叠token数"),
    min_tokens: int = Form(default=100, description="最小token数，小于此值会合并"),
):
    """
    上传合同文件并获取切分结果。

    支持的文件格式：PDF、DOCX、DOC、TXT、TEXT
    """
    return await chunk_service.process_upload(
        file=file,
        request_id=request_id,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
        min_tokens=min_tokens,
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    return HealthResponse(status="healthy", version="1.0.0")


@router.get("/info", response_model=InfoResponse)
async def get_info():
    """获取服务信息"""
    return InfoResponse(
        name="法律合同RAG切分工具",
        version="1.0.0",
        supported_formats=[".pdf", ".docx", ".doc", ".txt", ".text"],
        parameters={
            "max_tokens": {"default": 500, "description": "每个chunk最大token数"},
            "overlap_tokens": {"default": 50, "description": "相邻chunk重叠token数"},
            "min_tokens": {"default": 100, "description": "最小token数"},
        },
    )
