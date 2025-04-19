from datetime import datetime, timezone

from beanie import Document
from pydantic import Field


class Account(Document):
    created_at: datetime = Field(datetime.now(timezone.utc))
    updated_at: datetime = Field(datetime.now(timezone.utc))
    deleted_at: datetime | None = Field(None)
    google_user_id: str = Field(...)
    email: str = Field(...)
    name: str = Field(...)

    class Settings:
        name = "accounts"
