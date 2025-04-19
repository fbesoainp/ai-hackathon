from beanie import PydanticObjectId
from beanie.exceptions import DocumentNotFound
from bson import ObjectId

from databases.mongo.account import get_account_by_id
from models.partner import Partner, PartnerCreatePayload
from utils.logging import logger


async def get_partners() -> list[Partner]:
    """Get all partners"""
    return await Partner.find_all().to_list()


async def create_partner(payload: PartnerCreatePayload, google_user_id: str) -> Partner:
    """Create a partner"""
    return await Partner(
        name=payload.name,
        google_user_id=google_user_id,
        preferences=payload.preferences,
    ).insert()


async def get_partner_by_id(partner_id: PydanticObjectId) -> Partner:
    """Get a partner by id"""
    partner = await Partner.find_one(Partner.id == partner_id, Partner.deleted_at == None)

    if not partner:
        raise DocumentNotFound("Partner not found")
    return partner


async def get_partner_by_id_account(id_account: PydanticObjectId) -> Partner:
    """Get a partner by id_account"""
    partner = await Partner.find_one(Partner.id_account == id_account, Partner.deleted_at == None)

    if not partner:
        error = f"Partner not found for account {id_account}"
        logger.error(error)
        raise DocumentNotFound(error)
    return partner


async def get_partner_by_google_user_id(google_user_id: str) -> Partner:
    """Get a partner by google_user_id"""
    logger.info(f"Getting partner by google_user_id {google_user_id}")
    partner = await Partner.find_one(Partner.google_user_id == google_user_id, Partner.deleted_at == None)
    if not partner:
        error = f"Partner not found for google_user_id {google_user_id}"
        logger.error(error)
        raise DocumentNotFound(error)
    return partner
