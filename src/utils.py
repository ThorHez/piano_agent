"""
工具函数
"""
import uuid
import os
from datetime import datetime
try:
    from jose import JWTError, jwt
except ImportError:
    # 如果jose未安装，提供fallback
    JWTError = Exception
    jwt = None
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


from typing import Optional, List, Tuple, Dict, Any, AsyncIterator
import subprocess
import sys
from pathlib import Path
import httpx

# JWT配置 - 可以从config读取
def get_jwt_config():
    """获取JWT配置"""
    try:
        from src.config import config
        return config.auth_secret_key, config.auth_algorithm
    except ImportError:
        return "your-secret-key-here-change-in-production", "HS256"

SECRET_KEY, ALGORITHM = get_jwt_config()

security = HTTPBearer()


def generate_id() -> str:
    """生成唯一ID"""
    return str(uuid.uuid4())


def generate_session_id() -> str:
    """生成会话ID"""
    return f"session_{uuid.uuid4().hex[:16]}"


def get_current_timestamp() -> datetime:
    """获取当前时间戳"""
    return datetime.now()


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    验证JWT Token
    如果配置中关闭了认证，则跳过验证
    """
    # 检查是否启用认证
    try:
        from src.config import config
        if not config.auth_enabled:
            # 认证已关闭，返回空字典
            return {}
    except ImportError:
        pass  # 配置模块不可用，继续正常验证流程
    
    if jwt is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="JWT authentication not available"
        )
    
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def create_access_token(data: dict) -> str:
    """
    创建JWT Token
    """
    if jwt is None:
        raise RuntimeError("JWT library not available")
    to_encode = data.copy()
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def upload_folder_to_remote_linux(local_dir: str, remote_dir: str, host: str, user: str, password: str, keep_folder_name: bool = True):
    """
    将本地文件夹上传到远程Linux服务器
    
    参数:
        local_dir: 本地文件夹路径
        remote_dir: 远程目标父目录路径
        host: 远程主机地址
        user: SSH用户名
        password: SSH密码
        keep_folder_name: 是否在远程保留文件夹名称（默认True）
    
    示例:
        本地: /Users/xxx/my_folder/file1.txt
        
        keep_folder_name=True:  远程: /home/ubuntu/target/my_folder/file1.txt
        keep_folder_name=False: 远程: /home/ubuntu/target/file1.txt
    """
    from fabric import Connection
    
    # 标准化路径
    local_dir = os.path.abspath(local_dir)
    remote_dir = remote_dir.rstrip('/')  # 移除末尾的斜杠
    
    # 获取本地文件夹名称
    folder_name = os.path.basename(local_dir)
    
    # 根据参数决定最终的远程目录
    if keep_folder_name:
        final_remote_dir = f"{remote_dir}/{folder_name}"
        print(f"📤 开始上传文件夹: {local_dir} → {final_remote_dir}")
    else:
        final_remote_dir = remote_dir
        print(f"📤 开始上传文件夹内容: {local_dir} → {final_remote_dir}")
    
    c = Connection(host=host, user=user, connect_kwargs={"password": password})
    
    try:
        # 首先确保目标目录存在
        print(f"📁 创建远程目录: {final_remote_dir}")
        c.run(f"mkdir -p {final_remote_dir}", hide=True)
        
        # 遍历本地目录
        file_count = 0
        for root, _dirs, files in os.walk(local_dir):
            # 计算相对路径
            rel_path = os.path.relpath(root, local_dir)
            
            # 构建远程路径（处理 . 的情况）
            if rel_path == '.':
                remote_current_dir = final_remote_dir
            else:
                remote_current_dir = os.path.join(final_remote_dir, rel_path).replace("\\", "/")
            
            # 创建远程目录（包括所有子目录）
            if remote_current_dir != final_remote_dir:  # 避免重复创建根目录
                print(f"📁 创建远程子目录: {remote_current_dir}")
                c.run(f"mkdir -p {remote_current_dir}", hide=True)
            
            # 上传当前目录下的所有文件
            for file_name in files:
                local_file_path = os.path.join(root, file_name)
                remote_file_path = os.path.join(remote_current_dir, file_name).replace("\\", "/")
                
                try:
                    print(f"📤 上传文件: {os.path.basename(local_file_path)} → {remote_file_path}")
                    c.put(local_file_path, remote=remote_file_path)
                    file_count += 1
                except Exception as e:
                    print(f"❌ 上传失败: {local_file_path} - {e}")
        
        print(f"✅ 上传完成！共上传 {file_count} 个文件到 {final_remote_dir}")
        
    except Exception as e:
        print(f"❌ 上传过程出错: {e}")
        raise
    finally:
        c.close()
        print("🔒 SSH连接已关闭")


def run_python_script(
    script_path: str,
    args: Optional[List[str]] = None,
    capture_output: bool = True,
    timeout: Optional[int] = None,
) -> Tuple[int, str, str]:
    """
    在一个独立的 Python 进程中执行脚本。

    :param script_path: 要执行的 Python 脚本路径 (.py)
    :param args: 传递给脚本的参数列表
    :param capture_output: 是否捕获 stdout/stderr
    :param timeout: 超时时间（秒）
    :return: (exit_code, stdout, stderr)
    """
    if args is None:
        args = []

    # 确保脚本路径存在
    script = Path(script_path).resolve()
    if not script.exists():
        raise FileNotFoundError(f"Script not found: {script}")

    # 构造执行命令
    cmd = [sys.executable, str(script), *map(str, args)]
    print(f"▶ Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            text=True,
            capture_output=capture_output,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        print(f"❌ Script {script} timed out after {timeout} seconds.")
        return 1, "", f"Timeout after {timeout} seconds."
    except Exception as e:
        print(f"❌ Failed to run script: {e}")
        return 1, "", str(e)


# ==================== 异步HTTP接口调用工具 ====================

async def async_http_request(
    url: str,
    method: str = "GET",
    json_data: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    异步HTTP请求
    
    参数:
        url: 请求URL
        method: HTTP方法 (GET, POST, PUT, DELETE, PATCH等)
        json_data: JSON格式的请求体
        data: 表单格式的请求体
        params: URL查询参数
        headers: 请求头
        timeout: 超时时间（秒）
    
    返回:
        包含响应信息的字典:
        {
            "status_code": int,
            "headers": dict,
            "body": dict | str,
            "success": bool
        }
    
    示例:
        # GET请求
        result = await async_http_request("https://api.example.com/users")
        
        # POST请求
        result = await async_http_request(
            "https://api.example.com/users",
            method="POST",
            json_data={"name": "John", "age": 30}
        )
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.request(
                method=method.upper(),
                url=url,
                json=json_data,
                data=data,
                params=params,
                headers=headers,
            )
            
            # 尝试解析JSON，失败则返回文本
            try:
                body = response.json()
            except Exception:
                body = response.text
            
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": body,
                "success": 200 <= response.status_code < 300
            }
            
        except httpx.TimeoutException as e:
            return {
                "status_code": 0,
                "headers": {},
                "body": f"Request timeout: {str(e)}",
                "success": False
            }
        except Exception as e:
            return {
                "status_code": 0,
                "headers": {},
                "body": f"Request error: {str(e)}",
                "success": False
            }


async def async_get(url: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    异步GET请求
    
    参数:
        url: 请求URL
        params: URL查询参数
        **kwargs: 其他参数（headers, timeout等）
    
    返回:
        响应字典
    
    示例:
        result = await async_get("https://api.example.com/users", params={"page": 1})
    """
    return await async_http_request(url, method="GET", params=params, **kwargs)


