"""
测试自动生成ID的功能
"""
from src.database import db_manager, PerformanceHistoryDB
from datetime import datetime

# 初始化数据库
db_manager.init_db()

print("=" * 60)
print("📝 测试自动生成ID功能")
print("=" * 60)

# 示例1: 不指定ID（自动生成）
print("\n【示例1】不指定ID - 自动生成")
print("-" * 60)
with db_manager.get_session() as session:
    record1 = PerformanceHistoryDB.create(
        session,
        # 没有指定 id 参数
        piece_id="piece_1",
        piece_name="月光奏鸣曲",
        composer="贝多芬",
        started_at=datetime.now(),
        status="ended",
        success=True
    )
    print(f"✅ 自动生成的ID: {record1.id}")
    print(f"   曲目: {record1.piece_name}")

# 示例2: ID为None（也会自动生成）
print("\n【示例2】ID=None - 自动生成")
print("-" * 60)
with db_manager.get_session() as session:
    record2 = PerformanceHistoryDB.create(
        session,
        id=None,  # 明确指定为None
        piece_id="piece_2",
        piece_name="致爱丽丝",
        composer="贝多芬",
        started_at=datetime.now(),
        status="ended",
        success=True
    )
    print(f"✅ 自动生成的ID: {record2.id}")
    print(f"   曲目: {record2.piece_name}")

# 示例3: 手动指定ID
print("\n【示例3】手动指定ID")
print("-" * 60)
with db_manager.get_session() as session:
    record3 = PerformanceHistoryDB.create(
        session,
        id="my_custom_id_001",  # 手动指定
        piece_id="piece_3",
        piece_name="肖邦夜曲",
        composer="肖邦",
        started_at=datetime.now(),
        status="ended",
        success=True
    )
    print(f"✅ 手动指定的ID: {record3.id}")
    print(f"   曲目: {record3.piece_name}")

# 查看所有记录
print("\n【所有记录】")
print("-" * 60)
with db_manager.get_session() as session:
    records = PerformanceHistoryDB.get_all(session, limit=10)
    for idx, r in enumerate(records, 1):
        print(f"{idx}. ID: {r.id[:16]}... | {r.piece_name} ({r.composer})")

# 统计信息
print("\n【统计信息】")
print("-" * 60)
with db_manager.get_session() as session:
    stats = PerformanceHistoryDB.get_statistics(session)
    print(f"总记录数: {stats['total_performances']}")
    print(f"总时长: {stats['total_duration_sec']} 秒")

print("\n" + "=" * 60)
print("✅ 测试完成！")
print("=" * 60)

