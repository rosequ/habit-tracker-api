from datetime import date
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Completion
from app.db.session import get_session


class DuplicateCompletionError(Exception):
    pass


class CompletionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, habit_id: int, completion_date: date) -> Completion:
        completion = Completion(habit_id=habit_id, completion_date=completion_date)
        self._session.add(completion)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateCompletionError from exc
        await self._session.refresh(completion)
        return completion

    async def get_completions_by_habit_id(self, habit_id: int) -> list[Completion]:
        result = await self._session.execute(
            select(Completion)
            .where(Completion.habit_id == habit_id)
            .order_by(Completion.completion_date.asc())
        )
        return list(result.scalars().all())


def get_completion_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CompletionRepository:
    return CompletionRepository(session)
