from src.database import db_manager, PerformanceHistoryDB
from datetime import datetime

# 初始化数据库
db_manager.init_db()

# 测试连接
result = db_manager.check_connection()
print(f"✅ 数据库连接测试: {'成功' if result else '失败'}")

# 不指定ID，让系统自动生成
print(f"\n📝 插入测试记录（自动生成ID）")

with db_manager.get_session() as session:
    record = PerformanceHistoryDB.create(
        session,
        # 不指定 id，会自动生成
        piece_id="piece_1",
        piece_name="测试曲目",
        composer="测试作曲家",
        started_at=datetime.now(),
        status="ended",
        success=True
    )
    print(f"✅ 记录创建成功，自动生成的ID: {record.id}")

# 查询记录（保存刚创建的ID）
created_id = record.id
print(f"\n📊 查询刚创建的记录:")
with db_manager.get_session() as session:
    record = PerformanceHistoryDB.get_by_id(session, created_id)
    if record:
        print(f"   - ID: {record.id}")
        print(f"   - 曲目: {record.piece_name}")
        print(f"   - 作曲家: {record.composer}")
        print(f"   - 状态: {record.status}")
        print(f"   - 成功: {record.success}")

# 获取所有记录
print(f"\n📋 所有记录:")
with db_manager.get_session() as session:
    records = PerformanceHistoryDB.get_all(session, limit=10)
    for r in records:
        print(f"   - {r.piece_name} ({r.composer}) - {r.status}")

# 获取统计信息
print(f"\n📈 数据库统计:")
with db_manager.get_session() as session:
    stats = PerformanceHistoryDB.get_statistics(session)
    print(f"   - 总记录数: {stats['total_performances']}")
    print(f"   - 总时长: {stats['total_duration_sec']} 秒")

    # delete_all_records = PerformanceHistoryDB.delete_all(session)
    # print(f"   - 删除所有记录: {delete_all_records}")

print("\n✅ 测试完成！")
