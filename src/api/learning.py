from fastapi import APIRouter
from src.config import config
from src.utils import async_get


router = APIRouter()


@router.post("/learning/start", summary="开始学习")
async def start_learning():
    """
    开始学习
    """
    response = await async_get(config.learning_start_url)
    response = response["body"]
    return response


@router.post("/learning/end", summary="结束学习")
async def end_learning():
    """
    结束学习
    """
    response = await async_get(config.learning_end_url)
    response = response["body"]
    return response