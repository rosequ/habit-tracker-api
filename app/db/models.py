from datetime import date, datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
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


class Completion(SQLModel, table=True):
    __tablename__ = "completions"
    __table_args__ = (
        UniqueConstraint("habit_id", "completion_date", name="uq_completions_habit_id_completion_date"),
    )

    id: int | None = Field(default=None, sa_column=Column(Integer, primary_key=True))
    habit_id: int = Field(sa_column=Column(Integer, ForeignKey("habits.id"), nullable=False))
    completion_date: date = Field(sa_column=Column(Date, nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
