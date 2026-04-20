from fastapi import APIRouter


router = APIRouter(prefix="/api/v1/sample", tags=["sample"])


@router.get("/")
async def get_sample():
    return {"message": "Hello, Sample API!"}


@router.get("/health")
async def health_check():
    return {"status": "ok"}