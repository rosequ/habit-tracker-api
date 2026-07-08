from datetime import date, timedelta

from httpx import AsyncClient


async def _create_habit(client: AsyncClient) -> int:
    payload = {"name": "Read", "daily_target": 10, "category": "Learning"}
    response = await client.post("/habits", json=payload)
    return response.json()["id"]


async def test_create_completion_with_explicit_date_returns_201(client: AsyncClient) -> None:
    habit_id = await _create_habit(client)

    response = await client.post(
        f"/habits/{habit_id}/completions", json={"completion_date": "2026-07-01"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["habit_id"] == habit_id
    assert body["completion_date"] == "2026-07-01"
    assert "id" in body
    assert "created_at" in body


async def test_create_completion_without_date_defaults_to_today(client: AsyncClient) -> None:
    habit_id = await _create_habit(client)

    response = await client.post(f"/habits/{habit_id}/completions", json={})

    assert response.status_code == 201
    assert response.json()["completion_date"] == date.today().isoformat()


async def test_duplicate_completion_returns_409(client: AsyncClient) -> None:
    habit_id = await _create_habit(client)
    payload = {"completion_date": "2026-07-01"}

    first = await client.post(f"/habits/{habit_id}/completions", json=payload)
    second = await client.post(f"/habits/{habit_id}/completions", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


async def test_future_completion_date_returns_422(client: AsyncClient) -> None:
    habit_id = await _create_habit(client)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    response = await client.post(
        f"/habits/{habit_id}/completions", json={"completion_date": tomorrow}
    )

    assert response.status_code == 422


async def test_completion_for_missing_habit_returns_404(client: AsyncClient) -> None:
    response = await client.post("/habits/999999/completions", json={})

    assert response.status_code == 404
