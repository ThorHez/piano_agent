from fastapi import APIRouter

router = APIRouter()


@router.post("/learning/start", summary="开始学习")
async def start_learning():
    """
    开始学习
    """
    
    return {"message": "学习开始"}


@router.post("/learning/end", summary="结束学习")
async def end_learning():
    """
    结束学习
    """
    return {"message": "学习结束"}