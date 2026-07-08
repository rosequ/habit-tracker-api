from datetime import date, datetime

from pydantic import BaseModel


class CompletionCreate(BaseModel):
    completion_date: date | None = None


class CompletionRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    habit_id: int
    completion_date: date
    created_at: datetime
