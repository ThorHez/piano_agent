#!/usr/bin/env python
"""
启动脚本 - 读取配置并启动服务
"""
import sys
import os

# 确保项目根目录在 Python 路径中
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def main():
    """运行服务器"""
    import uvicorn
    from src.config import config
    
    print("=" * 60)
    print("🎹 Termitech Auto-Piano API Service")
    print("=" * 60)
    print("\n📋 配置信息:")
    print(f"   - 主机: {config.server_host}")
    print(f"   - 端口: {config.server_port}")
    print(f"   - 热重载: {config.server_reload}")
    print(f"   - 日志级别: {config.log_level}")
    print("\n🚀 启动服务器...")
    print("\n📝 API 文档:")
    print(f"   - Swagger UI: http://localhost:{config.server_port}/docs")
    print(f"   - ReDoc: http://localhost:{config.server_port}/redoc")
    print(f"   - OpenAPI JSON: http://localhost:{config.server_port}/openapi.json")
    print("\n" + "=" * 60 + "\n")
    
    # 使用配置文件中的参数启动服务
    # timeout_keep_alive=0 和其他配置确保流式响应不被缓冲
    uvicorn.run(
        "src.server:app",
        host=config.server_host,
        port=config.server_port,
        reload=config.server_reload,
        log_level=config.log_level.lower(),
        timeout_keep_alive=120,  # 保持连接时间
        ws_ping_interval=None,   # 禁用 WebSocket ping
        ws_ping_timeout=None     # 禁用 WebSocket ping 超时
    )


if __name__ == "__main__":
    main()
