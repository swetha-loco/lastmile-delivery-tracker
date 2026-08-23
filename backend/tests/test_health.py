from threading import Event
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, start_notification_worker, stop_notification_worker


def test_health_returns_ok_when_database_is_available() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_allows_configured_frontend_origin() -> None:
    client = TestClient(app)

    response = client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_notification_worker_startup_is_opt_in() -> None:
    fake_app = SimpleNamespace(state=SimpleNamespace())
    disabled = Settings(RUN_NOTIFICATION_WORKER=False)

    assert start_notification_worker(fake_app, settings_value=disabled) is None
    assert fake_app.state.notification_worker_running is False

    started = Event()

    def fake_runner(*, stop_event: Event) -> None:
        started.set()
        stop_event.wait(1)

    enabled = Settings(RUN_NOTIFICATION_WORKER=True)
    handle = start_notification_worker(
        fake_app, runner=fake_runner, settings_value=enabled
    )

    try:
        assert handle is not None
        assert started.wait(1)
        assert fake_app.state.notification_worker_running is True
    finally:
        stop_notification_worker(handle)
