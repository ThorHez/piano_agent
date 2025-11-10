"""
数据模型定义
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


# Enums
class Role(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class PerformanceStatus(str, Enum):
    idle = "idle"
    preparing = "preparing"
    playing = "playing"
    paused = "paused"
    ended = "ended"
    error = "error"


class ControlAction(str, Enum):
    pause = "pause"
    resume = "resume"
    stop = "stop"


class MessageType(str, Enum):
    assistant = "assistant"
    user = "user"
    planning = "planning"
    playing_log = "playing_log"
    key_position = "key_position"
    playing_summary = "playing_summary"
    end = "end"


# Schemas
class Message(BaseModel):
    type: str
    id: str
    sessionId: str
    timestamp: datetime = datetime.now()
    content: str
    status: Optional[int] = None


class DownloadRequest(BaseModel):
    music_id: int
    music_name: str


class AnalyzeRequest(BaseModel):
    music_id: int


class AnalyzeResponse(BaseModel):
    file_paths: List[str]


class ChatMessage(BaseModel):
    id: str
    sessionId: str
    role: Role
    content: str
    timestamp: datetime


class ControlRequest(BaseModel):
    action: ControlAction


class HistoryItem(BaseModel):
    id: str
    pieceId: str
    pieceName: str
    startedAt: datetime
    durationSec: int
    status: PerformanceStatus
    success: bool


class StatusEvent(BaseModel):
    status: str
    message: Optional[str] = None


