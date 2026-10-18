from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.completions import CompletionCreate, CompletionRead
from app.schemas.habits import HabitCreate, HabitRead
from app.services.completions import (
    CompletionService,
    DuplicateCompletionError,
    FutureCompletionDateError,
    HabitNotFoundError,
    get_completion_service,
)
from app.services.habits import HabitService, get_habit_service

router = APIRouter(prefix="/habits", tags=["habits"])


@router.post("", response_model=HabitRead, status_code=status.HTTP_201_CREATED)
async def create_habit(
    payload: HabitCreate,
    service: Annotated[HabitService, Depends(get_habit_service)],
) -> HabitRead:
    habit = await service.create_habit(
        name=payload.name,
        daily_target=payload.daily_target,
        category=payload.category,
    )
    return HabitRead.model_validate(habit)


@router.get("", response_model=list[HabitRead])
async def list_habits(
    service: Annotated[HabitService, Depends(get_habit_service)],
) -> list[HabitRead]:
    habits = await service.list_habits()
    return [HabitRead.model_validate(habit) for habit in habits]


@router.get("/{habit_id}", response_model=HabitRead)
async def get_habit(
    habit_id: int,
    service: Annotated[HabitService, Depends(get_habit_service)],
) -> HabitRead:
    habit = await service.get_habit(habit_id)
    if habit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")
    return HabitRead.model_validate(habit)


@router.post(
    "/{habit_id}/completions",
    response_model=CompletionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_completion(
    habit_id: int,
    payload: CompletionCreate,
    service: Annotated[CompletionService, Depends(get_completion_service)],
) -> CompletionRead:
    try:
        completion = await service.create_completion(
            habit_id=habit_id, completion_date=payload.completion_date
        )
    except HabitNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found") from exc
    except FutureCompletionDateError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Completion date cannot be in the future",
        ) from exc
    except DuplicateCompletionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completion already recorded for this habit and date",
        ) from exc
    return CompletionRead.model_validate(completion)


@router.get(
    "/{habit_id}/completions",
    response_model=list[CompletionRead],
)
async def list_completions(
    habit_id: int,
    service: Annotated[CompletionService, Depends(get_completion_service)],
) -> list[CompletionRead]:
    try:
        completions = await service.get_completions(habit_id)
    except HabitNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")
    return [CompletionRead.model_validate(c) for c in completions]
