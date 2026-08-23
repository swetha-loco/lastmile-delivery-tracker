from __future__ import annotations

import time
from threading import Event

from app.db import SessionLocal
from app.services.notifications import process_notification_batch


def process_one_batch(batch_size: int = 20) -> int:
    with SessionLocal() as db:
        return process_notification_batch(db, batch_size=batch_size)


def run_worker(
    *, sleep_seconds: int = 5, batch_size: int = 20, stop_event: Event | None = None
) -> None:
    while stop_event is None or not stop_event.is_set():
        processed = process_one_batch(batch_size=batch_size)
        if processed == 0:
            if stop_event is not None and stop_event.wait(sleep_seconds):
                break
            if stop_event is None:
                time.sleep(sleep_seconds)


if __name__ == "__main__":
    run_worker()
