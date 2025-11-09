"""
测试异步HTTP接口调用工具
演示如何使用 src.utils 中的异步HTTP函数
"""
import asyncio
from src.utils import (
    async_get,
    async_post,
    async_put,
    async_delete,
    async_stream_sse,
    async_download_file
)


async def test_basic_requests():
    """测试基本HTTP请求"""
    print("=" * 80)
    print("测试基本HTTP请求")
    print("=" * 80)
    
    # GET请求示例
    print("\n1. GET请求:")
    result = await async_get("https://httpbin.org/get", params={"test": "value"})
    print(f"   状态码: {result['status_code']}")
    print(f"   成功: {result['success']}")
    print(f"   响应: {result['body']}")
    
    # POST请求示例
    print("\n2. POST请求:")
    result = await async_post(
        "https://httpbin.org/post",
        json_data={"name": "John", "age": 30}
    )
    print(f"   状态码: {result['status_code']}")
    print(f"   成功: {result['success']}")
    
    # PUT请求示例
    print("\n3. PUT请求:")
    result = await async_put(
        "https://httpbin.org/put",
        json_data={"id": 1, "name": "Updated"}
    )
    print(f"   状态码: {result['status_code']}")
    print(f"   成功: {result['success']}")
    
    # DELETE请求示例
    print("\n4. DELETE请求:")
    result = await async_delete("https://httpbin.org/delete")
    print(f"   状态码: {result['status_code']}")
    print(f"   成功: {result['success']}")


async def test_stream_sse():
    """测试SSE流式请求"""
    print("\n" + "=" * 80)
    print("测试SSE流式请求")
    print("=" * 80)
    
    # 测试本地SSE接口
    url = "http://localhost:8123/record"
    
    try:
        print(f"\n连接到: {url}")
        print("接收流式数据（按 Ctrl+C 停止）:\n")
        
        count = 0
        async for data in async_stream_sse(url):
            count += 1
            print(f"[{count}] {data}")
            
            # 测试用：只接收10条消息
            if count >= 10:
                print("\n已接收10条消息，停止测试")
                break
                
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")


async def test_performance_stream():
    """测试演奏接口的SSE流"""
    print("\n" + "=" * 80)
    print("测试演奏接口SSE流")
    print("=" * 80)
    
    from src.config import config
    
    url = config.get('performance.stream_url')
    print(f"\n连接到: {url}")
    
    try:
        async for data in async_stream_sse(
            url,
            method="POST",
            json_data={"song_name": "青花瓷"}
        ):
            print(f"收到演奏数据: {data}")
            
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")


async def test_download_file():
    """测试文件下载"""
    print("\n" + "=" * 80)
    print("测试文件下载")
    print("=" * 80)
    
    def progress(downloaded, total):
        """下载进度回调"""
        percent = (downloaded / total * 100) if total > 0 else 0
        print(f"\r下载进度: {downloaded}/{total} 字节 ({percent:.1f}%)", end="")
    
    # 下载一个小文件测试
    url = "https://httpbin.org/image/png"
    save_path = "/tmp/test_image.png"
    
    print(f"\n下载文件:")
    print(f"  URL: {url}")
    print(f"  保存到: {save_path}")
    
    success = await async_download_file(url, save_path, progress_callback=progress)
    
    if success:
        print(f"\n✅ 下载成功: {save_path}")
    else:
        print("\n❌ 下载失败")


async def test_parallel_requests():
    """测试并行请求"""
    print("\n" + "=" * 80)
    print("测试并行HTTP请求")
    print("=" * 80)
    
    # 创建多个并行请求
    tasks = [
        async_get("https://httpbin.org/delay/1"),
        async_get("https://httpbin.org/delay/1"),
        async_get("https://httpbin.org/delay/1"),
    ]
    
    print("\n发起3个并行请求（每个延迟1秒）...")
    import time
    start = time.time()
    
    # 并行执行所有请求
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    print(f"✅ 完成！耗时: {elapsed:.2f}秒")
    print(f"   如果是串行执行应该需要3秒，并行只需要1秒左右")
    print(f"   成功请求数: {sum(1 for r in results if r['success'])}/{len(results)}")


async def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("🚀 异步HTTP工具测试")
    print("=" * 80)
    
    # 选择要运行的测试
    print("\n请选择测试:")
    print("  1. 基本HTTP请求 (GET/POST/PUT/DELETE)")
    print("  2. SSE流式请求 (record接口)")
    print("  3. 演奏接口SSE流")
    print("  4. 文件下载")
    print("  5. 并行请求")
    print("  6. 运行所有测试")
    
    choice = input("\n请输入选项 (1-6): ").strip()
    
    if choice == "1":
        await test_basic_requests()
    elif choice == "2":
        await test_stream_sse()
    elif choice == "3":
        await test_performance_stream()
    elif choice == "4":
        await test_download_file()
    elif choice == "5":
        await test_parallel_requests()
    elif choice == "6":
        await test_basic_requests()
        # await test_stream_sse()  # 需要手动停止
        await test_download_file()
        await test_parallel_requests()
    else:
        print("❌ 无效选项")


if __name__ == "__main__":
    asyncio.run(main())

