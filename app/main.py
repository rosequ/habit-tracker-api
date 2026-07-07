from fastapi import FastAPI

from app.routes.habits import router as habits_router

app = FastAPI(title="Habit Tracker API")

app.include_router(habits_router)
