from src.graph.agent import agent
from src.utils import generate_session_id
import json


# stream_mode="custom" 时，chunk 是通过 writer() 发送的自定义数据（JSON字符串）
for chunk in agent.stream({"messages": [], "context": {"session_id": generate_session_id()}}, stream_mode="custom"):
    # chunk 是 JSON 字符串，需要解析
    message_data = json.loads(chunk)
    print(f"📩 收到消息: {message_data['content']}")