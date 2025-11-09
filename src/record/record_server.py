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
    
    # 使用配置文件中的参数启动服务
    # timeout_keep_alive=0 和其他配置确保流式响应不被缓冲
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8123,
        reload=True,
        timeout_keep_alive=120,  # 保持连接时间
        ws_ping_interval=None,   # 禁用 WebSocket ping
        ws_ping_timeout=None     # 禁用 WebSocket ping 超时
    )


if __name__ == "__main__":
    main()