async def async_post(
    url: str, 
    json_data: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    异步POST请求
    
    参数:
        url: 请求URL
        json_data: JSON格式的请求体
        data: 表单格式的请求体
        **kwargs: 其他参数（headers, timeout等）
    
    返回:
        响应字典
    
    示例:
        result = await async_post(
            "https://api.example.com/users",
            json_data={"name": "John"}
        )
    """
    return await async_http_request(url, method="POST", json_data=json_data, data=data, **kwargs)


async def async_put(
    url: str,
    json_data: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    异步PUT请求
    
    参数:
        url: 请求URL
        json_data: JSON格式的请求体
        data: 表单格式的请求体
        **kwargs: 其他参数（headers, timeout等）
    
    返回:
        响应字典
    """
    return await async_http_request(url, method="PUT", json_data=json_data, data=data, **kwargs)


async def async_delete(url: str, **kwargs) -> Dict[str, Any]:
    """
    异步DELETE请求
    
    参数:
        url: 请求URL
        **kwargs: 其他参数（headers, timeout等）
    
    返回:
        响应字典
    """
    return await async_http_request(url, method="DELETE", **kwargs)


async def async_stream_request(
    url: str,
    method: str = "GET",
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 300.0,
) -> AsyncIterator[str]:
    """
    异步流式HTTP请求（适用于SSE、流式响应等）
    
    参数:
        url: 请求URL
        method: HTTP方法
        json_data: JSON格式的请求体
        params: URL查询参数
        headers: 请求头
        timeout: 超时时间（秒）
    
    返回:
        异步迭代器，逐行返回响应数据
    
    示例:
        async for line in async_stream_request("https://api.example.com/stream"):
            print(line)
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            method=method.upper(),
            url=url,
            json=json_data,
            params=params,
            headers=headers,
        ) as response:
            async for line in response.aiter_lines():
                yield line


async def async_stream_sse(
    url: str,
    method: str = "GET",
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 300.0,
) -> AsyncIterator[str]:
    """
    异步SSE流式请求，自动解析SSE格式
    
    参数:
        url: SSE接口URL
        method: HTTP方法
        json_data: JSON格式的请求体
        params: URL查询参数
        headers: 请求头
        timeout: 超时时间（秒）
    
    返回:
        异步迭代器，返回解析后的SSE数据（去掉"data: "前缀）
    
    示例:
        async for data in async_stream_sse("https://api.example.com/events"):
            print(f"收到事件: {data}")
    """
    async for line in async_stream_request(url, method, json_data, params, headers, timeout):
        # SSE格式：data: {...}
        if line.startswith('data: '):
            yield line[6:]  # 去掉 "data: " 前缀


async def async_download_file(
    url: str,
    save_path: str,
    chunk_size: int = 8192,
    timeout: float = 300.0,
    progress_callback: Optional[callable] = None
) -> bool:
    """
    异步下载文件
    
    参数:
        url: 文件URL
        save_path: 保存路径
        chunk_size: 每次读取的字节数
        timeout: 超时时间（秒）
        progress_callback: 进度回调函数 callback(downloaded_bytes, total_bytes)
    
    返回:
        是否下载成功
    
    示例:
        def progress(downloaded, total):
            print(f"进度: {downloaded}/{total} ({downloaded/total*100:.1f}%)")
        
        success = await async_download_file(
            "https://example.com/file.zip",
            "/path/to/save/file.zip",
            progress_callback=progress
        )
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                
                total_bytes = int(response.headers.get('content-length', 0))
                downloaded_bytes = 0
                
                # 确保目录存在
                os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
                
                with open(save_path, 'wb') as f:
                    async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                        f.write(chunk)
                        downloaded_bytes += len(chunk)
                        
                        if progress_callback and total_bytes:
                            progress_callback(downloaded_bytes, total_bytes)
                
                return True
                
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return False


