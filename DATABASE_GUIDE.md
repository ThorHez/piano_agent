# 数据库使用指南

## 📊 数据库架构

本服务使用 **SQLite** 数据库存储演奏历史记录，支持自动初始化和迁移。

## 🗄️ 数据库表结构

### performance_history（演奏历史表）

| 字段 | 类型 | 说明 | 索引 |
|------|------|------|------|
| id | String(50) | 主键，演奏会话ID | ✓ |
| piece_id | String(50) | 曲目ID | ✓ |
| piece_name | String(200) | 曲目名称 | |
| composer | String(100) | 作曲家 | |
| started_at | DateTime | 开始时间 | ✓ |
| ended_at | DateTime | 结束时间 | |
| duration_sec | Integer | 持续时长（秒） | |
| tempo | Integer | 速度（BPM） | |
| hands | String(10) | 使用的手（both/left/right） | |
| status | String(20) | 状态 | |
| success | Boolean | 是否成功完成 | |
| accuracy_score | Float | 准确率（0.0-1.0） | |
| error_notes | Integer | 错误音符数 | |
| total_notes | Integer | 总音符数 | |
| log_url | String(500) | 日志URL | |
| replay_id | String(50) | 回放ID | |
| notes | Text | 备注 | |
| created_at | DateTime | 创建时间 | |
| updated_at | DateTime | 更新时间 | |

## ⚙️ 配置

在 `config/config.yaml` 中配置数据库：

```yaml
database:
  type: "sqlite"  # 数据库类型
  path: "./data/piano_agent.db"  # 数据库文件路径
  url: "sqlite:///./data/piano_agent.db"  # 完整URL（可选）
  echo: false  # 是否打印SQL语句（调试用）
```

## 🚀 自动初始化

服务启动时会自动：

1. ✅ 检查数据库文件是否存在
2. ✅ 创建 `data` 目录（如果不存在）
3. ✅ 创建所有数据库表
4. ✅ 显示初始化信息

### 启动日志示例

```bash
$ python run.py

🎹 Termitech Auto-Piano API Service Starting...
📋 配置: 0.0.0.0:8000
📊 正在初始化数据库: sqlite:///./data/piano_agent.db
✅ 数据库表创建成功
📋 数据库表: performance_history
📊 演奏历史记录数: 0
✅ Service ready!
```

## 💾 数据库操作

### 使用 PerformanceHistoryDB 类

```python
from src.database import db_manager, PerformanceHistoryDB

# 获取Session
with db_manager.get_session() as session:
    
    # 创建记录
    record = PerformanceHistoryDB.create(
        session,
        id="perf_123",
        piece_id="piece_1",
        piece_name="月光奏鸣曲",
        composer="贝多芬",
        started_at=datetime.now(),
        tempo=120,
        hands="both",
        status="playing"
    )
    
    # 查询单条记录
    record = PerformanceHistoryDB.get_by_id(session, "perf_123")
    
    # 查询所有记录
    records = PerformanceHistoryDB.get_all(
        session,
        limit=20,
        offset=0,
        piece_id="piece_1",  # 可选过滤
        status="ended"  # 可选过滤
    )
    
    # 更新记录
    updated = PerformanceHistoryDB.update(
        session,
        "perf_123",
        status="ended",
        success=True,
        accuracy_score=0.95
    )
    
    # 删除记录
    success = PerformanceHistoryDB.delete(session, "perf_123")
    
    # 获取统计信息
    stats = PerformanceHistoryDB.get_statistics(session)
    # 返回: {
    #   "total_performances": 10,
    #   "average_accuracy": 0.87,
    #   "total_duration_sec": 3600
    # }
```

## 🔌 API端点

### 获取历史记录

```bash
GET /history?limit=20&offset=0&piece_id=piece_1&status=ended
```

参数：
- `limit`: 返回数量（默认20）
- `offset`: 偏移量（用于分页）
- `piece_id`: 按曲目ID过滤
- `status`: 按状态过滤

### 获取单条历史

```bash
GET /history/{id}
```

### 获取统计信息

```bash
GET /history/statistics
```

返回：
```json
{
  "total_performances": 10,
  "average_accuracy": 0.87,
  "total_duration_sec": 3600
}
```

### 删除历史记录

```bash
DELETE /history/{id}
```

## 🔄 演奏流程与数据库

演奏完成后，系统会自动保存记录到数据库：

```
1. 用户创建演奏会话
   ↓
2. 演奏进行中（内存存储）
   ↓
3. 演奏结束
   ↓
4. 自动保存到数据库 ✅
   ↓
5. 可通过 API 查询历史
```

