"""
录音相关API
"""
import json
import threading
import asyncio

from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware

try:
    from sse_starlette.sse import EventSourceResponse
except ImportError:
    from fastapi.responses import StreamingResponse as EventSourceResponse

from midi_record_intime_v2 import MidiPianoRecorder

from datetime import datetime

import os
import random



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


midi_base_dir = "/Users/hezhili/PycharmProjects/piano_agent_service/data/midi/"


# ==================== 清理处理函数 ====================

async def cleanup_handler(session_id: str, message_count: int, recorder: MidiPianoRecorder, do_record: bool = False):
    """
    自定义清理和后处理逻辑
    
    参数:
        session_id: 会话ID
        message_count: 接收到的消息数量
        recorder: MidiPianoRecorder 实例
        fingering_file_path: 指法文件路径
    """
    print(f"[{session_id}] 执行自定义后处理...")
    
    try:
        # 1. 保存会话统计到数据库（示例）
        # from src.database import db_manager
        # with db_manager.get_session() as db:
        #     db.execute(
        #         "INSERT INTO recording_sessions (session_id, message_count, end_time) VALUES (?, ?, ?)",
        #         (session_id, message_count, datetime.now())
        #     )
        
        # 2. 发送通知（示例）
        if message_count > 100:
            print(f"[{session_id}] 提示: 本次录音消息量较大 ({message_count} 条)")

        if do_record:
            print(f"[{session_id}] 开始录制MIDI文件")
            os.makedirs(os.path.dirname(midi_base_dir), exist_ok=True)
            midi_file_path = os.path.join(midi_base_dir, "record.midi")
            if os.path.exists(midi_file_path):
                os.remove(midi_file_path)
            recorder.save_to_midi(filename=midi_file_path)
        print(f"[{session_id}] 自定义后处理完成")
        
    except Exception as e:  # noqa: 捕获所有后处理异常以确保不影响主流程
        print(f"[{session_id}] 后处理错误: {e}")


async def record_stream(request: Request, do_record: bool = False):
    """
    MIDI录音流式接口
    
    参数:
        request: FastAPI Request 对象，用于检测客户端断开
        fingering_file_path: 指法文件路径（可选）
    """
    recorder = MidiPianoRecorder()
    session_id = f"record_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    message_count = 0
    
    print(f"[{session_id}] 录音流开始")
    
    try:
        # 选择并连接MIDI设备
        if not recorder.select_device():
            error_msg = {"error": "无法连接MIDI设备"}
            yield json.dumps(error_msg)
            return
        
        # 开始监听
        threading.Thread(target=recorder.start_recording, daemon=True).start()
        print(f"[{session_id}] MIDI录音线程已启动")
        
        # 获取事件循环
        loop = asyncio.get_event_loop()
        
        while True:
            # 检查客户端是否断开
            if await request.is_disconnected():
                print(f"[{session_id}] 检测到客户端断开连接")
                break
            
            try:
                # 在线程池中运行阻塞的 get_message() 调用，设置超时
                message = await asyncio.wait_for(
                    loop.run_in_executor(None, recorder.get_message),
                    timeout=1.0
                )
                
                message_count += 1
                # print(f"[{session_id}] 消息 #{message_count}: {message}")
                
                yield json.dumps(message)
            except asyncio.TimeoutError:
                # 超时继续循环，用于检测断开
                await asyncio.sleep(0.1)
                continue
            except Exception as e:  # noqa: 捕获所有消息获取异常以保持流稳定
                print(f"[{session_id}] 获取消息错误: {e}")
                await asyncio.sleep(0.1)
                continue
    
    except asyncio.CancelledError:
        print(f"[{session_id}] 流被取消")
        raise
    
    except Exception as e:  # noqa: 捕获所有流异常以确保资源清理
        print(f"[{session_id}] 录音流异常: {e}")
        error_msg = {"error": f"录音流异常: {str(e)}"}
        yield json.dumps(error_msg)
    
    finally:
        # 后处理：清理资源
        print(f"[{session_id}] 开始清理资源...")
        
        try:
            # 1. 停止录音器（如果有相关方法）
            if recorder and hasattr(recorder, 'should_stop'):
                recorder.should_stop = True
                print(f"[{session_id}] 录音器停止信号已发送")
            
            # 2. 保存录音数据（如果需要）
            if message_count > 0:
                print(f"[{session_id}] 共接收 {message_count} 条MIDI消息")
            
            # 后处理：清理资源
            await cleanup_handler(session_id, message_count, recorder, do_record)
            # 3. 释放MIDI设备
            if hasattr(recorder, 'port') and recorder.port:
                try:
                    recorder.port.close()
                    print(f"[{session_id}] MIDI端口已关闭")
                except Exception:  # noqa: 捕获所有端口关闭异常
                    pass
            
            # 4. 记录统计信息
            print(f"[{session_id}] 录音会话结束统计:")
            print(f"  - 会话ID: {session_id}")
            print(f"  - 消息数量: {message_count}")
            print(f"  - 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")          
        except Exception as cleanup_error:  # noqa: 捕获所有清理异常以避免影响主流程
            print(f"[{session_id}] 清理资源时出错: {cleanup_error}")
        
        print(f"[{session_id}] 录音流完全结束")


async def record_stream_mock():
    while True:
        random_midi_id = random.randint(21, 108)
        mock_data = {
            "action": "note_on",
            "key_name": "C4",
            "timestamp": datetime.now().timestamp(),
            "hand": "left",
            "midi_id": random_midi_id
        }
        yield json.dumps(mock_data)
        await asyncio.sleep(1)

        mock_data = {
            "action": "note_off",
            "key_name": "C4",
            "timestamp": datetime.now().timestamp(),
            "hand": "left",
            "midi_id": random_midi_id
        }
        yield json.dumps(mock_data)



@app.get("/record", summary="MIDI录音流式接口")
async def record(
    request: Request, 
    do_record: bool = Query(False, description="是否保存MIDI录音文件")
):
    """
    MIDI录音流式接口
    
    支持断开检测和自动清理资源
    
    参数:
        do_record: 是否保存MIDI录音文件（默认: False）
    
    返回:
        SSE流式数据，包含MIDI消息
    
    使用示例:
        # 不保存录音
        curl -N "http://localhost:8123/record"
        
        # 保存录音
        curl -N "http://localhost:8123/record?do_record=true"
    """
    print(f"record: do_record: {do_record}")
    return EventSourceResponse(record_stream(request, do_record))


@app.get("/record_mock", summary="语音转文字")
async def record_mock():
    """
    触发语音服务，返回语音转文字结果
    """
    return EventSourceResponse(record_stream_mock())