"""
测试录音流式接口
用于接收 /record 端点的 SSE 流式输出
"""
import requests
import json
import time
from datetime import datetime


def test_record_stream_simple():
    """
    简单方式：使用 requests 库接收流式数据
    """
    print("🎹 开始接收MIDI录音流式数据...\n")
    
    # 配置接口地址
    url = "http://localhost:8123/record"
    
    try:
        # 发起流式请求
        with requests.get(url, stream=True, timeout=60) as response:
            if response.status_code != 200:
                print(f"❌ 请求失败: {response.status_code}")
                print(f"响应内容: {response.text}")
                return
            
            print("✅ 连接成功，开始接收数据...\n")
            print("-" * 80)
            
            # 逐行读取流式数据
            for line in response.iter_lines():
                if line:
                    # 解码字节流
                    line_str = line.decode('utf-8')
                    
                    # SSE 格式：data: {...}
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # 去掉 "data: " 前缀
                        
                        try:
                            # 解析 JSON 数据
                            data = json.loads(data_str)
                            
                            # 格式化输出
                            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            print(f"[{timestamp}] 收到消息:")
                            print(json.dumps(data, indent=2, ensure_ascii=False))
                            print("-" * 80)
                            
                        except json.JSONDecodeError as e:
                            print(f"⚠️  JSON解析错误: {e}")
                            print(f"原始数据: {data_str}")
                    
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败: 无法连接到服务器")
        print("请确保服务器正在运行: python src/record/record_server.py")
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，停止接收")
    except Exception as e:
        print(f"❌ 发生错误: {e}")


def test_record_stream_with_sseclient():
    """
    使用 sseclient-py 库接收 SSE 数据（需要安装：pip install sseclient-py）
    """
    try:
        import sseclient
    except ImportError:
        print("❌ 未安装 sseclient-py 库")
        print("请运行: pip install sseclient-py")
        return
    
    print("🎹 使用 SSE 客户端接收MIDI录音流式数据...\n")
    
    url = "http://localhost:8123/record"
    
    try:
        # 创建 SSE 客户端
        response = requests.get(url, stream=True, timeout=60)
        client = sseclient.SSEClient(response)
        
        print("✅ 连接成功，开始接收数据...\n")
        print("-" * 80)
        
        # 接收事件流
        for event in client.events():
            try:
                # 解析 JSON 数据
                data = json.loads(event.data)
                
                # 格式化输出
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                print(f"[{timestamp}] 收到MIDI事件:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                print("-" * 80)
                
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON解析错误: {e}")
                print(f"原始数据: {event.data}")
                
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败: 无法连接到服务器")
        print("请确保服务器正在运行: python src/record/record_server.py")
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，停止接收")
    except Exception as e:
        print(f"❌ 发生错误: {e}")


def test_record_stream_with_statistics():
    """
    带统计信息的版本：统计接收到的消息数量和类型
    """
    print("🎹 开始接收MIDI录音流式数据（带统计）...\n")
    
    url = "http://localhost:8123/record"
    
    stats = {
        'total_messages': 0,
        'note_on': 0,
        'note_off': 0,
        'control_change': 0,
        'other': 0,
        'start_time': time.time()
    }
    
    try:
        with requests.get(url, stream=True, timeout=60) as response:
            if response.status_code != 200:
                print(f"❌ 请求失败: {response.status_code}")
                print(f"响应内容: {response.text}")
                return
            
            print("✅ 连接成功，开始接收数据...\n")
            print("-" * 80)
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        
                        try:
                            data = json.loads(data_str)
                            stats['total_messages'] += 1
                            
                            # 统计消息类型
                            msg_type = data.get('type', 'unknown')
                            if msg_type == 'note_on':
                                stats['note_on'] += 1
                            elif msg_type == 'note_off':
                                stats['note_off'] += 1
                            elif msg_type == 'control_change':
                                stats['control_change'] += 1
                            else:
                                stats['other'] += 1
                            
                            # 显示消息
                            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            print(f"[{timestamp}] {msg_type}: {data}")
                            
                            # 每10条消息显示一次统计
                            if stats['total_messages'] % 10 == 0:
                                elapsed = time.time() - stats['start_time']
                                print(f"\n📊 统计 [运行时间: {elapsed:.1f}秒]:")
                                print(f"   总消息数: {stats['total_messages']}")
                                print(f"   Note On: {stats['note_on']}")
                                print(f"   Note Off: {stats['note_off']}")
                                print(f"   Control Change: {stats['control_change']}")
                                print(f"   其他: {stats['other']}")
                                print("-" * 80)
                            
                        except json.JSONDecodeError as e:
                            print(f"⚠️  JSON解析错误: {e}")
                    
    except KeyboardInterrupt:
        elapsed = time.time() - stats['start_time']
        print("\n\n" + "=" * 80)
        print("📊 最终统计:")
        print(f"   运行时间: {elapsed:.1f}秒")
        print(f"   总消息数: {stats['total_messages']}")
        print(f"   Note On: {stats['note_on']}")
        print(f"   Note Off: {stats['note_off']}")
        print(f"   Control Change: {stats['control_change']}")
        print(f"   其他: {stats['other']}")
        if elapsed > 0:
            print(f"   平均速率: {stats['total_messages']/elapsed:.1f} 消息/秒")
        print("=" * 80)
        print("\n👋 用户中断，停止接收")
    except Exception as e:
        print(f"❌ 发生错误: {e}")


if __name__ == "__main__":
    import sys
    
    print("=" * 80)
    print("🎹 MIDI 录音流式接口测试工具")
    print("=" * 80)
    print("\n选择测试模式:")
    print("  1. 简单模式 (使用 requests)")
    print("  2. SSE 客户端模式 (需要 sseclient-py)")
    print("  3. 统计模式 (显示消息统计)")
    print("\n按 Ctrl+C 停止接收\n")
    
    # 如果有命令行参数，使用参数选择模式
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("请选择模式 (1/2/3，默认为1): ").strip() or "1"
    
    print()
    
    if choice == "1":
        test_record_stream_simple()
    elif choice == "2":
        test_record_stream_with_sseclient()
    elif choice == "3":
        test_record_stream_with_statistics()
    else:
        print("❌ 无效的选择")
        sys.exit(1)

