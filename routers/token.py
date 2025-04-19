from fastapi import APIRouter, Depends

from integrations.google_auth import verify_token

router = APIRouter(prefix="/token")


@router.get("/verify")
async def verify_google_token(_=Depends(verify_token)) -> None:
    """Verify the Google token"""
    None
