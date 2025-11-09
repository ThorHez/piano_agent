# Termitech Auto-Piano API Service

自动钢琴演奏系统的后端API服务，提供聊天、演奏控制、曲库管理等功能。

## 功能特性

- 🎹 **智能聊天**: 支持语音和文本聊天，流式响应
- 🎵 **演奏控制**: 创建、控制和监控钢琴演奏会话
- 📊 **实时推送**: 基于SSE的实时事件流（音符、手势、状态）
- 📚 **曲库管理**: 浏览、搜索、上传曲谱
- 📈 **历史记录**: 查看历史演奏记录和详情
- 🎼 **音乐分析**: 下载和分析MIDI/MusicXML文件

## 技术栈

- **FastAPI**: 现代、高性能的Python Web框架
- **SSE (Server-Sent Events)**: 实时事件推送
- **Pydantic**: 数据验证和序列化
- **JWT**: Token认证
- **Uvicorn**: ASGI服务器

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
# 方式1: 直接运行
python -m src.server

# 方式2: 使用uvicorn
uvicorn src.server:app --reload --host 0.0.0.0 --port 8000
```

### 3. 访问API文档

服务启动后，访问以下地址查看交互式API文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API端点

### 聊天相关

- `POST /chat` - 聊天主接口（SSE流式响应）
- `GET /chat/voice` - 语音转文字
- `GET /chat/history` - 获取聊天历史

### 演奏相关

- `POST /performances` - 创建/启动演奏
- `GET /performances/{id}` - 获取演奏状态
- `POST /performances/{id}/control` - 控制演奏（暂停/继续/停止）
- `GET /performances/{id}/stream` - 实时事件流（SSE）
- `GET /performances/{id}/events` - 获取离线事件
- `POST /performance/stream` - 曲目演奏接口

### 历史记录

- `GET /history` - 获取历史演奏记录
- `GET /history/{id}` - 获取单条历史详情

### 曲库管理

- `GET /scores` - 获取曲库列表（支持搜索）
- `POST /scores` - 上传曲谱（MIDI/MusicXML）

### 音乐处理

- `POST /download/music` - 下载音乐
- `POST /analyze_music` - 分析音乐并返回乐谱路径

## 项目结构

```
piano_agent_service/
├── config/
│   └── config.yaml          # 配置文件
├── src/
│   ├── api/                 # API路由模块
│   │   ├── __init__.py
│   │   ├── chat.py         # 聊天API
│   │   ├── performance.py  # 演奏API
│   │   ├── history.py      # 历史记录API
│   │   ├── scores.py       # 曲库API
│   │   └── music.py        # 音乐处理API
│   ├── models.py           # 数据模型
│   ├── storage.py          # 数据存储
│   ├── utils.py            # 工具函数
│   └── server.py           # 主服务器
├── requirements.txt        # 依赖列表
├── services.yaml          # OpenAPI规范
└── README.md              # 项目文档
```

## SSE事件类型

### 聊天事件
- `message` - 聊天消息

### 演奏事件
- `status` - 状态更新（preparing/playing/paused/ended/error）
- `note_frame` - 音符帧（note_on/note_off）
- `hand_pose` - 手部姿态和键位指示
- `log` - 实时日志
- `ping` - 心跳包

## 认证

API使用JWT Bearer Token认证。在请求头中添加：

```
Authorization: Bearer <your-token>
```

注意：当前认证已注释，可根据需要启用。

## 配置

配置文件位于 `config/config.yaml`，包括：

- 服务器配置（端口、主机等）
- JWT认证配置
- CORS配置
- 数据库配置
- 文件存储配置
- 演奏参数配置

## 开发

### 代码规范

项目使用标准的Python代码规范：
- 遵循PEP 8
- 使用类型注解
- 详细的文档字符串

### 测试

```bash
# 测试聊天接口
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'

# 测试演奏创建
curl -X POST http://localhost:8000/performances \
  -H "Content-Type: application/json" \
  -d '{"pieceId": "piece_1", "tempo": 120}'
```

## 数据存储

当前使用内存存储（InMemoryStorage），适合开发和测试。生产环境建议：

1. 使用PostgreSQL/MySQL等关系数据库
2. 使用Redis做缓存
3. 使用对象存储（S3/OSS）存储文件

## 性能优化

- 异步处理：所有接口都是异步的
- 流式响应：聊天和演奏使用SSE流式推送
- 连接池：数据库连接复用
- 缓存策略：常用数据缓存

## 部署

### Docker部署

```bash
# 构建镜像
docker build -t piano-api .

# 运行容器
docker run -p 8000:8000 piano-api
```

### 生产环境

```bash
# 使用gunicorn + uvicorn workers
gunicorn src.server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

## 许可证

MIT License

## 联系方式

- 项目: Termitech Auto-Piano
- 版本: 1.1.0

