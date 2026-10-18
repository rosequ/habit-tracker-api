from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import Depends

from app.db.models import Completion
from app.repository.completions import (
    CompletionRepository,
    DuplicateCompletionError as RepositoryDuplicateCompletionError,
    get_completion_repository,
)
from app.repository.habits import HabitRepository, get_habit_repository


class HabitNotFoundError(Exception):
    pass


class FutureCompletionDateError(Exception):
    pass


class DuplicateCompletionError(Exception):
    pass


class CompletionService:
    def __init__(
        self, habit_repository: HabitRepository, completion_repository: CompletionRepository
    ) -> None:
        self._habit_repository = habit_repository
        self._completion_repository = completion_repository

    async def create_completion(
        self, *, habit_id: int, completion_date: date | None
    ) -> Completion:
        resolved_date = completion_date or datetime.now(timezone.utc).date()
        if resolved_date > datetime.now(timezone.utc).date():
            raise FutureCompletionDateError

        habit = await self._habit_repository.get_by_id(habit_id)
        if habit is None:
            raise HabitNotFoundError

        return await self._completion_repository.create(
            habit_id=habit_id, completion_date=resolved_date
        )


def get_completion_service(
    habit_repository: Annotated[HabitRepository, Depends(get_habit_repository)],
    completion_repository: Annotated[CompletionRepository, Depends(get_completion_repository)],
) -> CompletionService:
    return CompletionService(habit_repository, completion_repository)
