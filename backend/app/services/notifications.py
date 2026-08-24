from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from html import escape

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


@dataclass(frozen=True)
class EmailMessage:
    subject: str
    text: str
    html: str


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
            log_delivery_result(delivery)
        else:
            delivery.status = NotificationStatus.SENT
            delivery.provider_message_id = result.message_id
            delivery.sent_at = now_utc()
            delivery.next_attempt_at = None
            delivery.last_error = None
            log_delivery_result(delivery)
        processed += 1
    db.commit()
    return processed


def send_delivery(provider: object, delivery: NotificationDelivery) -> ProviderResult:
    if delivery.channel == NotificationChannel.EMAIL:
        message = render_email(delivery.event)
        return provider.send(delivery.recipient, message.subject, message.text, message.html)
    message = render_sms(delivery.event)
    if isinstance(provider, TwilioSmsProvider):
        return provider.send(delivery.recipient, message, event_type=delivery.event.event_type)
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


def log_delivery_result(delivery: NotificationDelivery) -> None:
    message = f"Notification delivery {delivery.id} [{delivery.channel.value}] -> {delivery.status.value}"
    if delivery.status == NotificationStatus.SENT and delivery.provider_message_id:
        message += f" ({delivery.provider_message_id})"
    elif delivery.status in {NotificationStatus.RETRY, NotificationStatus.FAILED} and delivery.last_error:
        message += f": {delivery.last_error}"
    print(message)


