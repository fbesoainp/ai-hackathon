from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from databases.mongo import MODELS
from utils.constants import DATABASE_NAME, MONGODB_DOMAIN, MONGODB_PASSWORD, MONGODB_USER
from utils.logging import logger


async def init_db() -> None:
    """Initialize the MongoDB database and Beanie models"""
    logger.info("Connecting to MongoDB...")
    mongo_uri = (
        f"mongodb+srv://{MONGODB_USER}:{MONGODB_PASSWORD}@{MONGODB_DOMAIN}?retryWrites=true&w=majority"
    )
    logger.info(f"MONGODB_URI: {mongo_uri}")
    client = AsyncIOMotorClient(mongo_uri)
    db = client[DATABASE_NAME]

    await init_beanie(database=db, document_models=MODELS)
    logger.info("MongoDB connected and Beanie models initialized.")
