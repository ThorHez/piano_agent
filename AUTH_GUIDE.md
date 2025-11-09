# 认证配置指南

## 🔐 认证开关

本服务支持通过配置文件控制是否启用JWT认证。

## ⚙️ 配置方式

在 `config/config.yaml` 中设置：

```yaml
auth:
  enabled: false  # false=关闭认证，true=开启认证
  secret_key: "your-secret-key-here-change-in-production"
  algorithm: "HS256"
  access_token_expire_minutes: 30
```

## 🔓 关闭认证（开发模式）

适用于开发和测试环境。

### 配置

```yaml
auth:
  enabled: false  # 关闭认证
```

### 效果

- ✅ 所有API端点无需Token即可访问
- ✅ 不需要在请求头中添加 `Authorization`
- ✅ 适合本地开发和测试

### 使用示例

```bash
# 直接调用API，无需Token
curl http://localhost:8000/scores

curl -X POST http://localhost:8000/performances \
  -H "Content-Type: application/json" \
  -d '{"pieceId": "piece_1", "tempo": 120}'
```

## 🔒 开启认证（生产模式）

适用于生产环境，保护API安全。

### 配置

```yaml
auth:
  enabled: true   # 开启认证
  secret_key: "your-very-long-and-random-secret-key-at-least-32-chars"
  algorithm: "HS256"
  access_token_expire_minutes: 30
```

### 效果

- 🔒 所有带 `Depends(verify_token)` 的端点需要验证
- 🔒 请求必须携带有效的JWT Token
- 🔒 Token过期后需要重新获取

### 使用示例

```bash
# 1. 获取Token（需要实现登录接口）
TOKEN="your-jwt-token-here"

# 2. 带Token调用API
curl http://localhost:8000/scores \
  -H "Authorization: Bearer $TOKEN"

curl -X POST http://localhost:8000/performances \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"pieceId": "piece_1", "tempo": 120}'
```

## 🛠️ 启用认证的步骤

### 1. 修改配置文件

```yaml
auth:
  enabled: true  # 开启认证
  secret_key: "生成一个安全的密钥"
```

### 2. 生成安全密钥

```python
import secrets
secret_key = secrets.token_urlsafe(32)
print(secret_key)
```

或使用命令行：

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. 在API路由中启用认证

当前所有路由中的认证已注释，取消注释即可：

```python
from fastapi import Depends
from src.utils import verify_token

@router.get("/scores")
async def get_scores(
    token: dict = Depends(verify_token)  # 取消注释这行
):
    # ... 路由逻辑
```

### 4. 实现登录接口

创建登录接口来颁发Token：

```python
from fastapi import APIRouter
from src.utils import create_access_token

router = APIRouter()

@router.post("/login")
async def login(username: str, password: str):
    # 验证用户名和密码（这里简化处理）
    if username == "admin" and password == "password":
        # 创建Token
        token = create_access_token(
            data={"sub": username, "role": "admin"}
        )
        return {"access_token": token, "token_type": "bearer"}
    
    raise HTTPException(status_code=401, detail="Invalid credentials")
```

### 5. 重启服务

```bash
python run.py
```

## 📋 当前API认证状态

目前所有API路由中的认证都已**注释**，即使 `auth.enabled: true` 也不会验证。

要真正启用认证，需要：

1. 设置 `auth.enabled: true`
2. 取消路由中 `Depends(verify_token)` 的注释

### 需要取消注释的文件

- `src/api/chat.py` - 聊天接口
- `src/api/performance.py` - 演奏接口
- `src/api/history.py` - 历史接口
- `src/api/scores.py` - 曲库接口
- `src/api/music.py` - 音乐处理接口

## 🔄 快速切换

### 开发环境（无认证）

```yaml
auth:
  enabled: false
```

### 测试环境（有认证）

```yaml
auth:
  enabled: true
  secret_key: "test-secret-key-for-testing-only"
```

### 生产环境（严格认证）

```yaml
auth:
  enabled: true
  secret_key: "生产环境使用强随机密钥"
  access_token_expire_minutes: 15  # 缩短过期时间
```

## 🎯 最佳实践

### 开发阶段
- ✅ 使用 `enabled: false` 快速开发
- ✅ 无需每次请求都带Token
- ✅ 专注于业务逻辑实现

### 上线前
- ⚠️ 设置 `enabled: true`
- ⚠️ 生成强随机密钥
- ⚠️ 取消所有路由的认证注释
- ⚠️ 实现完整的登录/注册逻辑
- ⚠️ 测试所有需要认证的端点

### 生产环境
- 🔒 必须启用认证
- 🔒 使用环境变量存储密钥
- 🔒 定期轮换密钥
- 🔒 监控异常登录行为
- 🔒 实现Token刷新机制

## 🧪 测试

### 测试认证关闭

```bash
# 确保配置
auth:
  enabled: false

# 测试
curl http://localhost:8000/scores
# 应该返回数据，无需Token
```

### 测试认证开启

```bash
# 确保配置
auth:
  enabled: true

# 测试（应该失败）
curl http://localhost:8000/scores
# 应该返回 401 或要求提供Token

# 测试（带Token，应该成功）
curl http://localhost:8000/scores \
  -H "Authorization: Bearer your-valid-token"
# 应该返回数据
```

## ⚠️ 安全警告

1. **开发环境**：可以关闭认证（`enabled: false`）
2. **生产环境**：必须开启认证（`enabled: true`）
3. **永远不要**：在公网暴露的服务上关闭认证
4. **密钥管理**：不要把真实密钥提交到Git

## 💡 提示

- 配置修改后需要重启服务
- 可以通过环境变量覆盖配置
- 建议为不同环境准备不同的配置文件
- 使用 `config.dev.yaml`, `config.prod.yaml` 等

## 🆘 故障排除

### 问题：关闭认证后仍要求Token

**原因**：路由中未注释 `Depends(verify_token)`

**解决**：检查并注释掉路由中的认证依赖

### 问题：开启认证后所有请求都失败

**原因**：未实现登录接口或Token无效

**解决**：
1. 实现登录接口获取Token
2. 检查Token格式和有效期
3. 确认密钥配置正确

### 问题：配置不生效

**原因**：未重启服务

**解决**：修改配置后重启服务
```bash
python run.py
```

