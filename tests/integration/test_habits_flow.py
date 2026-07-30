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


async def test_list_habits_returns_created_habits(client: AsyncClient) -> None:
    empty_response = await client.get("/habits")
    assert empty_response.status_code == 200
    assert empty_response.json() == []

    create_response = await client.post(
        "/habits", json={"name": "Read", "daily_target": 10, "category": "Learning"}
    )
    created = create_response.json()

    list_response = await client.get("/habits")

    assert list_response.status_code == 200
    assert list_response.json() == [created]


async def test_list_completions_for_new_habit_returns_empty_list(client: AsyncClient) -> None:
    create_response = await client.post(
        "/habits", json={"name": "Read", "daily_target": 10, "category": "Learning"}
    )
    created = create_response.json()

    list_response = await client.get(f"/habits/{created['id']}/completions")

    assert list_response.status_code == 200
    assert list_response.json() == []


async def test_create_and_list_completions(client: AsyncClient) -> None:
    create_response = await client.post(
        "/habits", json={"name": "Read", "daily_target": 10, "category": "Learning"}
    )
    habit = create_response.json()

    date1 = "2026-06-01"
    date2 = "2026-06-03"
    date3 = "2026-06-02"

    comp1_response = await client.post(
        f"/habits/{habit['id']}/completions", json={"completion_date": date1}
    )
    comp1 = comp1_response.json()
    assert comp1_response.status_code == 201
    assert comp1["completion_date"] == date1

    comp2_response = await client.post(
        f"/habits/{habit['id']}/completions", json={"completion_date": date2}
    )
    comp2 = comp2_response.json()
    assert comp2_response.status_code == 201
    assert comp2["completion_date"] == date2

    comp3_response = await client.post(
        f"/habits/{habit['id']}/completions", json={"completion_date": date3}
    )
    comp3 = comp3_response.json()
    assert comp3_response.status_code == 201
    assert comp3["completion_date"] == date3

    list_response = await client.get(f"/habits/{habit['id']}/completions")
    assert list_response.status_code == 200
    completions = list_response.json()
    assert len(completions) == 3
    assert completions[0]["completion_date"] == date1
    assert completions[1]["completion_date"] == date3
    assert completions[2]["completion_date"] == date2


async def test_list_completions_for_non_existent_habit_returns_404(client: AsyncClient) -> None:
    response = await client.get("/habits/999999/completions")

    assert response.status_code == 404
