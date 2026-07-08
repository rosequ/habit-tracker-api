from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Habit
from app.db.session import get_session


class HabitRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, name: str, daily_target: int, category: str) -> Habit:
        habit = Habit(name=name, daily_target=daily_target, category=category)
        self._session.add(habit)
        await self._session.commit()
        await self._session.refresh(habit)
        return habit

    async def get_by_id(self, habit_id: int) -> Habit | None:
        return await self._session.get(Habit, habit_id)


def get_habit_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HabitRepository:
    return HabitRepository(session)
