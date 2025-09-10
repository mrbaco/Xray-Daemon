from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from database import import_database
from loki_logger import Logger, LOGGER

from api import (
    users,
    stats,
    health,
    routine
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await import_database()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    BaseHTTPMiddleware,
    Logger(
        logger=LOGGER,
        req_body_required=True
    )
)

app.include_router(users.router)
app.include_router(stats.router)
app.include_router(health.router)
app.include_router(routine.router)
