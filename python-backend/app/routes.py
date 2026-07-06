from fastapi import APIRouter

router = APIRouter()


@router.get("/", tags=["Health"])
async def health_check() -> dict:
    """
    Health-check endpoint.
    Returns a simple status payload to confirm the service is running.
    """
    return {"status": "running"}
