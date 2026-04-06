from fastapi import APIRouter
from app.core.settings import settings

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Limitr is running"}


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/protected")
async def protected():
    return {"message": "Request allowed"}
