# SSE 流式返回修复指南

## 🔍 问题原因

您的代码之前**无法分步返回**的原因：

### 1. **SSE 格式不正确**
```python
# ❌ 错误：直接返回 JSON
yield first_message.model_dump_json()

# ✅ 正确：使用 SSE 格式
yield f"data: {first_message.model_dump_json()}\n\n"
```

### 2. **缺少异步控制**
```python
# ❌ 错误：没有让出控制权，数据可能被缓冲
for chunk in agent.stream(...):
    yield chunk

# ✅ 正确：添加 await asyncio.sleep(0)
for chunk in agent.stream(...):
    yield f"data: {chunk}\n\n"
    await asyncio.sleep(0)  # 让出控制权，立即发送
```

### 3. **参数传递错误**
```python
# ❌ 错误：参数没有正确传递
async def generate_chat_voice_stream(sessionId: str = Query(...)):
    ...

# ✅ 正确：直接传递参数
async def generate_chat_voice_stream(sessionId: str):
    ...
```

## 📝 关键修改

### `src/api/chat.py` 修改

```python
async def generate_chat_voice_stream(sessionId: str):
    """生成语音转文字流"""
    # 第一条消息
    first_message = Message(
        type="assistant",
        id=generate_id(),
        sessionId=sessionId,
        timestamp=get_current_timestamp(),
        content="请问您想听什么曲子？",
        status=200
    )
    # 🔑 关键1: 使用 SSE 格式 "data: ...\n\n"
    yield f"data: {first_message.model_dump_json()}\n\n"
    # 🔑 关键2: 让出控制权
    await asyncio.sleep(0)

    # 流式返回 agent 的执行结果
    for chunk in agent.stream({"messages": [], "context": {"session_id": sessionId}}, stream_mode="custom"):
        # 🔑 关键3: 每条消息都用 SSE 格式并立即发送
        yield f"data: {chunk}\n\n"
        await asyncio.sleep(0)
```

### `run.py` 修改

```python
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
```

## 🧪 测试方法

### 方法 1: 使用 curl（推荐）

```bash
curl -N -X POST http://localhost:8000/chat
```

**预期输出**（逐步返回）：
```
data: {"type":"assistant","id":"...","sessionId":"...","timestamp":"...","content":"请问您想听什么曲子？","status":200}

data: {"type":"planning","id":"...","sessionId":"...","timestamp":"...","content":"1. 下载歌曲","status":null}

data: {"type":"planning","id":"...","sessionId":"...","timestamp":"...","content":"2. 分析歌曲","status":null}

data: {"type":"planning","id":"...","sessionId":"...","timestamp":"...","content":"3. 解析参数","status":null}
```

### 方法 2: 使用 Python 脚本

```bash
python test_sse.py
```

### 方法 3: 使用浏览器 EventSource

```javascript
const eventSource = new EventSource('http://localhost:8000/chat');

eventSource.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('收到消息:', message.content);
};
```

## 📊 SSE 格式说明

### SSE (Server-Sent Events) 标准格式

```
data: {JSON 数据}\n\n
```

- 每条消息以 `data: ` 开头
- 消息内容是 JSON 字符串
- 每条消息以 `\n\n` (两个换行符) 结尾

### 示例

```
data: {"type":"assistant","content":"Hello"}\n\n
data: {"type":"planning","content":"Step 1"}\n\n
data: {"type":"planning","content":"Step 2"}\n\n
```

## ⚠️ 常见问题

### 1. 消息还是一起返回？

**检查清单：**
- [ ] 确认使用了 `yield f"data: {content}\n\n"` 格式
- [ ] 确认添加了 `await asyncio.sleep(0)`
- [ ] 确认客户端使用了 `stream=True` 或 `-N` 参数
- [ ] 确认 Uvicorn 配置了合适的超时参数

### 2. 连接超时？

**解决方案：**
- 增加 `timeout_keep_alive` 参数
- 在长时间运行的任务中定期发送心跳消息

### 3. 浏览器中看不到效果？

**解决方案：**
- 使用 EventSource API，不要用 fetch
- 检查 CORS 配置
- 打开浏览器开发者工具查看 Network 标签

## 🎯 性能优化建议

### 1. 添加心跳
```python
async def generate_chat_voice_stream(sessionId: str):
    # 定期发送心跳，防止连接超时
    async def heartbeat():
        while True:
            await asyncio.sleep(30)
            yield f": heartbeat\n\n"
```

### 2. 错误处理
```python
async def generate_chat_voice_stream(sessionId: str):
    try:
        for chunk in agent.stream(...):
            yield f"data: {chunk}\n\n"
            await asyncio.sleep(0)
    except Exception as e:
        error_msg = {"type": "error", "content": str(e)}
        yield f"data: {json.dumps(error_msg)}\n\n"
```

### 3. 结束标记
```python
async def generate_chat_voice_stream(sessionId: str):
    # ... 发送所有消息 ...
    
    # 发送结束标记
    yield f"data: {json.dumps({'type': 'done', 'content': '完成'})}\n\n"
```

## 📚 参考资料

- [MDN: Server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [FastAPI: StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [sse-starlette](https://github.com/sysid/sse-starlette)

