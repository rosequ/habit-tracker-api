from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.routes.habits import router as habits_router

app = FastAPI(
    title="Habit Tracker API",
    description="Track habits and their daily completions.",
    version="0.1.0",
)

app.include_router(habits_router)

# Minimal static HTML/JS dashboard (no build step, no framework) that
# exercises POST/GET /habits and POST /habits/{id}/completions from a real
# browser -- see app/static/index.html and issue #36. `html=True` makes
# StaticFiles serve index.html for the mount root itself
# (GET /dashboard -> app/static/index.html), not just for files reachable
# by exact name. Additive only: no new app/routes/ endpoint, no business
# logic -- just serving pre-built static assets, same layering-neutral
# pattern as /health below.
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/dashboard", StaticFiles(directory=STATIC_DIR, html=True), name="dashboard")

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
