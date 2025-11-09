"""
数据库模型和连接管理
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, func, select
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.pool import StaticPool
from pathlib import Path

from src.config import config


# 创建Base类
Base = declarative_base()


class PerformanceHistory(Base):
    """演奏历史表"""
    __tablename__ = "performance_history"
    
    # 主键
    id = Column(String(50), primary_key=True, index=True)
    
    # 基本信息
    piece_id = Column(String(50), nullable=False, index=True)
    piece_name = Column(String(200), nullable=False)
    composer = Column(String(100))
    
    # 时间信息
    started_at = Column(DateTime, nullable=False, index=True)
    ended_at = Column(DateTime)
    duration_sec = Column(Integer)
    
    # 状态信息
    status = Column(String(20), nullable=False)  # idle, preparing, playing, paused, ended, error
    success = Column(Boolean, default=False)
    
    # 元数据
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "pieceId": self.piece_id,
            "pieceName": self.piece_name,
            "composer": self.composer,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "endedAt": self.ended_at.isoformat() if self.ended_at else None,
            "durationSec": self.duration_sec,
            "status": self.status,
            "success": self.success,
        }


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.database_url = self._get_database_url()
        self.engine = None
        self.session_maker = None
        
    def _get_database_url(self) -> str:
        """获取数据库URL"""
        db_type = config.get('database.type', 'sqlite')
        
        if db_type == 'sqlite':
            # SQLite数据库
            db_path = config.get('database.path', './data/piano_agent.db')
            # 确保数据目录存在
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{db_path}"
        else:
            # 其他数据库
            return config.get('database.url', 'sqlite:///./data/piano_agent.db')
    
    def init_db(self):
        """初始化数据库（同步方式）"""
        print(f"📊 正在初始化数据库: {self.database_url}")
        
        # 创建同步引擎
        if self.database_url.startswith('sqlite'):
            # SQLite 使用特殊配置以支持多线程
            self.engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=config.get('database.echo', False)
            )
        else:
            self.engine = create_engine(
                self.database_url,
                echo=config.get('database.echo', False)
            )
        
        # 创建所有表
        Base.metadata.create_all(bind=self.engine)
        print("✅ 数据库表创建成功")
        
        # 创建Session工厂
        from sqlalchemy.orm import sessionmaker
        self.session_maker = sessionmaker(bind=self.engine)
        
        # 显示表信息
        self._show_tables_info()
    
    def _show_tables_info(self):
        """显示数据库表信息"""
        tables = Base.metadata.tables.keys()
        print(f"📋 数据库表: {', '.join(tables)}")
        
        # 显示记录数
        with self.get_session() as session:
            count = session.query(PerformanceHistory).count()
            print(f"📊 演奏历史记录数: {count}")
    
    def get_session(self) -> Session:
        """获取数据库Session"""
        if not self.session_maker:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return self.session_maker()
    
    def check_connection(self) -> bool:
        """检查数据库连接"""
        try:
            from sqlalchemy import text
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except (IOError, RuntimeError) as e:
            print(f"❌ 数据库连接失败: {e}")
            return False


# 全局数据库管理器实例
db_manager = DatabaseManager()


# CRUD操作函数
class PerformanceHistoryDB:
    """演奏历史数据库操作"""
    
    @staticmethod
    def create(session: Session, **kwargs) -> PerformanceHistory:
        """
        创建新记录
        
        如果未提供id，将自动生成一个唯一ID
        """
        # 如果没有提供id，自动生成
        if 'id' not in kwargs or not kwargs['id']:
            from src.utils import generate_id
            kwargs['id'] = generate_id()
        
        record = PerformanceHistory(**kwargs)
        session.add(record)
        session.commit()
        session.refresh(record)
        return record
    
    @staticmethod
    def create_or_update(session: Session, record_id: str, **kwargs) -> PerformanceHistory:
        """创建或更新记录（如果ID已存在则更新）"""
        existing = PerformanceHistoryDB.get_by_id(session, record_id)
        if existing:
            # 记录已存在，更新它
            for key, value in kwargs.items():
                if hasattr(existing, key) and key != 'id':
                    setattr(existing, key, value)
            existing.updated_at = datetime.now()
            session.commit()
            session.refresh(existing)
            return existing
        else:
            # 记录不存在，创建新记录
            kwargs['id'] = record_id
            return PerformanceHistoryDB.create(session, **kwargs)
    
    @staticmethod
    def get_by_id(session: Session, record_id: str) -> Optional[PerformanceHistory]:
        """根据ID获取记录"""
        return session.query(PerformanceHistory).filter(
            PerformanceHistory.id == record_id
        ).first()
    
    @staticmethod
    def get_all(
        session: Session,
        limit: int = 20,
        offset: int = 0,
        piece_id: Optional[str] = None,
        status: Optional[str] = None,
        order_by: str = "started_at"
    ) -> list[PerformanceHistory]:
        """获取所有记录"""
        query = session.query(PerformanceHistory)
        
        # 过滤条件
        if piece_id:
            query = query.filter(PerformanceHistory.piece_id == piece_id)
        if status:
            query = query.filter(PerformanceHistory.status == status)
        
        # 排序
        if order_by == "started_at":
            query = query.order_by(PerformanceHistory.started_at.desc())
        elif order_by == "accuracy_score":
            query = query.order_by(PerformanceHistory.accuracy_score.desc())
        
        # 分页
        query = query.offset(offset).limit(limit)
        
        return query.all()
    
    @staticmethod
    def update(session: Session, record_id: str, **kwargs) -> Optional[PerformanceHistory]:
        """更新记录"""
        record = PerformanceHistoryDB.get_by_id(session, record_id)
        if record:
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            record.updated_at = datetime.now()
            session.commit()
            session.refresh(record)
        return record
    
    @staticmethod
    def delete(session: Session, record_id: str) -> bool:
        """删除记录"""
        record = PerformanceHistoryDB.get_by_id(session, record_id)
        if record:
            session.delete(record)
            session.commit()
            return True
        return False


    @staticmethod
    def delete_all(session: Session) -> bool:
        """删除所有记录"""
        session.query(PerformanceHistory).delete()
        session.commit()
        return True
    
    
    @staticmethod
    def get_statistics(session: Session) -> dict:
        """获取统计信息"""
        # 使用 select 语句进行查询
        stmt = select(
            func.count(PerformanceHistory.id).label('total'),
            func.sum(PerformanceHistory.duration_sec).label('total_duration'),
        )
        
        result = session.execute(stmt).first()
        
        if result:
            return {
                "total_performances": result.total or 0,
                "total_duration_sec": result.total_duration or 0,
            }
        else:
            return {
                "total_performances": 0,
                "total_duration_sec": 0,
            }

