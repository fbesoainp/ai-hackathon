from beanie import PydanticObjectId
from beanie.exceptions import DocumentNotFound

from models.account import Account


async def create_account(google_user_id: str, email: str, name: str) -> Account:
    """Create a account"""
    return await Account(google_user_id=google_user_id, email=email, name=name).insert()


async def get_account_by_id(id_account: PydanticObjectId) -> Account:
    """Get a account by id"""
    account = await Account.find_one(Account.id == id_account, Account.deleted_at == None)

    if not account:
        raise DocumentNotFound("Account not found")
    return account


async def get_account_by_google_user_id(google_user_id: str) -> Account:
    """Get a account by id"""
    account = await Account.find_one(Account.google_user_id == google_user_id, Account.deleted_at == None)

    if not account:
        raise DocumentNotFound("Account not found")
    return account
