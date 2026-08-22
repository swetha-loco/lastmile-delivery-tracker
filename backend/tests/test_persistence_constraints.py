from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    AgentProfile,
    Area,
    CodSurcharge,
    DeliveryAttempt,
    DeliveryAttemptStatus,
    NotificationChannel,
    NotificationDelivery,
    NotificationStatus,
    Order,
    OrderStatus,
    OrderType,
    OutboxEvent,
    PaymentType,
    RateCard,
    User,
    UserRole,
    Zone,
)


@pytest.fixture
def db_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def make_user(role: UserRole = UserRole.CUSTOMER) -> User:
    suffix = uuid4().hex
    return User(
        name=f"User {suffix}",
        email=f"{suffix}@example.com",
        password_hash="not-a-real-hash-yet",
        role=role,
    )


def make_zone() -> Zone:
    return Zone(name=unique("Zone"))


def make_order(db: Session) -> Order:
    customer = make_user()
    zone = make_zone()
    rate_card = RateCard(
        origin_zone=zone,
        destination_zone=zone,
        order_type=OrderType.B2C,
        rate_per_kg=Decimal("40.00"),
    )
    order = Order(
        customer=customer,
        creator=customer,
        pickup_address="Demo pickup",
        pickup_postal_code="DEMO1001",
        pickup_latitude=Decimal("12.971600"),
        pickup_longitude=Decimal("77.594600"),
        pickup_zone=zone,
        drop_address="Demo drop",
        drop_postal_code="DEMO1002",
        drop_latitude=Decimal("12.972000"),
        drop_longitude=Decimal("77.595000"),
        drop_zone=zone,
        length_cm=Decimal("10.000"),
        breadth_cm=Decimal("10.000"),
        height_cm=Decimal("10.000"),
        actual_weight_kg=Decimal("1.000"),
        volumetric_weight_kg=Decimal("0.200"),
        billable_weight_kg=Decimal("1.000"),
        order_type=OrderType.B2C,
        payment_type=PaymentType.PREPAID,
        rate_card=rate_card,
        rate_per_kg=Decimal("40.00"),
        delivery_charge=Decimal("40.00"),
        cod_surcharge=Decimal("0.00"),
        total_charge=Decimal("40.00"),
        current_status=OrderStatus.CREATED,
    )
    db.add(order)
    db.flush()
    return order


def test_duplicate_user_email_rejected(db_session: Session) -> None:
    email = f"{uuid4().hex}@example.com"
    db_session.add_all(
        [
            User(
                name="First",
                email=email,
                password_hash="hash",
                role=UserRole.CUSTOMER,
            ),
            User(
                name="Second",
                email=email,
                password_hash="hash",
                role=UserRole.CUSTOMER,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_area_postal_code_rejected(db_session: Session) -> None:
    zone = make_zone()
    postal_code = f"D{uuid4().hex[:12]}"
    db_session.add_all(
        [
            zone,
            Area(name="First", postal_code=postal_code, zone=zone),
            Area(name="Second", postal_code=postal_code, zone=zone),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_rate_card_rejected(db_session: Session) -> None:
    zone = make_zone()
    db_session.add(zone)
    db_session.flush()
    db_session.add_all(
        [
            RateCard(
                origin_zone=zone,
                destination_zone=zone,
                order_type=OrderType.B2B,
                rate_per_kg=Decimal("35.00"),
            ),
            RateCard(
                origin_zone=zone,
                destination_zone=zone,
                order_type=OrderType.B2B,
                rate_per_kg=Decimal("36.00"),
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_non_positive_rate_rejected(db_session: Session) -> None:
    zone = make_zone()
    db_session.add(
        RateCard(
            origin_zone=zone,
            destination_zone=zone,
            order_type=OrderType.B2B,
            rate_per_kg=Decimal("0.00"),
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_cod_order_type_rejected(db_session: Session) -> None:
    db_session.add_all(
        [
            CodSurcharge(order_type=OrderType.B2B, amount=Decimal("10.00")),
            CodSurcharge(order_type=OrderType.B2B, amount=Decimal("12.00")),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_negative_cod_surcharge_rejected(db_session: Session) -> None:
    surcharge = db_session.scalar(
        select(CodSurcharge).where(CodSurcharge.order_type == OrderType.B2C)
    )
    if surcharge is None:
        surcharge = CodSurcharge(order_type=OrderType.B2C, amount=Decimal("1.00"))
        db_session.add(surcharge)
        db_session.flush()

    surcharge.amount = Decimal("-1.00")

    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (Decimal("91.000000"), Decimal("77.000000")),
        (Decimal("12.000000"), Decimal("181.000000")),
        (Decimal("12.000000"), None),
    ],
)
def test_invalid_agent_coordinates_rejected(
    db_session: Session, latitude: Decimal | None, longitude: Decimal | None
) -> None:
    agent = make_user(UserRole.DELIVERY_AGENT)
    db_session.add(
        AgentProfile(
            user=agent,
            current_latitude=latitude,
            current_longitude=longitude,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_invalid_order_dimension_rejected(db_session: Session) -> None:
    order = make_order(db_session)
    order.length_cm = Decimal("0.000")

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_delivery_attempt_number_rejected(db_session: Session) -> None:
    order = make_order(db_session)
    db_session.add_all(
        [
            DeliveryAttempt(
                order=order,
                attempt_number=1,
                scheduled_date=date.today(),
                status=DeliveryAttemptStatus.PLANNED,
            ),
            DeliveryAttempt(
                order=order,
                attempt_number=1,
                scheduled_date=date.today(),
                status=DeliveryAttemptStatus.PLANNED,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_notification_delivery_channel_rejected(db_session: Session) -> None:
    order = make_order(db_session)
    event = OutboxEvent(
        event_type="order.status_changed",
        order=order,
        payload={"order_id": order.id},
    )
    db_session.add_all(
        [
            event,
            NotificationDelivery(
                event=event,
                channel=NotificationChannel.EMAIL,
                recipient="customer@example.com",
                status=NotificationStatus.PENDING,
            ),
            NotificationDelivery(
                event=event,
                channel=NotificationChannel.EMAIL,
                recipient="customer@example.com",
                status=NotificationStatus.PENDING,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()
