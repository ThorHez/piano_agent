"""
演奏相关API
"""
import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, Path, HTTPException
try:
    from sse_starlette.sse import EventSourceResponse
except ImportError:
    from fastapi.responses import StreamingResponse as EventSourceResponse
from src.utils import generate_id, get_current_timestamp
from src.database import db_manager, PerformanceHistoryDB


router = APIRouter()


# 用于存储SSE连接的活跃状态
active_streams = {}



@router.post("/performance/stream", summary="曲目演奏接口（流式）")
async def performance_stream(
    # token: dict = Depends(verify_token)
):
    """
    曲目演奏接口，流式返回演奏状态
    """
    async def generate():
        for i in range(5):
            message = {
                "type": "performance",
                "id": generate_id(),
                "sessionId": "perf_session",
                "timestamp": get_current_timestamp().isoformat(),
                "content": f"演奏进度: {(i+1)*20}%",
                "status": 200 if i == 4 else None
            }
            yield {
                "event": "message",
                "data": json.dumps(message)
            }
            await asyncio.sleep(1)
    
    return EventSourceResponse(generate())

