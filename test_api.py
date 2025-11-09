"""
API测试脚本
使用 httpx 或 requests 测试API端点
"""
import asyncio
import json


async def test_api():
    """测试API端点"""
    try:
        import httpx
    except ImportError:
        print("请先安装 httpx: pip install httpx")
        return
    
    base_url = "http://localhost:8000"
    
    print("=" * 60)
    print("🧪 测试 Termitech Auto-Piano API")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. 健康检查
        print("\n✅ 1. 测试健康检查...")
        response = await client.get(f"{base_url}/health")
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
        
        # 2. 获取曲库列表
        print("\n✅ 2. 测试获取曲库列表...")
        response = await client.get(f"{base_url}/scores")
        print(f"   状态码: {response.status_code}")
        scores = response.json()
        print(f"   曲目数量: {len(scores)}")
        if scores:
            print(f"   第一首曲目: {scores[0]['name']}")
        
        # 3. 搜索曲目
        print("\n✅ 3. 测试搜索曲目...")
        response = await client.get(f"{base_url}/scores?q=贝多芬")
        print(f"   状态码: {response.status_code}")
        print(f"   搜索结果: {len(response.json())} 首")
        
        # 4. 创建演奏会话
        print("\n✅ 4. 测试创建演奏会话...")
        response = await client.post(
            f"{base_url}/performances",
            json={
                "pieceId": "piece_1",
                "tempo": 120,
                "hands": "both"
            }
        )
        print(f"   状态码: {response.status_code}")
        performance = response.json()
        performance_id = performance["id"]
        print(f"   演奏ID: {performance_id}")
        print(f"   SSE URL: {performance['sseUrl']}")
        
        # 5. 获取演奏状态
        print("\n✅ 5. 测试获取演奏状态...")
        response = await client.get(f"{base_url}/performances/{performance_id}")
        print(f"   状态码: {response.status_code}")
        print(f"   演奏状态: {response.json()['status']}")
        
        # 6. 测试下载音乐
        print("\n✅ 6. 测试下载音乐...")
        response = await client.post(
            f"{base_url}/download/music",
            json={
                "music_id": 1,
                "music_name": "测试曲目"
            }
        )
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
        
        # 7. 测试分析音乐
        print("\n✅ 7. 测试分析音乐...")
        response = await client.post(
            f"{base_url}/analyze_music",
            json={"music_id": 1}
        )
        print(f"   状态码: {response.status_code}")
        print(f"   乐谱路径: {response.json()}")
        
        # 8. 获取历史记录
        print("\n✅ 8. 测试获取历史记录...")
        response = await client.get(f"{base_url}/history?limit=10")
        print(f"   状态码: {response.status_code}")
        print(f"   历史记录数: {len(response.json())}")
        
    print("\n" + "=" * 60)
    print("✨ 测试完成！")
    print("=" * 60)


def test_sse():
    """测试SSE流"""
    try:
        import httpx
    except ImportError:
        print("请先安装 httpx: pip install httpx")
        return
    
    print("\n🌊 测试SSE流...")
    print("提示: 按 Ctrl+C 停止测试\n")
    
    import sys
    
    base_url = "http://localhost:8000"
    
    # 首先创建一个演奏会话
    with httpx.Client() as client:
        response = client.post(
            f"{base_url}/performances",
            json={"pieceId": "piece_1", "tempo": 120}
        )
        performance_id = response.json()["id"]
        print(f"创建演奏会话: {performance_id}\n")
    
    # 连接到SSE流
    try:
        with httpx.stream("GET", f"{base_url}/performances/{performance_id}/stream") as response:
            for line in response.iter_lines():
                if line:
                    print(line)
                    sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n\n测试中断")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "sse":
        test_sse()
    else:
        asyncio.run(test_api())
        
        print("\n💡 提示:")
        print("   - 运行 'python test_api.py sse' 测试SSE流")
        print("   - 访问 http://localhost:8000/docs 查看交互式文档")

