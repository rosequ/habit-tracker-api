from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.habits import HabitCreate, HabitRead
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


@router.get("/{habit_id}", response_model=HabitRead)
async def get_habit(
    habit_id: int,
    service: Annotated[HabitService, Depends(get_habit_service)],
) -> HabitRead:
    habit = await service.get_habit(habit_id)
    if habit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")
    return HabitRead.model_validate(habit)
