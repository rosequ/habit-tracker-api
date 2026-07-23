from httpx import AsyncClient


async def test_create_habit_returns_201_and_persists(client: AsyncClient) -> None:
    payload = {"name": "Read", "daily_target": 10, "category": "Learning"}

    create_response = await client.post("/habits", json=payload)

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == payload["name"]
    assert created["daily_target"] == payload["daily_target"]
    assert created["category"] == payload["category"]
    assert "id" in created
    assert "created_at" in created

    get_response = await client.get(f"/habits/{created['id']}")

    assert get_response.status_code == 200
    assert get_response.json() == created


async def test_create_habit_with_invalid_payload_returns_422(client: AsyncClient) -> None:
    payload = {"name": "", "daily_target": 10, "category": "Learning"}

    response = await client.post("/habits", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert any(error["loc"][-1] == "name" for error in body["detail"])


async def test_get_missing_habit_returns_404(client: AsyncClient) -> None:
    response = await client.get("/habits/999999")

    assert response.status_code == 404


async def test_list_habits_returns_empty_list_when_none_exist(client: AsyncClient) -> None:
    response = await client.get("/habits")

    assert response.status_code == 200
    assert response.json() == []


async def test_list_habits_returns_all_habits_ordered_by_id(client: AsyncClient) -> None:
    first = await client.post(
        "/habits", json={"name": "Read", "daily_target": 10, "category": "Learning"}
    )
    second = await client.post(
        "/habits", json={"name": "Run", "daily_target": 1, "category": "Fitness"}
    )

    response = await client.get("/habits")

    assert response.status_code == 200
    body = response.json()
    assert [habit["id"] for habit in body] == [
        first.json()["id"],
        second.json()["id"],
    ]
