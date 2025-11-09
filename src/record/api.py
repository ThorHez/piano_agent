"""
录音相关API
"""
import json
import threading
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from sse_starlette.sse import EventSourceResponse
except ImportError:
    from fastapi.responses import StreamingResponse as EventSourceResponse

from midi_record_intime import MidiPianoRecorder



app = FastAPI(
    title="Termitech Auto-Piano API (SSE)",
    version="1.1.0",
    description="",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def record_stream():
    recorder = MidiPianoRecorder()
    
    # 选择并连接MIDI设备
    if recorder.select_device():
        # 开始监听
        threading.Thread(target=recorder.start_recording, daemon=True).start()
        
        # 获取事件循环
        loop = asyncio.get_event_loop()
        
        while True:
            # 在线程池中运行阻塞的 get_message() 调用
            message = await loop.run_in_executor(None, recorder.get_message)
            print(f"message: {message}")
            
            yield f"{message}"



@app.get("/record", summary="语音转文字")
async def chat_voice():
    """
    触发语音服务，返回语音转文字结果
    """
    return EventSourceResponse(record_stream())