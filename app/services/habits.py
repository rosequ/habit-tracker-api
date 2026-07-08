from typing import Annotated

from fastapi import Depends

from app.db.models import Habit
from app.repository.habits import HabitRepository, get_habit_repository


class HabitService:
    def __init__(self, repository: HabitRepository) -> None:
        self._repository = repository

    async def create_habit(self, *, name: str, daily_target: int, category: str) -> Habit:
        return await self._repository.create(
            name=name, daily_target=daily_target, category=category
        )

    async def get_habit(self, habit_id: int) -> Habit | None:
        return await self._repository.get_by_id(habit_id)


def get_habit_service(
    repository: Annotated[HabitRepository, Depends(get_habit_repository)],
) -> HabitService:
    return HabitService(repository)
