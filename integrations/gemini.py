import json

import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel

from models.gemini import MATCHED_RESTAURANTS_SCHEMA, RESTAURANT_QUERY_SCHEMA
from models.maps import GoogleRestaurantInformation, GoogleRestaurantQuery
from models.partner import PartnerPreferences
from models.restaurant import UserRestaurantQueryResponse
from utils.constants import PROJECT_ID, LOCATION, MODEL
from utils.logging import logger
from utils.prompts import get_restaurant_priority_prompt, get_restaurant_query_prompt

vertexai.init(project=PROJECT_ID, location=LOCATION)
model = GenerativeModel(MODEL)


def get_restaurant_query(parter_preferences: PartnerPreferences, user_query: str) -> GoogleRestaurantQuery:
    """Get the restaurant query from the user query and partner preferences"""
    logger.info(
        f"Getting restaurant query for user query: {user_query}, with partner preferences: {parter_preferences}"
    )
    response = model.generate_content(
        get_restaurant_query_prompt(parter_preferences, user_query),
        generation_config=GenerationConfig(
            response_mime_type="application/json", response_schema=RESTAURANT_QUERY_SCHEMA
        ),
    )
    response_json = json.loads(response.text)
    return GoogleRestaurantQuery(**response_json)


def match_restaurants(
    restaurants: list[GoogleRestaurantInformation], partner_preferences: PartnerPreferences, user_query: str
) -> UserRestaurantQueryResponse:
    """Match restaurants based on the user query, partner preferences and restaurant options"""
    logger.info("Matching restaurants")
    response = model.generate_content(
        get_restaurant_priority_prompt(restaurants, partner_preferences, user_query),
        generation_config=GenerationConfig(
            response_mime_type="application/json", response_schema=MATCHED_RESTAURANTS_SCHEMA
        ),
    )
    response_json = json.loads(response.text)
    return UserRestaurantQueryResponse(**response_json)
