from pydantic import BaseModel


class GoogleRestaurantQuery(BaseModel):
    title: str
    location: str
    min_price: int
    max_price: int


class GoogleRestaurantReview(BaseModel):
    rating: float
    text: str


class GoogleRestaurantInformation(BaseModel):
    name: str
    address: str
    rating: float
    user_ratings_total: int
    reviews: list[GoogleRestaurantReview]
    website: str
    description: str
    photo_url: str