## 🛠️ 数据库管理

### 查看数据库文件

```bash
ls -lh data/piano_agent.db
```

### 使用 SQLite 命令行工具

```bash
# 打开数据库
sqlite3 data/piano_agent.db

# 查看所有表
.tables

# 查看表结构
.schema performance_history

# 查询数据
SELECT * FROM performance_history LIMIT 10;

# 退出
.quit
```

### 备份数据库

```bash
# 备份
cp data/piano_agent.db data/piano_agent.db.backup

# 或使用 SQLite 备份命令
sqlite3 data/piano_agent.db ".backup data/piano_agent.db.backup"
```

### 清空数据

```bash
# 删除数据库文件（重启服务会自动重建）
rm data/piano_agent.db

# 或使用SQL清空表
sqlite3 data/piano_agent.db "DELETE FROM performance_history;"
```

## 🔍 调试

### 启用SQL日志

在 `config/config.yaml` 中：

```yaml
database:
  echo: true  # 打印所有SQL语句
```

重启服务后，所有SQL语句会打印到控制台。

### 检查数据库连接

```python
from src.database import db_manager

# 初始化
db_manager.init_db()

# 检查连接
if db_manager.check_connection():
    print("✅ 数据库连接正常")
else:
    print("❌ 数据库连接失败")
```

## 📈 性能优化

### 索引

已为以下字段创建索引：
- `id` (主键)
- `piece_id` (曲目查询)
- `started_at` (时间排序)

### 分页查询

使用 `limit` 和 `offset` 进行分页：

```python
# 第一页（0-19）
records = PerformanceHistoryDB.get_all(session, limit=20, offset=0)

# 第二页（20-39）
records = PerformanceHistoryDB.get_all(session, limit=20, offset=20)
```

### 连接池

SQLite使用 `StaticPool` 以支持多线程访问。

## 🔐 数据安全

### 数据库文件权限

```bash
# 设置适当的权限
chmod 600 data/piano_agent.db
```

### 定期备份

建议设置定期备份脚本：

```bash
#!/bin/bash
# backup_db.sh
BACKUP_DIR="./backups"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)
cp data/piano_agent.db "$BACKUP_DIR/piano_agent_$DATE.db"
echo "✅ 备份完成: piano_agent_$DATE.db"

# 保留最近7天的备份
find $BACKUP_DIR -name "piano_agent_*.db" -mtime +7 -delete
```

## 🚀 迁移到生产数据库

### 切换到 PostgreSQL

1. 修改配置：

```yaml
database:
  type: "postgresql"
  url: "postgresql://user:password@localhost/piano_agent"
  echo: false
```

2. 安装驱动：

```bash
pip install psycopg2-binary
```

3. 重启服务，表会自动创建

### 数据迁移

```python
# 从SQLite导出数据
import sqlite3
import json

conn = sqlite3.connect('data/piano_agent.db')
cursor = conn.execute('SELECT * FROM performance_history')
data = cursor.fetchall()

# 导入到PostgreSQL
# ... 使用 SQLAlchemy 导入
```

## 🧪 测试

### 测试数据库初始化

```bash
python -c "from src.database import db_manager; db_manager.init_db()"
```

### 插入测试数据

```python
from datetime import datetime
from src.database import db_manager, PerformanceHistoryDB

db_manager.init_db()

with db_manager.get_session() as session:
    record = PerformanceHistoryDB.create(
        session,
        id="test_001",
        piece_id="piece_1",
        piece_name="测试曲目",
        composer="测试作曲家",
        started_at=datetime.now(),
        tempo=120,
        hands="both",
        status="ended",
        success=True
    )
    print(f"✅ 创建测试记录: {record.id}")
```

## ❓ 常见问题

### Q: 数据库文件在哪里？

A: 默认在 `./data/piano_agent.db`，可在配置文件中修改。

### Q: 如何重置数据库？

A: 删除数据库文件，重启服务会自动重建：
```bash
rm data/piano_agent.db
python run.py
```

### Q: 支持其他数据库吗？

A: 支持！只需修改 `database.url` 为对应的连接字符串：
- PostgreSQL: `postgresql://user:pass@host/db`
- MySQL: `mysql://user:pass@host/db`

### Q: 数据库文件变大怎么办？

A: 可以使用 SQLite 的 VACUUM 命令：
```bash
sqlite3 data/piano_agent.db "VACUUM;"
```

## 📚 相关文档

- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [SQLite 文档](https://www.sqlite.org/docs.html)
- [FastAPI 数据库](https://fastapi.tiangolo.com/tutorial/sql-databases/)

