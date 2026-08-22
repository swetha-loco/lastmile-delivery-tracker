from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import httpx
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    NotificationChannel,
    NotificationDelivery,
    NotificationStatus,
    Order,
    OutboxEvent,
)
from app.services.lifecycle_time import now_utc


MAX_SEND_ATTEMPTS = 5
RETRY_DELAYS = [
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(minutes=60),
]


@dataclass(frozen=True)
class ProviderResult:
    message_id: str | None = None


class ProviderSendError(Exception):
    pass


def create_order_event(
    db: Session,
    *,
    order: Order,
    event_type: str,
    payload: dict[str, object],
) -> OutboxEvent:
    event = OutboxEvent(event_type=event_type, order=order, payload=payload)
    db.add(event)
    db.flush()
    customer = order.customer
    if customer.email:
        db.add(
            NotificationDelivery(
                event=event,
                channel=NotificationChannel.EMAIL,
                recipient=customer.email,
                status=NotificationStatus.PENDING,
            )
        )
    if customer.phone:
        db.add(
            NotificationDelivery(
                event=event,
                channel=NotificationChannel.SMS,
                recipient=customer.phone,
                status=NotificationStatus.PENDING,
            )
        )
    db.flush()
    return event


def process_notification_batch(
    db: Session,
    *,
    email_provider: object | None = None,
    sms_provider: object | None = None,
    batch_size: int = 20,
) -> int:
    due_at = now_utc()
    deliveries = db.scalars(
        select(NotificationDelivery)
        .where(
            or_(
                NotificationDelivery.status == NotificationStatus.PENDING,
                and_(
                    NotificationDelivery.status == NotificationStatus.RETRY,
                    NotificationDelivery.next_attempt_at <= due_at,
                ),
            )
        )
        .order_by(NotificationDelivery.id)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    ).all()

    processed = 0
    email_provider = email_provider or ResendEmailProvider()
    sms_provider = sms_provider or TwilioSmsProvider()
    for delivery in deliveries:
        if delivery.status == NotificationStatus.SENT:
            continue
        provider = email_provider if delivery.channel == NotificationChannel.EMAIL else sms_provider
        try:
            delivery.attempt_count += 1
            result = send_delivery(provider, delivery)
        except ProviderSendError as exc:
            mark_failed_attempt(delivery, str(exc))
        else:
            delivery.status = NotificationStatus.SENT
            delivery.provider_message_id = result.message_id
            delivery.sent_at = now_utc()
            delivery.next_attempt_at = None
            delivery.last_error = None
        processed += 1
    db.commit()
    return processed


def send_delivery(provider: object, delivery: NotificationDelivery) -> ProviderResult:
    if delivery.channel == NotificationChannel.EMAIL:
        subject, body = render_email(delivery.event)
        return provider.send(delivery.recipient, subject, body)
    message = render_sms(delivery.event)
    return provider.send(delivery.recipient, message)


def mark_failed_attempt(delivery: NotificationDelivery, error: str) -> None:
    delivery.last_error = error[:1000]
    delivery.provider_message_id = None
    delivery.sent_at = None
    if delivery.attempt_count >= MAX_SEND_ATTEMPTS:
        delivery.status = NotificationStatus.FAILED
        delivery.next_attempt_at = None
        return
    delivery.status = NotificationStatus.RETRY
    delivery.next_attempt_at = now_utc() + RETRY_DELAYS[delivery.attempt_count - 1]


def render_email(event: OutboxEvent) -> tuple[str, str]:
    order_id = event.payload.get("order_id", event.order_id)
    status = human_status(str(event.payload.get("status", event.event_type)))
    subject = f"Order #{order_id} status: {status}"
    lines = [
        f"Your order #{order_id} status is now {status}.",
        f"Event: {event.event_type}",
    ]
    if event.payload.get("total_charge") is not None:
        lines.append(f"Total charge: {event.payload['total_charge']}")
    if event.payload.get("reason"):
        lines.append(f"Reason: {event.payload['reason']}")
    if event.payload.get("scheduled_date"):
        lines.append(f"New scheduled date: {event.payload['scheduled_date']}")
    return subject, "\n".join(lines)


def render_sms(event: OutboxEvent) -> str:
    order_id = event.payload.get("order_id", event.order_id)
    status = human_status(str(event.payload.get("status", event.event_type)))
    message = f"Order #{order_id}: {status}."
    if event.payload.get("scheduled_date"):
        message += f" Scheduled {event.payload['scheduled_date']}."
    if event.payload.get("reason") and event.event_type == "ORDER_FAILED":
        message += f" Reason: {event.payload['reason']}."
    return message


def human_status(value: str) -> str:
    return value.replace("ORDER_", "").replace("_", " ").title()


class ResendEmailProvider:
    def send(self, recipient: str, subject: str, body: str) -> ProviderResult:
        settings = get_settings()
        if not settings.resend_api_key or not settings.email_from:
            raise ProviderSendError("Resend configuration is missing")
        try:
            response = httpx.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.email_from,
                    "to": [recipient],
                    "subject": subject,
                    "text": body,
                },
                timeout=10,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderSendError("Resend send failed") from exc
        data = response.json()
        message_id = data.get("id") if isinstance(data, dict) else None
        return ProviderResult(message_id=message_id)


class TwilioSmsProvider:
    def send(self, recipient: str, message: str) -> ProviderResult:
        settings = get_settings()
        if (
            not settings.twilio_account_sid
            or not settings.twilio_auth_token
            or not settings.twilio_from_number
        ):
            raise ProviderSendError("Twilio configuration is missing")
        try:
            response = httpx.post(
                f"https://api.twilio.com/2010-04-01/Accounts/"
                f"{settings.twilio_account_sid}/Messages.json",
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                data={
                    "From": settings.twilio_from_number,
                    "To": recipient,
                    "Body": message,
                },
                timeout=10,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderSendError("Twilio send failed") from exc
        data = response.json()
        message_id = data.get("sid") if isinstance(data, dict) else None
        return ProviderResult(message_id=message_id)
