import os

from sqlalchemy.ext.asyncio import create_async_engine


def get_database_url() -> str:
    return os.environ["DATABASE_URL"]


engine = create_async_engine(get_database_url())
