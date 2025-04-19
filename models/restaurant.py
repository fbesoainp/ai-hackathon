from pydantic import BaseModel, Field


class UserRestaurantQueryPayload(BaseModel):
    user_query: str = Field(...)


class UserRestaurantQueryResponseItem(BaseModel):
    name: str
    address: str
    rating: float
    user_ratings_total: int
    explanation: str
    website: str
    photo_url: str


class UserRestaurantQueryResponse(BaseModel):
    restaurants: list[UserRestaurantQueryResponseItem]
