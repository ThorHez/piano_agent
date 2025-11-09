#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI语音服务接口 - 专注于音频设备准备和播放功能
"""
import os
import json
import base64
import time
import wave
import threading
import queue
import tempfile
import requests
import websocket
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import numpy as np
import sounddevice as sd
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    from funasr import AutoModel
    from funasr.utils.postprocess_utils import rich_transcription_postprocess
    FUNASR_AVAILABLE = True
except ImportError:
    FUNASR_AVAILABLE = False

# ==================== 配置参数 ====================

# 语音大模型配置
API_KEY = "3zVld4viwKMPfg8dEUZyTdVd53Ikx8BTee1yIdvUHDrUxHL5No5i6mG8lH2IZIfCJ"  # 或者硬编码 "YOUR_API_KEY"
MODEL_ID = "step-1o-audio"  # 替换为你有权限使用的文本实时模型
WS_URL = f"wss://api.stepfun.com/v1/realtime?model={MODEL_ID}"

# 本地ASR配置
ASR_MODEL_ID = os.getenv("ASR_MODEL_ID", "iic/SenseVoiceSmall")
ASR_DEVICE = os.getenv("ASR_DEVICE", "cpu")
LOCAL_ASR_URL = os.getenv("LOCAL_ASR_URL", "http://127.0.0.1:8000/transcribe")

# 音频配置
SAMPLE_RATE = 48000  # 使用48kHz，与play_piano.py保持一致
OUTPUT_SR = 24000    # 输出采样率
TARGET_SR = 24000    # ASR上传采样率
CHANNELS = 1
CHUNK_MS = 20
VOICE = "alloy"
INSTRUCTIONS = "你是一个会弹钢琴的机器人，你只会回复用户关于弹钢琴曲目的问题，当用户询问你是否会谈某些曲目的时候，你只需要回答：好的，我会为你弹奏。你需要严格遵守上面的指令。"

# 语言映射
LANG_MAP = {
    "auto": "auto",
    "chinese": "zn",
    "zh": "zn",
    "zh-cn": "zn",
    "english": "en",
    "en": "en",
    "yue": "yue",
    "ja": "ja",
    "ko": "ko",
    "nospeech": "nospeech",
}

# ==================== 数据模型 ====================

@dataclass
class TurnBuf:
    user_audio_16k: list = field(default_factory=list)  # list[np.float32]
    ai_pcm_bytes: bytearray = field(default_factory=bytearray)
    asr_text: str = ""
    ai_text: str = ""

class VoiceStreamRequest(BaseModel):
    timeout: Optional[int] = 30
    use_local_asr: Optional[bool] = True
    use_llm: Optional[bool] = True

# ==================== 工具函数 ====================

def float_to_pcm16_bytes(f32: np.ndarray) -> bytes:
    f32 = np.clip(f32, -1.0, 1.0)
    return (f32 * 32767.0).astype(np.int16).tobytes()

def pcm16_bytes_to_float(pcm: bytes) -> np.ndarray:
    return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32767.0

def b64_encode_pcm16_f32(f32: np.ndarray) -> str:
    """把 float32（-1..1）编码为 Base64(PCM16) 字符串"""
    return base64.b64encode(float_to_pcm16_bytes(f32)).decode("ascii")

def b64_decode_pcm(b64: str) -> bytes:
    return base64.b64decode(b64)

def asr_tool_fun_local(audio_path, asr_url=None):
    """
    调用本地 ASR 接口（FastAPI /transcribe），默认 http://127.0.0.1:8000/transcribe
    识别中文；不返回时间戳，只取 text 字段。
    """
    import os
    import requests
    from pathlib import Path

    if asr_url is None:
        asr_url = LOCAL_ASR_URL

    p = Path(audio_path)
    with p.open("rb") as f:
        resp = requests.post(
            asr_url,
            files={"file": (p.name, f, "audio/wav")},
            data={"language": "chinese", "timestamps": "none", "task": "transcribe"},
            timeout=120,
        )
    resp.raise_for_status()
    j = resp.json()
    return str(j.get("text", ""))

def asr_with_funasr(audio_path):
    """
    使用FunASR直接进行语音识别（使用预热好的模型）
    """
    if not FUNASR_AVAILABLE:
        raise RuntimeError("FunASR not available")

    global asr_model
    if 'asr_model' not in globals():
        raise RuntimeError("FunASR model not warmed up")

    try:
        print(f"[ASR] Processing with FunASR: {audio_path}")
        res = asr_model.generate(
            input=audio_path,
            cache={},
            language="zn",
            use_itn=True,
            batch_size_s=60,
        )
        text_raw = res[0].get("text", "")
        text = rich_transcription_postprocess(text_raw)
        print(f"[ASR] FunASR result: {text}")
        return text
    except Exception as e:
        print(f"[ASR] FunASR error: {e}")
        return ""

# ==================== 语音大模型客户端 ====================

class SimpleRealtimeClient:
    """简化的实时语音客户端"""
    def __init__(self, device_index: int = None):
        assert API_KEY, "未设置 API_KEY"
        self.ws = None
        self.ws_thread = None
        self.should_stop = threading.Event()
        self.session_ready = False
        self.last_event_ts = time.time()
        self.round_id = 0

        self.turn = TurnBuf()
        self.turns = []

        self.mic_q: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=200)
        self.play_q: "queue.Queue[bytes]" = queue.Queue(maxsize=200)

        self.stream = None
        self.player_thread = None
        self.mic_thread = None
        self.device_index = device_index

        # 回调函数
        self.response_callback = None
        self.asr_callback = None

    def connect(self):
        headers = [f"Authorization: Bearer {API_KEY}"]
        self.ws = websocket.WebSocketApp(
            WS_URL,
            header=headers,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self.ws_thread = threading.Thread(
            target=lambda: self.ws.run_forever(ping_interval=20, ping_timeout=10),
            daemon=True
        )
        self.ws_thread.start()

    def _on_open(self, ws):
        print("[LLM] WebSocket connected")
        ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "turn_detection": {"type": "server_vad"},
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "instructions": INSTRUCTIONS
            }
        }))

    def _on_message(self, ws, msg):
        data = json.loads(msg)
        t = data.get("type", "")
        self.last_event_ts = time.time()

        if t == "error":
            print("[LLM] Server error:", data)
            return

        if t == "session.updated":
            print("[LLM] Session updated, ready")
            self.session_ready = True

        elif t == "input_audio_buffer.speech_started":
            print("[LLM] Speech started")
            self.turn = TurnBuf()

        elif t == "input_audio_buffer.speech_stopped":
            print("[LLM] Speech stopped, triggering generation")
            self.ws.send(json.dumps({
                "type": "response.create",
                "response": {"modalities": ["text"]}
            }))

            # 保存用户音频并发送给ASR
            file_path = self._save_user_wav()
            if file_path and self.asr_callback:
                try:
                    threading.Thread(target=self.asr_callback, args=(file_path,), daemon=True).start()
                except Exception as e:
                    print(f"[LLM] ASR callback error: {e}")

        elif t == "response.audio.delta":
            # 处理AI音频数据
            b = b64_decode_pcm(data.get("delta", ""))
            self.turn.ai_pcm_bytes.extend(b)
            try:
                self.play_q.put_nowait(b)
            except queue.Full:
                pass
        
        elif t == "response.audio_transcript.delta":
            self.turn.asr_text += data.get("delta", "")

        elif t == "response.text.delta":
            delta = data.get("delta", "")
            self.turn.ai_text += delta
            print(f"[LLM] AI text delta: {delta}")

        elif t == "response.done":
            print(f"[LLM] Response done - User: {self.turn.asr_text}, AI: {self.turn.ai_text}")

            asr_text = self.turn.asr_text.strip()

            # 保存AI音频文件
            self._save_ai_wav()

            if self.response_callback:
                try:
                    self.response_callback({
                        "user_text": self.turn.asr_text,
                        "ai_text": asr_text,
                    })
                except Exception as e:
                    print(f"[LLM] Response callback error: {e}")

            self.round_id += 1
            self.turns.append(self.turn)

    def _on_error(self, ws, error):
        print("[LLM] WebSocket error:", error)

    def _on_close(self, ws, code, msg):
        print("[LLM] WebSocket closed:", code, msg)
        self.should_stop.set()

    def start_audio_chain(self):
        """启动音频采集链路"""
        def cb(indata, frames, time_info, status):
            if status:
                print("[Mic] Status:", status)
            mono = indata[:, 0] if indata.ndim > 1 else indata
            try:
                self.mic_q.put_nowait(mono.copy())
            except queue.Full:
                pass

        blocksize = int(SAMPLE_RATE * CHUNK_MS / 1000)
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=blocksize,
            device=self.device_index,
            callback=cb,
        )
        self.stream.start()
        print(f"[Mic] Audio input started: device#{self.device_index}, {SAMPLE_RATE} Hz")

        self.mic_thread = threading.Thread(target=self._mic_loop, daemon=True)
        self.mic_thread.start()

    def _mic_loop(self):
        step = SAMPLE_RATE // TARGET_SR
        while not self.should_stop.is_set():
            try:
                chunk = self.mic_q.get(timeout=0.5)
            except queue.Empty:
                continue

            down = chunk[::step] if step > 1 else chunk
            self.turn.user_audio_16k.append(down)

            if self.session_ready:
                try:
                    self.ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": b64_encode_pcm16_f32(down)
                    }))
                except Exception as e:
                    print("[LLM] Send audio error:", e)

    def _save_user_wav(self):
        if not self.turn.user_audio_16k:
            return None
        buf = np.concatenate(self.turn.user_audio_16k)
        fname = f"user_round_{self.round_id + 1}.wav"
        self._save_wav_16k(fname, buf)
        print(f"[Save] User audio saved: {fname}")
        return os.path.abspath(fname)

    def _save_ai_wav(self):
        """保存AI生成的音频文件"""
        if not self.turn.ai_pcm_bytes:
            return
        fname = f"ai_round_{self.round_id}.wav"
        with wave.open(fname, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)          # PCM16
            wf.setframerate(OUTPUT_SR)  # 保存为输出采样率
            wf.writeframes(bytes(self.turn.ai_pcm_bytes))
        print(f"[LLM] AI audio saved: {fname}")

    def start_player_thread(self):
        """启动音频播放线程"""
        self.player_thread = threading.Thread(target=self._player_loop, daemon=True)
        self.player_thread.start()

    def _player_loop(self):
        """连续播放队列里的 PCM16 音频，避免卡顿和丢帧"""
        with sd.OutputStream(
            samplerate=OUTPUT_SR,
            channels=1,
            dtype="float32",
            blocksize=1024,   # 可以调整，越小延迟越低
        ) as stream:
            buffer = bytearray()
            while not self.should_stop.is_set():
                try:
                    pcm = self.play_q.get(timeout=0.5)
                    buffer.extend(pcm)
                except queue.Empty:
                    continue

                # 每次写固定帧数，避免卡顿
                frame_size = 1024  # 帧数 (samples)
                bytes_per_frame = 2  # PCM16 = 2字节
                while len(buffer) >= frame_size * bytes_per_frame:
                    chunk = buffer[:frame_size * bytes_per_frame]
                    buffer = buffer[frame_size * bytes_per_frame:]
                    audio = pcm16_bytes_to_float(chunk)
                    stream.write(audio)

    @staticmethod
    def _save_wav_16k(fname: str, f32: np.ndarray):
        pcm16 = float_to_pcm16_bytes(f32.astype(np.float32, copy=False))
        with wave.open(fname, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(OUTPUT_SR)
            wf.writeframes(pcm16)

    def close(self):
        self.should_stop.set()
        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
        except Exception:
            pass
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass

# 音频设备管理
class AudioManager:
    def __init__(self):
        self.device_index = None
        self.is_initialized = False
        self._lock = threading.Lock()

    def initialize_audio_device(self):
        """初始化音频设备"""
        with self._lock:
            if self.is_initialized:
                return True

            try:
                # 获取默认输出设备
                devices = sd.query_devices()
                output_device = None
                default_device = None

                for i, device in enumerate(devices):
                    if device.get('max_output_channels', 0) > 0:
                        if output_device is None:
                            output_device = i
                        # 查找默认设备
                        if device.get('name', '').lower() in ['default', '默认']:
                            default_device = i
                            break

                # 优先使用默认设备
                if default_device is not None:
                    output_device = default_device

                if output_device is None:
                    raise RuntimeError("No audio output device found")

                device_info = devices[output_device]
                self.device_index = output_device

                # 获取设备支持的采样率
                device_sr = device_info.get('default_samplerate', 44100)
                if device_sr == 0:
                    device_sr = 44100  # 如果设备没有默认采样率，使用44100

                print(f"[Audio] Using device {output_device}: {device_info['name']}")
                print(f"[Audio] Device sample rate: {device_sr}")

                # 测试音频设备 - 使用设备支持的采样率
                test_data = np.zeros(1024, dtype=np.float32)
                sd.play(test_data, int(device_sr), device=self.device_index)
                sd.wait()

                self.is_initialized = True
                print(f"[Audio] Audio device initialized successfully")
                return True

            except Exception as e:
                print(f"[Audio] Failed to initialize audio device: {e}")
                # 尝试不指定设备，使用系统默认
                try:
                    print("[Audio] Trying system default device...")
                    test_data = np.zeros(1024, dtype=np.float32)
                    sd.play(test_data, 44100)  # 使用常见的44100Hz
                    sd.wait()
                    self.is_initialized = True
                    self.device_index = None
                    print("[Audio] System default device initialized successfully")
                    return True
                except Exception as e2:
                    print(f"[Audio] System default device also failed: {e2}")
                    return False

    def play_audio_file(self, audio_file_path: str):
        """播放音频文件"""
        try:
            if not self.is_initialized:
                if not self.initialize_audio_device():
                    raise RuntimeError("Failed to initialize audio device")

            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

            print(f"[Audio] Playing audio: {audio_file_path}")

            # 根据文件扩展名选择读取方式
            file_ext = Path(audio_file_path).suffix.lower()

            if file_ext == '.wav':
                with wave.open(audio_file_path, 'rb') as wf:
                    sample_rate = wf.getframerate()
                    frames = wf.readframes(-1)
                    audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0

            elif file_ext == '.mp3':
                if not LIBROSA_AVAILABLE:
                    raise RuntimeError("MP3 playback requires librosa library")
                audio_data, sample_rate = librosa.load(audio_file_path, sr=None, mono=True)

            else:
                raise ValueError(f"Unsupported audio format: {file_ext}")

            # 播放音频 - 使用音频文件原有的采样率，如果指定了设备则使用设备
            if self.device_index is not None:
                sd.play(audio_data, sample_rate, device=self.device_index)
            else:
                sd.play(audio_data, sample_rate)
            sd.wait()
            print(f"[Audio] Audio playback completed")

        except Exception as e:
            print(f"[Audio] Error playing audio: {e}")
            raise

# 全局音频管理器
audio_manager = AudioManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("[Server] Starting voice API server...")

    # 初始化音频设备
    success = audio_manager.initialize_audio_device()
    if success:
        print("[Server] Audio device initialized successfully")
    else:
        print("[Server] Warning: Audio device initialization failed")

    # 预热FunASR模型
    if FUNASR_AVAILABLE:
        print("[Server] Warming up FunASR model...")
        try:
            global asr_model
            asr_model = AutoModel(
                model=ASR_MODEL_ID,
                device=ASR_DEVICE,
                disable_update=True,
            )
            print("[Server] FunASR model warmed up successfully")
        except Exception as e:
            print(f"[Server] Failed to warm up FunASR model: {e}")
    else:
        print("[Server] FunASR not available, skipping model warmup")

    yield  # 应用运行期间

    print("[Server] Shutting down voice API server...")

app = FastAPI(title="Voice API Server", lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Voice API Server", "status": "running"}

@app.post("/voice/stream")
async def voice_stream(request: VoiceStreamRequest):
    """
    语音结果接口 - SSE模式

    单一接口启动完整语音流程，等待处理后分两次yield返回：
    1. 第一次yield: type="user", ASR识别的完整文本
    2. 第二次yield: type="assistant", AI生成的完整文本

    注意：不是流式输出文字，而是等待完整语音处理完成后，
          分别返回user和assistant的完整文本结果。

    使用方式:
    curl -X POST "http://localhost:9331/voice/stream" \
         -H "Content-Type: application/json" \
         -d '{"timeout": 30}' \
         -N
    """

    async def generate_response():
        session_id = f"session_{int(time.time())}"
        print(f"[{session_id}] Voice stream started")

        try:
            # 1. 准备音频设备并播放准备好的音频文件（保持原有逻辑）
            print(f"[{session_id}] Preparing audio system...")

            # 确保音频设备已初始化
            if not audio_manager.is_initialized:
                audio_manager.initialize_audio_device()

            # 播放准备好的音频文件（这里可以指定具体的音频文件）
            startup_audio = "startup.mp3"  # 可以根据需要修改
            if os.path.exists(startup_audio):
                audio_manager.play_audio_file(startup_audio)
            else:
                print(f"[{session_id}] Startup audio file not found: {startup_audio}")

            # 2. 语音处理流程
            print(f"[{session_id}] Starting voice processing...")

            # 用于存储结果的容器
            result_container = {"asr_text": "", "ai_text": "", "completed": False}
            processing_complete = asyncio.Event()

            # ASR回调函数
            def asr_callback(audio_path: str):
                """ASR识别回调"""
                try:
                    print(f"[{session_id}] Processing ASR for: {audio_path}")

                    # 尝试使用本地ASR服务
                    if request.use_local_asr:
                        try:
                            # 优先尝试本地FunASR
                            if FUNASR_AVAILABLE:
                                result_container["asr_text"] = asr_with_funasr(audio_path)
                                print(f"[{session_id}] FunASR result: {result_container['asr_text']}")
                            else:
                                # 回退到远程ASR服务
                                result_container["asr_text"] = asr_tool_fun_local(audio_path)
                                print(f"[{session_id}] Local ASR result: {result_container['asr_text']}")
                        except Exception as e:
                            print(f"[{session_id}] Local ASR failed: {e}")

                    # ASR完成后检查LLM是否也完成了
                    if result_container["ai_text"]:
                        result_container["completed"] = True
                        processing_complete.set()
                        print(f"[{session_id}] ASR completed and LLM already completed, ready to yield results")
                    else:
                        print(f"[{session_id}] ASR completed but waiting for LLM result...")

                    # 清理临时音频文件
                    try:
                        os.unlink(audio_path)
                    except Exception:
                        pass

                except Exception as e:
                    print(f"[{session_id}] ASR callback error: {e}")

            # LLM响应回调函数
            def response_callback(result: dict):
                """LLM响应回调"""
                try:
                    result_container["ai_text"] = result.get("ai_text", "")
                    print(f"[{session_id}] LLM response received: AI={result_container['ai_text']}")

                    # 只有当ASR也完成时才标记为完成
                    if result_container["asr_text"]:
                        result_container["completed"] = True
                        processing_complete.set()
                        print(f"[{session_id}] Both ASR and LLM completed, ready to yield results")
                    else:
                        print(f"[{session_id}] LLM completed but waiting for ASR result...")
                except Exception as e:
                    print(f"[{session_id}] Response callback error: {e}")

            # 3. 启动语音大模型客户端（如果启用）
            realtime_client = None
            print(f"[{session_id}] LLM config - use_llm: {request.use_llm}, API_KEY set: {bool(API_KEY)}")

            if request.use_llm and API_KEY:
                try:
                    print(f"[{session_id}] Initializing LLM client...")
                    realtime_client = SimpleRealtimeClient(device_index=audio_manager.device_index)
                    realtime_client.asr_callback = asr_callback
                    realtime_client.response_callback = response_callback
                    realtime_client.connect()
                    print(f"[{session_id}] LLM client connecting...")

                    # 等待会话准备就绪
                    max_wait = 10  # 最多等待10秒
                    wait_count = 0
                    while not realtime_client.session_ready and wait_count < max_wait:
                        await asyncio.sleep(0.5)
                        wait_count += 0.5
                        print(f"[{session_id}] Waiting for session ready... {wait_count}s")

                    if realtime_client.session_ready:
                        realtime_client.start_audio_chain()
                        realtime_client.start_player_thread()
                        print(f"[{session_id}] LLM client started successfully - listening for speech...")
                    else:
                        print(f"[{session_id}] LLM client failed to initialize within timeout")
                        realtime_client.close()
                        realtime_client = None

                except Exception as e:
                    print(f"[{session_id}] Failed to start LLM client: {e}")
                    import traceback
                    traceback.print_exc()
                    if realtime_client:
                        realtime_client.close()
                        realtime_client = None
            else:
                print(f"[{session_id}] LLM disabled or API_KEY not set, skipping LLM initialization")

            # 4. 等待语音处理完成或超时
            try:
                if realtime_client:
                    # 使用大模型时的处理
                    timeout = request.timeout if request.timeout > 0 else 30
                    print(f"[{session_id}] Waiting for voice processing (timeout: {timeout}s)...")

                    # 等待处理完成或超时
                    try:
                        await asyncio.wait_for(processing_complete.wait(), timeout=timeout)
                        print(f"[{session_id}] Processing completed!")
                    except asyncio.TimeoutError:
                        print(f"[{session_id}] Voice processing timeout")

                    # 检查是否有结果
                    if result_container["completed"]:
                        # 第一次yield：返回FunASR识别的用户语音结果
                        user_result = {
                            "type": "user",
                            "text": result_container["asr_text"],
                            "timestamp": time.time()
                        }
                        yield f"data: {json.dumps(user_result, ensure_ascii=False)}\n\n"
                        print(f"[{session_id}] Yielded user result (FunASR): {user_result['text']}")

                        # 第二次yield：返回AI结果
                        assistant_result = {
                            "type": "assistant",
                            "text": result_container["ai_text"],
                            "timestamp": time.time()
                        }
                        yield f"data: {json.dumps(assistant_result, ensure_ascii=False)}\n\n"
                        print(f"[{session_id}] Yielded assistant result (LLM): {assistant_result['text']}")
                    else:
                        # 没有结果，返回错误
                        error_result = {
                            "type": "error",
                            "message": "语音处理超时或未检测到有效语音输入",
                            "timestamp": time.time()
                        }
                        yield f"data: {json.dumps(error_result, ensure_ascii=False)}\n\n"
                        print(f"[{session_id}] Yielded timeout error")
                else:
                    # 回退到模拟模式（如果没有启用LLM或初始化失败）
                    print(f"[{session_id}] Falling back to demo mode")

                    # 第一次yield：模拟用户语音识别结果
                    user_result = {
                        "type": "user",
                        "text": "这是演示模式的用户语音识别结果（请检查LLM配置）",
                        "timestamp": time.time()
                    }
                    yield f"data: {json.dumps(user_result, ensure_ascii=False)}\n\n"
                    print(f"[{session_id}] Demo mode - yielded user result")

                    # 模拟一些处理时间
                    await asyncio.sleep(1)

                    # 第二次yield：模拟AI生成的文本
                    assistant_result = {
                        "type": "assistant",
                        "text": "这是演示模式的AI回复结果（请检查LLM配置）",
                        "timestamp": time.time()
                    }
                    yield f"data: {json.dumps(assistant_result, ensure_ascii=False)}\n\n"
                    print(f"[{session_id}] Demo mode - yielded assistant result")

            except Exception as e:
                print(f"[{session_id}] Processing error: {e}")
                error_result = {
                    "type": "error",
                    "message": f"语音处理失败: {str(e)}",
                    "timestamp": time.time()
                }
                yield f"data: {json.dumps(error_result, ensure_ascii=False)}\n\n"

            finally:
                # 清理资源
                if realtime_client:
                    realtime_client.close()
                    print(f"[{session_id}] LLM client closed")

        except Exception as e:
            print(f"[{session_id}] Stream error: {e}")
            error_result = {
                "type": "error",
                "message": f"语音流处理失败: {str(e)}",
                "timestamp": time.time()
            }
            yield f"data: {json.dumps(error_result, ensure_ascii=False)}\n\n"

        print(f"[{session_id}] Voice stream completed")

    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )

@app.post("/audio/play")
async def play_audio(audio_file_path: str):
    """
    播放指定音频文件的接口

    Args:
        audio_file_path: 要播放的音频文件路径

    Returns:
        播放结果
    """
    try:
        audio_manager.play_audio_file(audio_file_path)
        return {"status": "success", "message": f"Audio played: {audio_file_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audio/devices")
async def list_audio_devices():
    """
    列出可用的音频输出设备

    Returns:
        音频设备列表
    """
    try:
        devices = sd.query_devices()
        output_devices = []

        for i, device in enumerate(devices):
            if device.get('max_output_channels', 0) > 0:
                output_devices.append({
                    "id": i,
                    "name": device.get('name', f'Device {i}'),
                    "channels": device.get('max_output_channels', 0),
                    "sample_rate": device.get('default_samplerate', 0)
                })

        return {"devices": output_devices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("voice_api_server_v2:app", host="0.0.0.0", port=9331, reload=False)