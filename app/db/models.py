from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String
from sqlmodel import Field, SQLModel


class Habit(SQLModel, table=True):
    __tablename__ = "habits"

    id: int | None = Field(default=None, sa_column=Column(Integer, primary_key=True))
    name: str = Field(sa_column=Column(String(100), nullable=False))
    daily_target: int = Field(sa_column=Column(Integer, nullable=False))
    category: str = Field(sa_column=Column(String(50), nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
