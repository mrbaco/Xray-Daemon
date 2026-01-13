from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database import import_database
from loki_logger import Logger, LOGGER
from processing import process

from api import (
    users,
    stats,
    health
)


scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        await import_database()

        scheduler.add_job(
            process,
            trigger=IntervalTrigger(minutes=1),
            id='processing',
            replace_existing=True
        )
        scheduler.start()

        yield

    except Exception:
        exit()

    finally:
        scheduler.shutdown()

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
