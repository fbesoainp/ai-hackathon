from typing import List

from beanie.exceptions import DocumentNotFound
from fastapi import APIRouter, Depends

from databases.mongo.partner import create_partner, get_partner_by_google_user_id
from integrations.google_auth import verify_token
from models.google_user import GoogleUser
from models.partner import Partner, PartnerCreatePayload
from utils.logging import logger

router = APIRouter(prefix="/partners", tags=["partners"])


@router.get("")
async def get_partner(google_user: GoogleUser = Depends(verify_token)) -> Partner | None:
    """Get Partner by google_user"""
    try:
        return await get_partner_by_google_user_id(google_user.id)
    except DocumentNotFound:
        return None


@router.post("")
async def create_new_partner(payload: PartnerCreatePayload, google_user: GoogleUser = Depends(verify_token)) -> Partner:
    """Create a partner"""
    logger.info(f"Creating partner with payload: {payload} for google_user: {google_user}")
    partner = await create_partner(payload, google_user.id)
    return partner
