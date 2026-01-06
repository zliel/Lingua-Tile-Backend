import logging

# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.triggers.interval import IntervalTrigger
# from services.notifications import check_overdue_reviews
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pymongo import AsyncMongoClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.cache_config import setup_cache

# Setup cache BEFORE importing API routes to ensure decorators bind to correct config
setup_cache()

# ruff: noqa: E402
from api import dependencies
from api.auth import router as auth_router
from api.cards import router as cards_router
from api.lessons import router as lessons_router
from api.notifications import router as notifications_router
from api.sections import router as section_router
from api.translations import router as translations_router
from api.users import router as users_router
from app.cache_config import setup_cache
from app.config import get_settings
from app.exception_handlers import add_exception_handlers
from app.limiter import limiter
from app.logging_config import setup_logging
from app.middleware.correlation import CorrelationIdMiddleware

# setup_cache()
settings = get_settings()
# scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    mongo_host = settings.MONGO_HOST
    if mongo_host:
        dependencies.db_client = AsyncMongoClient(mongo_host)
        # Store in app.state for cleaner access (even though dependencies.db_client is still used)
        app.state.mongo_client = dependencies.db_client
        logging.info("Connected to MongoDB")
    else:
        logging.warning("MONGO_HOST not set, skipping MongoDB connection")

    # scheduler.add_job(
    #     check_overdue_reviews,
    #     IntervalTrigger(hours=24),  # Check every 24 hours
    #     id="check_reviews",
    #     replace_existing=True,
    # )
    # scheduler.start()

    yield

    if dependencies.db_client:
        await dependencies.db_client.close()
        logging.info("Closed MongoDB connection")


app = FastAPI(
    title=settings.TITLE,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
)
app.include_router(cards_router)
app.include_router(lessons_router)
app.include_router(translations_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(section_router)
app.include_router(notifications_router)

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
@limiter.limit("5/minute")
async def root(request: Request):
    return {"message": "Hello World!"}


add_exception_handlers(app)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(CorrelationIdMiddleware)
