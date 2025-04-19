from fastapi import APIRouter, Depends, Response

from business.query_restaurant import get_restaurants_by_user_query
from databases.mongo.partner import get_partner_by_google_user_id
from integrations.google_auth import verify_token
from integrations.google_maps import get_restaurant_photo
from models.google_user import GoogleUser
from models.restaurant import UserRestaurantQueryPayload, UserRestaurantQueryResponse

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.post("/query")
async def restaurant_query(
    payload: UserRestaurantQueryPayload, google_user: GoogleUser = Depends(verify_token)
) -> UserRestaurantQueryResponse:
    """Get the restaurant query from the user query"""
    partner = await get_partner_by_google_user_id(google_user.id)
    return get_restaurants_by_user_query(partner.preferences, payload.user_query)


@router.get("/{place_id}/photo")
async def restaurant_photo(place_id: str) -> Response:
    """Get the restaurant photo by place id"""
    return get_restaurant_photo(place_id)
