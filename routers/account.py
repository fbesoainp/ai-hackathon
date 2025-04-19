from beanie.exceptions import DocumentNotFound
from fastapi import APIRouter, Depends

from databases.mongo.account import create_account, get_account_by_google_user_id
from integrations.google_auth import verify_token
from models.account import Account
from models.google_user import GoogleUser

router = APIRouter(prefix="/accounts", tags=["partners"])


@router.get("")
async def get_account_by_id_google_user_id(google_user: GoogleUser = Depends(verify_token)) -> Account:
    """Get a account by id"""
    try:
        return await get_account_by_google_user_id(google_user.id)
    except DocumentNotFound:
        return await create_account(google_user.id, google_user.email, google_user.name)
