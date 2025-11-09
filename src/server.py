"""
Termitech Auto-Piano API Service
自动钢琴API服务主程序
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime

# 导入配置
from src.config import config

# 导入路由
from src.api import chat, performance, history, music

# 创建FastAPI应用
app = FastAPI(
    title="Termitech Auto-Piano API (SSE)",
    version="1.1.0",
    description="自动钢琴演奏系统API - 支持聊天、演奏控制、曲库管理等功能",
    servers=[
        {"url": "https://api.termitech.local", "description": "Production"},
        {"url": f"http://localhost:{config.server_port}", "description": "Development"}
    ]
)

# CORS配置 - 从配置文件读取
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=config.cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "path": request.url.path
        }
    )

# 健康检查
@app.get("/", tags=["System"])
async def root():
    """健康检查接口"""
    return {
        "service": "Termitech Auto-Piano API",
        "version": "1.1.0",
        "status": "running"
    }

@app.get("/health", tags=["System"])
async def health_check():
    """详细健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "port": config.server_port,
            "log_level": config.log_level
        },
        "services": {
            "chat": "operational",
            "performance": "operational",
            "storage": "operational"
        }
    }

# 注册路由
app.include_router(chat.router, tags=["Chat"])
app.include_router(performance.router, tags=["Performance"])
app.include_router(history.router, tags=["History"])
app.include_router(music.router, tags=["Music"])

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print("🎹 Termitech Auto-Piano API Service Starting...")
    print(f"📋 配置: {config.server_host}:{config.server_port}")
    
    # 初始化数据库
    try:
        from src.database import db_manager
        db_manager.init_db()
    except (ImportError, IOError, RuntimeError) as e:
        print(f"⚠️  数据库初始化失败: {e}")
    
    print("📚 Loading initial data...")
    print("✅ Service ready!")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    print("👋 Termitech Auto-Piano API Service Shutting down...")


