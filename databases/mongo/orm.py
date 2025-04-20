from beanie import init_beanie

from lancedb.cloud import connect
from databases.mongo import MODELS
from utils.constants import LANCE_URI, LANCE_API_KEY
from utils.logging import logger


async def init_db() -> None:
    """Initialize the Lance database and Beanie models"""
    logger.info("Connecting to LanceDB...")
    logger.info(f"LANCEDB_URI: {LANCE_URI}")
    db = connect(uri=LANCE_URI, api_key=LANCE_API_KEY)
    await init_beanie(database=db, document_models=MODELS)
    logger.info("MongoDB connected and Beanie models initialized.")
