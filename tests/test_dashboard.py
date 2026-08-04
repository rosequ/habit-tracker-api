from httpx import AsyncClient


async def test_dashboard_serves_html_with_add_form_and_habit_list(client: AsyncClient) -> None:
    # StaticFiles redirects the extensionless mount root ("/dashboard") to
    # "/dashboard/" (a real browser follows this automatically) before
    # serving index.html for the trailing-slash path.
    response = await client.get("/dashboard", follow_redirects=True)

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert 'id="add-habit-form"' in body
    assert 'id="habit-list"' in body


async def test_dashboard_trailing_slash_also_serves_html(client: AsyncClient) -> None:
    response = await client.get("/dashboard/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
