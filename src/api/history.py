"""
历史记录相关API - 使用数据库存储
"""
from typing import Optional
from fastapi import APIRouter, Query, Path, HTTPException

from src.database import db_manager, PerformanceHistoryDB


router = APIRouter()


@router.get("/history", summary="获取历史演奏记录")
async def get_history(
    limit: int = Query(20, description="返回记录数"),
    offset: int = Query(0, description="偏移量"),
    piece_id: Optional[str] = Query(None, description="曲目ID过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    # token: dict = Depends(verify_token)
):
    """
    获取历史演奏记录列表（从数据库）
    
    参数:
    - limit: 返回记录数量限制
    - offset: 偏移量（用于分页）
    - piece_id: 按曲目ID过滤
    - status: 按状态过滤
    """
    try:
        with db_manager.get_session() as session:
            records = PerformanceHistoryDB.get_all(
                session,
                limit=limit,
                offset=offset,
                piece_id=piece_id,
                status=status
            )
            
            # 转换为API响应格式
            return [record.to_dict() for record in records]
    except (IOError, RuntimeError) as e:
        print(f"❌ 获取历史记录失败: {e}")
        # 返回空列表而不是错误，保证服务可用
        return []


@router.get("/history/{history_id}", summary="获取单条历史详情")
async def get_history_item(
    history_id: str = Path(..., alias="id"),
    # token: dict = Depends(verify_token)
):
    """
    获取指定ID的历史记录详情（从数据库）
    """
    try:
        with db_manager.get_session() as session:
            record = PerformanceHistoryDB.get_by_id(session, history_id)
            
            if not record:
                raise HTTPException(status_code=404, detail="History item not found")
            
            return record.to_dict()
    
    except HTTPException:
        raise
    except (IOError, RuntimeError) as e:
        print(f"❌ 获取历史记录失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/history/statistics", summary="获取统计信息")
async def get_statistics(
    # token: dict = Depends(verify_token)
):
    """
    获取演奏统计信息
    """
    try:
        with db_manager.get_session() as session:
            stats = PerformanceHistoryDB.get_statistics(session)
            return stats
    
    except (IOError, RuntimeError) as e:
        print(f"❌ 获取统计信息失败: {e}")
        return {
            "total_performances": 0,
            "average_accuracy": 0,
            "total_duration_sec": 0
        }


@router.delete("/history/{history_id}", summary="删除历史记录")
async def delete_history_item(
    history_id: str = Path(..., alias="id"),
    # token: dict = Depends(verify_token)
):
    """
    删除指定的历史记录
    """
    try:
        with db_manager.get_session() as session:
            success = PerformanceHistoryDB.delete(session, history_id)
            
            if not success:
                raise HTTPException(status_code=404, detail="History item not found")
            
            return {"success": True, "message": "History item deleted"}
    
    except HTTPException:
        raise
    except (IOError, RuntimeError) as e:
        print(f"❌ 删除历史记录失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e
