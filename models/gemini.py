RESTAURANT_QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
        },
        "location": {
            "type": "string",
        },
        "min_price": {
            "type": "number",
        },
        "max_price": {
            "type": "number",
        },
    },
    "required": ["title", "location", "min_price", "max_price"],
}

MATCHED_RESTAURANT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
        },
        "address": {
            "type": "string",
        },
        "rating": {
            "type": "number",
        },
        "user_ratings_total": {
            "type": "number",
        },
        "explanation": {
            "type": "string",
        },
        "website": {
            "type": "string",
        },
        "photo_url": {
            "type": "string",
        },
    },
    "required": ["name", "address", "rating", "user_ratings_total", "explanation", "website", "photo_url"],
}

MATCHED_RESTAURANTS_SCHEMA = {
    "type": "object",
    "properties": {
        "restaurants": {
            "type": "array",
            "items": MATCHED_RESTAURANT_SCHEMA,
        },
    },
    "required": ["restaurants"],
}
