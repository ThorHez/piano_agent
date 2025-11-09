"""
清理数据库测试数据
"""
import os
from pathlib import Path

db_path = Path("./data/piano_agent.db")

if db_path.exists():
    print(f"🗑️  删除数据库文件: {db_path}")
    os.remove(db_path)
    print("✅ 数据库已删除")
else:
    print("ℹ️  数据库文件不存在")

print("\n💡 提示: 重新运行程序时会自动创建新的数据库")

