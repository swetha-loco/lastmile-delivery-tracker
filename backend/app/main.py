from contextlib import asynccontextmanager
from threading import Event, Thread
from types import SimpleNamespace
from typing import Annotated, Callable

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.routers.agent import router as agent_router
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.orders import router as orders_router
from app.worker import run_worker


settings = get_settings()


WorkerRunner = Callable[..., None]


def start_notification_worker(
    app: FastAPI, *, runner: WorkerRunner = run_worker, settings_value: Settings = settings
) -> SimpleNamespace | None:
    if not settings_value.run_notification_worker:
        app.state.notification_worker_running = False
        return None

    stop_event = Event()
    thread = Thread(
        target=runner,
        kwargs={"stop_event": stop_event},
        daemon=True,
        name="notification-worker",
    )
    thread.start()
    app.state.notification_worker_running = True
    return SimpleNamespace(stop_event=stop_event, thread=thread)


def stop_notification_worker(handle: SimpleNamespace | None) -> None:
    if handle is None:
        return
    handle.stop_event.set()
    handle.thread.join(timeout=10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_handle = start_notification_worker(app)
    try:
        yield
    finally:
        stop_notification_worker(worker_handle)


app = FastAPI(title="Last-Mile Delivery Tracker API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(agent_router)
app.include_router(orders_router)


@app.get("/health")
def health(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc

    return {"status": "ok", "database": "ok"}
