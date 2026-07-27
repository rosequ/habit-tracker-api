from app.main import app


def test_app_metadata_includes_description_and_version() -> None:
    assert app.title == "Habit Tracker API"
    assert app.version == "0.1.0"
    assert app.description == "Track habits and their daily completions."
