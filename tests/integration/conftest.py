import os
import signal
import subprocess
import time
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlmodel import SQLModel

import app.db.models  # noqa: F401 ensures SQLModel.metadata is populated for truncation
from app.db.session import async_session_maker

REPO_ROOT = Path(__file__).resolve().parents[2]
STARTUP_TIMEOUT_SECONDS = 15
POLL_INTERVAL_SECONDS = 0.1
SHUTDOWN_TIMEOUT_SECONDS = 5


@pytest.fixture(scope="session")
def live_server() -> Generator[str, None, None]:
    port = int(os.environ["APP_PORT"]) + 1000
    base_url = f"http://127.0.0.1:{port}"

    with httpx.Client() as probe:
        try:
            probe.get(base_url, timeout=1)
            already_running = True
        except httpx.ConnectError:
            already_running = False
    if already_running:
        raise RuntimeError(
            f"Port {port} is already in use — a previous integration test run may "
            f"have crashed and left a process behind. Find and stop it, e.g. "
            f"`lsof -ti:{port} | xargs kill`, then retry."
        )

    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )

    try:
        deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
        ready = False
        with httpx.Client() as client:
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    output = proc.stdout.read() if proc.stdout else ""
                    raise RuntimeError(
                        f"uvicorn subprocess exited early (code {proc.returncode}):\n{output}"
                    )
                try:
                    response = client.get(f"{base_url}/health", timeout=1)
                    if response.status_code == 200:
                        ready = True
                        break
                except (httpx.ConnectError, httpx.ConnectTimeout):
                    pass
                time.sleep(POLL_INTERVAL_SECONDS)

        if not ready:
            output = proc.stdout.read() if proc.stdout else ""
            raise TimeoutError(
                f"Timed out waiting for live server at {base_url} to become healthy:\n{output}"
            )

        yield base_url
    finally:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        try:
            proc.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait()


@pytest_asyncio.fixture(autouse=True)
async def _truncate_all_tables() -> None:
    async with async_session_maker() as session:
        for table in reversed(SQLModel.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


@pytest_asyncio.fixture
async def client(live_server: str) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(base_url=live_server) as ac:
        yield ac
