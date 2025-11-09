from langgraph.graph import StateGraph
from typing import Annotated, TypedDict
import operator

from langgraph.graph.state import START, END

from src.database import db_manager
from src.models import Message, MessageType
import time
import asyncio
import json

from src.utils import generate_id
from langgraph.config import get_stream_writer

import httpx

from src.config import config

from src.utils import async_post

import re

from src.database import PerformanceHistoryDB
from datetime import datetime


def merge_dicts(left: dict, right: dict) -> dict:
    """
    合并两个字典（右侧覆盖左侧）
    
    相当于: left.update(right) 并返回新字典
    """
    result = {**left, **right}
    return result


class PianoAgentState(TypedDict):
    messages: Annotated[list[Message], operator.add]
    context: Annotated[dict, merge_dicts]  # 使用自定义合并函数，不能用 operator.add



def mock_voice_to_text(state: PianoAgentState) -> PianoAgentState:
    writer = get_stream_writer()
    if writer:
        message = Message(
            type=MessageType.user, 
            content="我想听大鱼", 
            sessionId=state["context"]["session_id"], 
            id=generate_id()
        )
        writer(message.model_dump_json())

        message = Message(
            type=MessageType.assistant, 
            content="好的，理解您想要听《大鱼》", 
            sessionId=state["context"]["session_id"], 
            id=generate_id()
        )
        writer(message.model_dump_json())

        state["context"]["song_name"] = "大鱼"
    return state


async def voice_to_text(state: PianoAgentState) -> PianoAgentState:
    async with httpx.AsyncClient(timeout=3600.0) as client:
        async with client.stream(
            "POST",
            config.get('voice.url'),
            json={
                "timeout": 3600
            }
        ) as response:
            # 使用 async for 循环，更优雅地处理流数据
            i = 0
            async for text in response.aiter_lines():
                if text.startswith('data: '):
                    data_str = text[6:]  # 去掉 "data: " 前缀
                    
                    try:
                        # 解析 JSON 数据
                        data = json.loads(data_str)
                        
                        # 检查是否是错误消息
                        if data.get("type") == "error":
                            print(f"语音服务错误: {data.get('message', 'Unknown error')}")
                            continue
                        
                        # 提取实际的文本内容
                        content = data.get("text", data_str)
                        msg_type = data.get("type", "unknown")
                        
                        # 根据返回的type创建消息
                        if msg_type == "user":
                            message = Message(
                                type=MessageType.user, 
                                content=content, 
                                sessionId=state["context"]["session_id"], 
                                id=generate_id()
                            )
                        elif msg_type == "assistant":
                            message = Message(
                                type=MessageType.assistant, 
                                content=content, 
                                sessionId=state["context"]["session_id"], 
                                id=generate_id()
                            )

                            song_name = re.findall(r"《(.*?)》", content)
                            if song_name:
                                state["context"]["song_name"] = song_name[0]
                                print(f"歌曲名称: {song_name[0]}")
                        else:
                            # 未知类型，跳过
                            print(f"未知消息类型: {msg_type}")
                            continue
                        
                        print(f"收到语音 [{msg_type}]: {content}")
                        writer = get_stream_writer()
                        if writer:
                            writer(message.model_dump_json())
                        
                        i += 1
                        # 读取2条消息后退出
                        if i >= 2:
                            break
                            
                    except json.JSONDecodeError as e:
                        print(f"JSON解析错误: {e}, 原始数据: {data_str}")
                        continue
    
    return state


async def download_music(state: PianoAgentState) -> PianoAgentState:
    download_message = Message(type=MessageType.planning, content="1. 下载歌曲", sessionId=state["context"]["session_id"], id=generate_id())
    state["messages"].append(download_message)
    # time.sleep(1)
    # get_stream_writer() 返回的是一个函数，需要直接调用
    writer = get_stream_writer()
    writer(download_message.model_dump_json())


    music_name = state["context"]["song_name"]
    response = await async_post(config.music_download_url, json_data={"music_name": music_name})
    print(f"下载歌曲: {response}")
    return state

def analyze_music(state: PianoAgentState) -> PianoAgentState:
    analyze_message = Message(type=MessageType.planning, content="2. 分析歌曲", sessionId=state["context"]["session_id"], id=generate_id())
    state["messages"].append(analyze_message)
    time.sleep(1)
    # get_stream_writer() 返回的是一个函数，需要直接调用
    writer = get_stream_writer()
    writer(analyze_message.model_dump_json())
    return state

def parse_params(state: PianoAgentState) -> PianoAgentState:
    parse_params_message = Message(type=MessageType.planning, content="3. 解析参数", sessionId=state["context"]["session_id"], id=generate_id())
    state["messages"].append(parse_params_message)
    time.sleep(1)
    # get_stream_writer() 返回的是一个函数，需要直接调用
    writer = get_stream_writer()
    writer(parse_params_message.model_dump_json())
    return state

def generate_trajectory(state: PianoAgentState) -> PianoAgentState:
    return state

