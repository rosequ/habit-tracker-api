from datetime import datetime

from pydantic import BaseModel, Field


class HabitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    daily_target: int = Field(gt=0)
    category: str = Field(min_length=1, max_length=50)


class HabitRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    daily_target: int
    category: str
    created_at: datetime
