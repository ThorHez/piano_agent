"""
测试 SSE 流式返回
"""
import requests
import json

print("🚀 测试 SSE 流式返回")
print("=" * 60)

url = "http://localhost:8000/chat"

try:
    # 使用 stream=True 接收流式响应
    response = requests.post(url, stream=True)
    
    print(f"📡 状态码: {response.status_code}")
    print(f"📋 Content-Type: {response.headers.get('content-type')}")
    print("\n📩 开始接收消息:\n")
    
    # 逐行读取 SSE 数据
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            
            # SSE 格式: data: {...}
            if line_str.startswith('data: '):
                data_json = line_str[6:]  # 移除 "data: " 前缀
                try:
                    message = json.loads(data_json)
                    print(f"✅ [{message.get('type', 'unknown')}] {message.get('content', '')}")
                    print(f"   时间: {message.get('timestamp', 'N/A')}")
                    print()
                except json.JSONDecodeError as e:
                    print(f"❌ JSON 解析错误: {e}")
                    print(f"   原始数据: {data_json}")
                    print()

except requests.exceptions.ConnectionError:
    print("❌ 连接失败！请确保服务器正在运行:")
    print("   python run.py")
except Exception as e:
    print(f"❌ 错误: {e}")

print("=" * 60)
print("✅ 测试完成")

