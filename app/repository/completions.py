from datetime import date
from typing import Annotated

from fastapi import Depends
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


def get_completion_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CompletionRepository:
    return CompletionRepository(session)
