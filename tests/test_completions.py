from datetime import date, timedelta

from httpx import AsyncClient


async def _create_habit(client: AsyncClient) -> int:
    payload = {"name": "Read", "daily_target": 10, "category": "Learning"}
    response = await client.post("/habits", json=payload)
    return response.json()["id"]


async def _create_completion(client: AsyncClient, habit_id: int, date_str: str) -> dict:
    response = await client.post(
        f"/habits/{habit_id}/completions", json={"completion_date": date_str}
    )
    return response.json()


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


async def test_list_completions_returns_empty_list_for_new_habit(client: AsyncClient) -> None:
    habit_id = await _create_habit(client)

    response = await client.get(f"/habits/{habit_id}/completions")

    assert response.status_code == 200
    assert response.json() == []


async def test_list_completions_returns_ordered_completions(client: AsyncClient) -> None:
    habit_id = await _create_habit(client)

    date1 = "2026-06-01"
    date2 = "2026-06-03"
    date3 = "2026-06-02"

    await _create_completion(client, habit_id, date1)
    await _create_completion(client, habit_id, date2)
    await _create_completion(client, habit_id, date3)

    response = await client.get(f"/habits/{habit_id}/completions")

    assert response.status_code == 200
    completions = response.json()
    assert len(completions) == 3
    assert completions[0]["completion_date"] == date1
    assert completions[1]["completion_date"] == date3
    assert completions[2]["completion_date"] == date2


async def test_list_completions_for_missing_habit_returns_404(client: AsyncClient) -> None:
    response = await client.get("/habits/999999/completions")

    assert response.status_code == 404
