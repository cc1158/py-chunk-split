from fastapi import FastAPI

from .router import router


app = FastAPI(
    title="法律合同RAG切分工具",
    description="用于将法律合同文档智能切分为适合检索增强生成（RAG）应用的文本块",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 注册路由
app.include_router(router)


@app.get("/")
async def root():
    """根路径跳转提示"""
    return {
        "message": "法律合同RAG切分工具 API",
        "docs": "/docs",
        "redoc": "/redoc",
    }
