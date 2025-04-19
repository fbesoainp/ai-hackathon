from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI

from databases.mongo.orm import init_db
from routers import ROUTERS
from utils.logging import logger


@asynccontextmanager
async def lifespan(_) -> AsyncGenerator[None, Any]:
    """Lifespan event handler"""
    await init_db()
    yield
    logger.info("Shutting down the application.")


app = FastAPI(lifespan=lifespan)
for router in ROUTERS:
    app.include_router(router)
