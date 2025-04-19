from datetime import date, datetime, timezone
from enum import Enum

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field


class CuisineType(str, Enum):
    INDIAN = "Indian"
    CHINESE = "Chinese"
    MEXICAN = "Mexican"
    ITALIAN = "Italian"
    THAI = "Thai"
    JAPANESE = "Japanese"
    AMERICAN = "American"
    FRENCH = "French"
    SPANISH = "Spanish"
    GREEK = "Greek"
    ASIAN = "Asian"
    MEDITERRANEAN = "Mediterranean"
    KOREAN = "Korean"


class DietType(str, Enum):
    VEGAN = "Vegan"
    VEGETARIAN = "Vegetarian"
    PESCATARIAN = "Pescatarian"
    GLUTEN_FREE = "Gluten Free"
    DAIRY_FREE = "Dairy Free"
    KETO = "Keto"
    HALAL = "Halal"
    KOSHER = "Kosher"


class AllergyType(str, Enum):
    PEANUT = "Peanut"
    TREE_NUT = "Tree Nut"
    DAIRY = "Dairy"
    EGG = "Egg"
    WHEAT = "Wheat"
    SOY = "Soy"
    FISH = "Fish"
    SHELLFISH = "Shellfish"
    SESAME = "Sesame"
    GLUTEN = "Gluten"
    SULFITE = "Sulfite"


class PartnerPreferences(BaseModel):
    preferred_cuisines: list[CuisineType] = Field(default_factory=list)
    disliked_cuisines: list[CuisineType] = Field(default_factory=list)
    diets: list[DietType] = Field(default_factory=list)
    allergies: list[AllergyType] = Field(default_factory=list)


class Partner(Document):
    created_at: datetime = Field(datetime.now(timezone.utc))
    updated_at: datetime = Field(datetime.now(timezone.utc))
    deleted_at: datetime | None = Field(None)
    google_user_id: str = Field(...)
    name: str = Field(...)
    # birth_date: date = Field(...)
    preferences: PartnerPreferences = Field(...)

    class Settings:
        name = "partners"


class PartnerCreatePayload(BaseModel):
    name: str = Field(...)
    # birth_date: date = Field(...)
    preferences: PartnerPreferences = Field(...)
