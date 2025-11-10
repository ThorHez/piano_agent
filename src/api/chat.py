"""
聊天相关API
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, Query
try:
    from sse_starlette.sse import EventSourceResponse
except ImportError:
    from fastapi.responses import StreamingResponse as EventSourceResponse
from src.models import Message
from src.utils import generate_id, generate_session_id, get_current_timestamp

from src.graph.agent import agent


router = APIRouter()


async def generate_chat_voice_stream(sessionId: str, mode: Optional[str] = None):
    """生成语音转文字流"""
    if mode == "learning":
        # 流式返回 agent 的执行结果（使用异步流）
        async for chunk in agent.astream({"messages": [], "context": {"session_id": sessionId, "mode": mode}}, stream_mode="custom"):
            # chunk 已经是 JSON 字符串，按 SSE 格式返回
            if chunk:
                yield f"data: {chunk}"
                await asyncio.sleep(0)  # 让出控制权，确保每条消息立即发送
    else:
        # 第一条消息
        first_message = Message(
            type="assistant",
            id=generate_id(),
            sessionId=sessionId,
            timestamp=get_current_timestamp(),
            content="请问您想听什么曲子？",
            status=200
        )
        yield f"data: {first_message.model_dump_json()}"
        await asyncio.sleep(0)  # 让出控制权，确保数据被发送

        # 流式返回 agent 的执行结果（使用异步流）
        async for chunk in agent.astream({"messages": [], "context": {"session_id": sessionId, "mode": mode}}, stream_mode="custom"):
            # chunk 已经是 JSON 字符串，按 SSE 格式返回
            if chunk:
                yield f"data: {chunk}"
                await asyncio.sleep(0)  # 让出控制权，确保每条消息立即发送




@router.post("/chat", summary="聊天主接口")
async def chat(
    mode: Optional[str] = Query(None, description="模式（可选）"),
    # token: dict = Depends(verify_token)  # 可选：取消注释以启用认证
):
    """
    聊天主接口，流式返回响应
    
    参数:
        mode: 可选的模式参数，如果未提供则使用默认模式
              可选值: "voice" (语音模式), "text" (文本模式), 默认为 None
    """
    session_id = generate_session_id()
    return EventSourceResponse(generate_chat_voice_stream(session_id, mode))





@router.get("/chat/voice", summary="语音转文字")
async def chat_voice(
    sessionId: str = Query(...),
    # token: dict = Depends(verify_token)
):
    """
    触发语音服务，返回语音转文字结果
    """
    return EventSourceResponse(generate_chat_voice_stream(sessionId))
