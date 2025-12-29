import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import get_settings
from api import dependencies
from pymongo import AsyncMongoClient
import os


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture
def settings():
    return get_settings()


@pytest_asyncio.fixture
async def db_client(settings):
    if settings.MONGO_HOST:
        client = AsyncMongoClient(settings.MONGO_HOST)
        yield client
        await client.close()
    else:
        yield None


@pytest_asyncio.fixture
async def db(db_client):
    if db_client:
        return db_client["lingua-tile-test"]
    return None


@pytest_asyncio.fixture(autouse=True)
async def override_dependency(db_client):
    if db_client:
        app.state.mongo_client = db_client
        dependencies.db_client = db_client

        async def override_get_db():
            yield db_client["lingua-tile-test"]

        app.dependency_overrides[dependencies.get_db] = override_get_db

    yield

    app.dependency_overrides = {}

    if db_client:
        await db_client["lingua-tile-test"].users.delete_many({})
        await db_client["lingua-tile-test"].lessons.delete_many({})
        await db_client["lingua-tile-test"].cards.delete_many({})
        await db_client["lingua-tile-test"].lesson_reviews.delete_many({})
        await db_client["lingua-tile-test"].review_logs.delete_many({})
        await db_client["lingua-tile-test"].sections.delete_many({})
