from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok_when_database_is_available() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
