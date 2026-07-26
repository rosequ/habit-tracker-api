from typing import Annotated

from fastapi import Depends, FastAPI
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.routes.habits import router as habits_router

app = FastAPI(title="Habit Tracker API")

app.include_router(habits_router)

# metrics.default() bundles request count with latency, but hardcodes
# latency's labels to (method, handler) only -- no status -- to avoid a
# histogram-bucket x status-code cardinality blow-up. We want status on
# both, so request count and latency are added individually instead; both
# default to (method, handler, status).
Instrumentator().add(metrics.requests()).add(metrics.latency()).instrument(app).expose(app)


@app.get("/health")
async def health(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "version": "0.1.0"}
