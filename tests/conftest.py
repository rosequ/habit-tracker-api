from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.db.models import Habit
from app.db.session import async_session_maker
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def _clean_habits_table() -> AsyncGenerator[None, None]:
    yield
    async with async_session_maker() as session:
        await session.execute(delete(Habit))
        await session.commit()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