async def perform_music(state: PianoAgentState) -> PianoAgentState:
    """
    异步执行音乐演奏，接收 SSE 流式数据
    同时并行接收键位数据，当演奏结束时自动停止键位数据接收
    """
    parse_params_message = Message(type=MessageType.planning, content="4. 开始演奏", sessionId=state["context"]["session_id"], id=generate_id())
    writer = get_stream_writer()
    writer(parse_params_message.model_dump_json())


    async def stream_performance():
        """接收演奏流数据"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST",
                    config.get('performance.stream_url'),
                    json={"song_name": state["context"]["song_name"]}
                ) as response:
                    print(f"开始演奏: {state['context']['song_name']}")
                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            data = line[6:]  # 去掉 "data: " 前缀
                            # print(f"收到演奏数据: {data}")
                            
                            

                            data = data.strip()
                            print(f"收到演奏数据: {data}")
                            json_data = {}
                            try:
                                json_data = json.loads(data)
                                print(f"收到演奏数据: {json_data}")
                            except json.JSONDecodeError as e:
                                continue

                            message = None
                            if "log" in json_data:
                                    message = Message(
                                        type=MessageType.playing_log, 
                                        content=json_data["log"], 
                                        sessionId=state["context"]["session_id"], 
                                        id=generate_id()
                                    )
                            elif "summary" in json_data:
                                    message = Message(
                                        type=MessageType.playing_summary, 
                                        content=json_data["summary"], 
                                        sessionId=state["context"]["session_id"], 
                                        id=generate_id()
                                    )
                            writer = get_stream_writer()
                            if writer and message:
                                writer(message.model_dump_json())
        except Exception as e:  # noqa: 捕获所有异常以确保流稳定性
            print(f"演奏流异常: {e}")
    
    async def stream_record(stop_event: asyncio.Event):
        """接收键位录音数据，当 stop_event 被设置时停止"""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "GET",
                    config.get('performance.record_url')
                ) as response:
                    async for line in response.aiter_lines():
                        # 检查是否需要停止
                        if stop_event.is_set():
                            print("演奏结束，停止键位录音")
                            break
                        
                        if line.startswith('data: '):
                            data = line[6:]  # 去掉 "data: " 前缀
                            print(f"收到键位: {data}")
                            
                            message = Message(
                                type=MessageType.key_position, 
                                content=data, 
                                sessionId=state["context"]["session_id"], 
                                id=generate_id()
                            )
                            
                            writer = get_stream_writer()
                            if writer:
                                writer(message.model_dump_json())
        except asyncio.CancelledError:
            print("键位录音任务被取消")
            raise
        except Exception as e:  # noqa: 捕获所有异常以确保流稳定性
            print(f"键位录音流异常: {e}")
    
    # 创建停止事件
    stop_event = asyncio.Event()
    
    # 创建录音任务
    record_task = asyncio.create_task(stream_record(stop_event))
    
    try:
        # 执行演奏流（阻塞直到完成）
        await stream_performance()
    finally:
        # 演奏结束，设置停止事件并取消录音任务
        stop_event.set()
        record_task.cancel()
        # 等待录音任务结束或取消
        try:
            await asyncio.wait_for(record_task, timeout=2.0)
        except asyncio.TimeoutError:
            # 如果等待超时，强制取消任务
            record_task.cancel()
            try:
                await record_task
            except asyncio.CancelledError:
                pass
    
    return state



def save_history(state: PianoAgentState) -> PianoAgentState:
    with db_manager.get_session() as session:
        record = PerformanceHistoryDB.create(
            session,
            # 不指定 id，会自动生成
            piece_id="test",
            piece_name=state["context"]["song_name"],
            composer="测试作曲家",
            started_at=datetime.now(),
            status="ended",
            success=True
        )
        print(f"✅ 记录创建成功，自动生成的ID: {record.id}")
    return state


agent_builder = StateGraph(PianoAgentState)

# define nodes
agent_builder.add_node("mock_voice_to_text", mock_voice_to_text)
agent_builder.add_node("voice_to_text", voice_to_text)
agent_builder.add_node("download_music", download_music)
agent_builder.add_node("analyze_music", analyze_music)
agent_builder.add_node("parse_params", parse_params)
agent_builder.add_node("generate_trajectory", generate_trajectory)
agent_builder.add_node("perform_music", perform_music)
agent_builder.add_node("save_history", save_history)

# define edges
# agent_builder.add_edge(START, "voice_to_text")
# agent_builder.add_edge("voice_to_text", "download_music")
agent_builder.add_edge(START, "mock_voice_to_text")
agent_builder.add_edge("mock_voice_to_text", "download_music")
agent_builder.add_edge("download_music", "analyze_music")
agent_builder.add_edge("analyze_music", "parse_params")
agent_builder.add_edge("parse_params", "generate_trajectory")
agent_builder.add_edge("generate_trajectory", "perform_music")
agent_builder.add_edge("perform_music", "save_history")
agent_builder.add_edge("save_history", END)


agent = agent_builder.compile()


