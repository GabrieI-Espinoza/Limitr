from fastapi import APIRouter

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