def render_email(event: OutboxEvent) -> EmailMessage:
    payload = event.payload
    order = event.order
    order_code = display_order_id(int(payload.get("order_id", event.order_id)))
    copy = event_copy(event.event_type)
    status = human_status(str(payload.get("status", event.event_type)))
    subject = f"{copy['subject']} - {order_code}"

    rows: list[tuple[str, object | None]] = [
        ("Order", order_code),
        ("Status", status),
        ("Pickup", payload.get("pickup_address") or getattr(order, "pickup_address", None)),
        ("Drop", payload.get("drop_address") or getattr(order, "drop_address", None)),
        ("Total", format_money(payload.get("total_charge") or getattr(order, "total_charge", None))),
        ("Assigned agent", assigned_agent_name(order)),
        ("Failure reason", payload.get("reason") if event.event_type == "ORDER_FAILED" else None),
        (
            "Scheduled date",
            payload.get("scheduled_date") if event.event_type == "ORDER_RESCHEDULED" else None,
        ),
    ]
    visible_rows = [(label, value) for label, value in rows if value not in (None, "")]

    text_lines = [
        "Last-Mile Delivery Tracker",
        "",
        str(copy["heading"]),
        str(copy["body"]),
        "",
    ]
    for label, value in visible_rows:
        text_lines.extend([str(label), str(value), ""])
    text_lines.append(str(copy["footer"]))

    html_rows = "\n".join(
        f"""
        <tr>
          <td style="padding:12px 0;color:#667085;font-size:13px;font-weight:700;width:34%;vertical-align:top;">{escape(label)}</td>
          <td style="padding:12px 0;color:#142033;font-size:14px;font-weight:700;line-height:1.45;vertical-align:top;">{escape(str(value))}</td>
        </tr>
        """
        for label, value in visible_rows
    )
    html = f"""<!doctype html>
<html>
  <body style="margin:0;background:#F7F8F6;font-family:Manrope,Arial,sans-serif;color:#142033;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#F7F8F6;padding:24px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#FFFFFF;border:1px solid #DDE5E1;border-radius:14px;overflow:hidden;">
            <tr>
              <td style="background:#071D34;padding:22px 24px;color:#FFFFFF;">
                <div style="font-size:16px;font-weight:800;letter-spacing:.01em;">Last-Mile Delivery Tracker</div>
              </td>
            </tr>
            <tr>
              <td style="padding:28px 24px 8px;">
                <div style="display:inline-block;height:4px;width:42px;background:#F25F3A;border-radius:999px;margin-bottom:18px;"></div>
                <h1 style="margin:0;color:#071D34;font-size:24px;line-height:1.25;font-weight:800;">{escape(str(copy["heading"]))}</h1>
                <p style="margin:10px 0 0;color:#667085;font-size:15px;line-height:1.6;">{escape(str(copy["body"]))}</p>
              </td>
            </tr>
            <tr>
              <td style="padding:8px 24px 24px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-top:1px solid #DDE5E1;border-bottom:1px solid #DDE5E1;">
                  {html_rows}
                </table>
                <p style="margin:20px 0 0;color:#667085;font-size:14px;line-height:1.6;">{escape(str(copy["footer"]))}</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""
    return EmailMessage(subject=subject, text="\n".join(text_lines), html=html)


def render_sms(event: OutboxEvent) -> str:
    order_code = display_order_id(int(event.payload.get("order_id", event.order_id)))
    messages = {
        "ORDER_CREATED": f"Last-Mile: Order {order_code} created successfully. We'll keep you updated.",
        "ORDER_ASSIGNED": f"Last-Mile: Agent assigned to order {order_code}.",
        "ORDER_PICKED_UP": f"Last-Mile: Order {order_code} has been picked up.",
        "ORDER_IN_TRANSIT": f"Last-Mile: Order {order_code} is in transit.",
        "ORDER_OUT_FOR_DELIVERY": f"Last-Mile: Order {order_code} is out for delivery.",
        "ORDER_DELIVERED": f"Last-Mile: Order {order_code} has been delivered.",
        "ORDER_FAILED": f"Last-Mile: Delivery attempt for {order_code} failed. Open the app to reschedule.",
        "ORDER_RESCHEDULED": f"Last-Mile: Order {order_code} has been rescheduled.",
    }
    return messages.get(
        event.event_type,
        f"Last-Mile: Order {order_code} status is {human_status(str(event.payload.get('status', event.event_type)))}.",
    )


def twilio_trial_template(event_type: str) -> str:
    if event_type == "ORDER_CREATED":
        return "sms_order_confirmation"
    return "sms_delivery_updates"


def human_status(value: str) -> str:
    return value.replace("ORDER_", "").replace("_", " ").title()


def display_order_id(order_id: int) -> str:
    return f"LM-{order_id:05d}"


def format_money(value: object | None) -> str | None:
    if value is None:
        return None
    return f"Rs. {value}"


def assigned_agent_name(order: Order | None) -> str | None:
    if order is None or order.current_agent is None:
        return None
    return order.current_agent.user.name


def event_copy(event_type: str) -> dict[str, str]:
    copy = {
        "ORDER_CREATED": {
            "subject": "Your delivery has been created",
            "heading": "Your delivery has been created",
            "body": "We have received your delivery request.",
        },
        "ORDER_ASSIGNED": {
            "subject": "An agent has been assigned",
            "heading": "An agent has been assigned to your delivery",
            "body": "Your delivery is now assigned and ready for pickup.",
        },
        "ORDER_PICKED_UP": {
            "subject": "Your parcel has been picked up",
            "heading": "Your parcel has been picked up",
            "body": "Your parcel is now with the delivery agent.",
        },
        "ORDER_IN_TRANSIT": {
            "subject": "Your delivery is on the way",
            "heading": "Your delivery is on the way",
            "body": "Your parcel is moving through the delivery route.",
        },
        "ORDER_OUT_FOR_DELIVERY": {
            "subject": "Your delivery is out for delivery",
            "heading": "Your delivery is out for delivery",
            "body": "Your parcel is on its final delivery leg.",
        },
        "ORDER_DELIVERED": {
            "subject": "Your delivery has been delivered",
            "heading": "Your delivery has been delivered",
            "body": "This delivery has been completed.",
            "footer": "Thank you for using Last-Mile Delivery Tracker.",
        },
        "ORDER_FAILED": {
            "subject": "Delivery attempt could not be completed",
            "heading": "We couldn't complete this delivery attempt",
            "body": "Please review the attempt details and reschedule from the app when ready.",
        },
        "ORDER_RESCHEDULED": {
            "subject": "Your delivery has been rescheduled",
            "heading": "Your delivery has been rescheduled",
            "body": "We will prepare a new delivery attempt for the selected date.",
        },
    }
    default = {
        "subject": "Your delivery status has changed",
        "heading": "Your delivery status has changed",
        "body": "We have an update on your delivery.",
    }
    selected = {**default, **copy.get(event_type, {})}
    selected.setdefault("footer", "We'll keep you updated as your delivery progresses.")
    return selected


def provider_error_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        body = response.text.strip()
        return body[:300] if body else response.reason_phrase
    if isinstance(data, dict):
        code = data.get("code") or data.get("error_code")
        message = data.get("message") or data.get("error") or data.get("detail")
        if code and message:
            return f"{code}: {message}"
        if message:
            return str(message)
    return response.reason_phrase


class ResendEmailProvider:
    def send(
        self, recipient: str, subject: str, text_body: str, html_body: str
    ) -> ProviderResult:
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
                    "text": text_body,
                    "html": html_body,
                },
                timeout=10,
            )
        except httpx.RequestError as exc:
            raise ProviderSendError(f"Resend request failed: {exc.__class__.__name__}") from exc
        if response.status_code >= 400:
            raise ProviderSendError(
                f"Resend send failed ({response.status_code}): {provider_error_detail(response)}"
            )
        data = response.json()
        message_id = data.get("id") if isinstance(data, dict) else None
        return ProviderResult(message_id=message_id)


class TwilioSmsProvider:
    def send(
        self, recipient: str, message: str, *, event_type: str | None = None
    ) -> ProviderResult:
        settings = get_settings()
        if (
            not settings.twilio_account_sid
            or not settings.twilio_auth_token
            or (not settings.twilio_trial_mode and not settings.twilio_from_number)
        ):
            raise ProviderSendError("Twilio configuration is missing")
        data = {
            "To": recipient,
            "Body": twilio_trial_template(event_type or "")
            if settings.twilio_trial_mode
            else message,
        }
        if not settings.twilio_trial_mode:
            data["From"] = settings.twilio_from_number
        try:
            response = httpx.post(
                f"https://api.twilio.com/2010-04-01/Accounts/"
                f"{settings.twilio_account_sid}/Messages.json",
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                data=data,
                timeout=10,
            )
        except httpx.RequestError as exc:
            raise ProviderSendError(f"Twilio request failed: {exc.__class__.__name__}") from exc
        if response.status_code >= 400:
            raise ProviderSendError(
                f"Twilio send failed ({response.status_code}): {provider_error_detail(response)}"
            )
        data = response.json()
        message_id = data.get("sid") if isinstance(data, dict) else None
        return ProviderResult(message_id=message_id)
