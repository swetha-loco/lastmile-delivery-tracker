from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier, Thread
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, or_, select

from app.db import SessionLocal
from app.main import app
from app.models import (
    AgentAvailability,
    AgentProfile,
    DeliveryAttempt,
    DeliveryAttemptStatus,
    Order,
    OrderStatus,
    OrderStatusHistory,
    OrderType,
    OutboxEvent,
    PaymentType,
    RateCard,
    User,
    UserRole,
    Zone,
)
from app.security import hash_password
from app.services import assignment

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_assignment_rows() -> None:
    cleanup()
    yield
    cleanup()


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@assignment-test.com"


def unique_name(prefix: str) -> str:
    return f"Assign{prefix}-{uuid4().hex[:12]}"


def auth_header(user: User, password: str = "password123") -> dict[str, str]:
    response = client.post(
        "/auth/login", data={"username": user.email, "password": password}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_user(
    role: UserRole,
    *,
    availability: AgentAvailability = AgentAvailability.OFFLINE,
    current_zone_id: int | None = None,
    latitude: Decimal | None = None,
    longitude: Decimal | None = None,
    last_assigned_at: datetime | None = None,
) -> User:
    with SessionLocal() as db:
        user = User(
            name=unique_name(role.value),
            email=unique_email(role.value.lower()),
            phone="+15550000000" if role == UserRole.CUSTOMER else None,
            password_hash=hash_password("password123"),
            role=role,
        )
        db.add(user)
        db.flush()
        if role == UserRole.DELIVERY_AGENT:
            db.add(
                AgentProfile(
                    user=user,
                    availability=availability,
                    current_zone_id=current_zone_id,
                    current_latitude=latitude,
                    current_longitude=longitude,
                    last_assigned_at=last_assigned_at,
                )
            )
        db.commit()
        db.refresh(user)
        return user


def create_config() -> dict[str, int]:
    with SessionLocal() as db:
        pickup_zone = Zone(name=unique_name("PickupZone"))
        drop_zone = Zone(name=unique_name("DropZone"))
        db.add_all([pickup_zone, drop_zone])
        db.flush()
        rate_card = RateCard(
            origin_zone=pickup_zone,
            destination_zone=drop_zone,
            order_type=OrderType.B2C,
            rate_per_kg=Decimal("40.00"),
        )
        db.add(rate_card)
        db.commit()
        return {
            "pickup_zone_id": pickup_zone.id,
            "drop_zone_id": drop_zone.id,
            "rate_card_id": rate_card.id,
        }


def create_order(
    *,
    customer_id: int,
    creator_id: int,
    pickup_zone_id: int,
    drop_zone_id: int,
    rate_card_id: int,
    status: OrderStatus = OrderStatus.CREATED,
) -> int:
    with SessionLocal() as db:
        creator = db.get(User, creator_id)
        assert creator is not None
        order = Order(
            customer_id=customer_id,
            created_by_id=creator_id,
            pickup_address="Assignment pickup",
            pickup_postal_code="600001",
            pickup_latitude=Decimal("13.082700"),
            pickup_longitude=Decimal("80.270700"),
            pickup_zone_id=pickup_zone_id,
            drop_address="Assignment drop",
            drop_postal_code="600020",
            drop_latitude=Decimal("13.006700"),
            drop_longitude=Decimal("80.257800"),
            drop_zone_id=drop_zone_id,
            length_cm=Decimal("10.000"),
            breadth_cm=Decimal("10.000"),
            height_cm=Decimal("10.000"),
            actual_weight_kg=Decimal("1.000"),
            volumetric_weight_kg=Decimal("0.200"),
            billable_weight_kg=Decimal("1.000"),
            order_type=OrderType.B2C,
            payment_type=PaymentType.PREPAID,
            rate_card_id=rate_card_id,
            rate_per_kg=Decimal("40.00"),
            delivery_charge=Decimal("40.00"),
            cod_surcharge=Decimal("0.00"),
            total_charge=Decimal("40.00"),
            current_status=status,
        )
        db.add(order)
        db.flush()
        db.add(
            OrderStatusHistory(
                order=order,
                from_status=None,
                to_status=status,
                actor_id=creator_id,
                actor_role=creator.role,
            )
        )
        db.add(
            OutboxEvent(
                event_type="ORDER_CREATED",
                order=order,
                payload={"order_id": order.id, "status": status.value},
            )
        )
        db.commit()
        return order.id


def assignment_setup() -> tuple[User, User, User, dict[str, int], int]:
    ids = create_config()
    admin = create_user(UserRole.ADMIN)
    customer = create_user(UserRole.CUSTOMER)
    agent = create_user(
        UserRole.DELIVERY_AGENT, availability=AgentAvailability.AVAILABLE
    )
    order_id = create_order(
        customer_id=customer.id,
        creator_id=customer.id,
        pickup_zone_id=ids["pickup_zone_id"],
        drop_zone_id=ids["drop_zone_id"],
        rate_card_id=ids["rate_card_id"],
    )
    return admin, customer, agent, ids, order_id


def test_haversine_distance_is_close_to_expected() -> None:
    distance = assignment.haversine_km(
        Decimal("13.082700"),
        Decimal("80.270700"),
        Decimal("13.006700"),
        Decimal("80.257800"),
    )

    assert Decimal("8.0") < distance < Decimal("9.0")


def test_agent_location_and_availability_updates() -> None:
    agent = create_user(UserRole.DELIVERY_AGENT)

    location = client.patch(
        "/agent/location",
        headers=auth_header(agent),
        json={"latitude": "13.082700", "longitude": "80.270700"},
    )
    available = client.patch(
        "/agent/availability",
        headers=auth_header(agent),
        json={"availability": "AVAILABLE"},
    )
    busy = client.patch(
        "/agent/availability",
        headers=auth_header(agent),
        json={"availability": "BUSY"},
    )

    assert location.status_code == 200
    assert location.json()["current_zone_id"] is None
    assert available.status_code == 200
    assert available.json()["availability"] == AgentAvailability.AVAILABLE
    assert busy.status_code == 422


def test_busy_agent_with_active_assignment_cannot_self_release() -> None:
    admin, _, agent, _, order_id = assignment_setup()
    assigned = client.post(
        f"/admin/orders/{order_id}/assign",
        headers=auth_header(admin),
        json={"agent_id": agent.id},
    )

    response = client.patch(
        "/agent/availability",
        headers=auth_header(agent),
        json={"availability": "OFFLINE"},
    )

    assert assigned.status_code == 200
    assert response.status_code == 409


def test_manual_assignment_creates_attempt_history_outbox_and_busy_agent() -> None:
    admin, _, agent, _, order_id = assignment_setup()

    response = client.post(
        f"/admin/orders/{order_id}/assign",
        headers=auth_header(admin),
        json={"agent_id": agent.id},
    )

    assert response.status_code == 200
    assert response.json()["current_status"] == OrderStatus.ASSIGNED
    assert response.json()["current_agent_id"] == agent.id
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        profile = db.get(AgentProfile, agent.id)
        attempt = db.scalar(
            select(DeliveryAttempt).where(DeliveryAttempt.order_id == order_id)
        )
        assigned_history = db.scalar(
            select(OrderStatusHistory).where(
                OrderStatusHistory.order_id == order_id,
                OrderStatusHistory.to_status == OrderStatus.ASSIGNED,
            )
        )
        assigned_event = db.scalar(
            select(OutboxEvent).where(
                OutboxEvent.order_id == order_id,
                OutboxEvent.event_type == "ORDER_ASSIGNED",
            )
        )
        assert order is not None
        assert profile is not None
        assert attempt is not None
        assert attempt.attempt_number == 1
        assert attempt.agent_id == agent.id
        assert attempt.status == DeliveryAttemptStatus.PLANNED
        assert profile.availability == AgentAvailability.BUSY
        assert profile.last_assigned_at is not None
        assert assigned_history is not None
        assert assigned_event is not None


@pytest.mark.parametrize("availability", [AgentAvailability.BUSY, AgentAvailability.OFFLINE])
def test_manual_assignment_rejects_unavailable_agents(
    availability: AgentAvailability,
) -> None:
    admin, _, agent, _, order_id = assignment_setup()
    with SessionLocal() as db:
        profile = db.get(AgentProfile, agent.id)
        assert profile is not None
        profile.availability = availability
        db.commit()

    response = client.post(
        f"/admin/orders/{order_id}/assign",
        headers=auth_header(admin),
        json={"agent_id": agent.id},
    )

    assert response.status_code == 409


def test_auto_assignment_nearest_available_agent_wins_and_excludes_unavailable() -> None:
    ids = create_config()
    admin = create_user(UserRole.ADMIN)
    customer = create_user(UserRole.CUSTOMER)
    far = create_user(
        UserRole.DELIVERY_AGENT,
        availability=AgentAvailability.AVAILABLE,
        latitude=Decimal("12.900000"),
        longitude=Decimal("80.100000"),
    )
    near = create_user(
        UserRole.DELIVERY_AGENT,
        availability=AgentAvailability.AVAILABLE,
        latitude=Decimal("13.082800"),
        longitude=Decimal("80.270800"),
    )
    create_user(
        UserRole.DELIVERY_AGENT,
        availability=AgentAvailability.BUSY,
        latitude=Decimal("13.082700"),
        longitude=Decimal("80.270700"),
    )
    order_id = create_order(
        customer_id=customer.id,
        creator_id=customer.id,
        pickup_zone_id=ids["pickup_zone_id"],
        drop_zone_id=ids["drop_zone_id"],
        rate_card_id=ids["rate_card_id"],
    )

    response = client.post(
        f"/admin/orders/{order_id}/auto-assign", headers=auth_header(admin)
    )

    assert response.status_code == 200
    assert response.json()["current_agent_id"] == near.id
    assert response.json()["current_agent_id"] != far.id


def test_auto_assignment_tie_breaks_by_least_recent_and_id() -> None:
    ids = create_config()
    admin = create_user(UserRole.ADMIN)
    customer = create_user(UserRole.CUSTOMER)
    newer = create_user(
        UserRole.DELIVERY_AGENT,
        availability=AgentAvailability.AVAILABLE,
        latitude=Decimal("13.080000"),
        longitude=Decimal("80.270000"),
        last_assigned_at=datetime.now(UTC),
    )
    older = create_user(
        UserRole.DELIVERY_AGENT,
        availability=AgentAvailability.AVAILABLE,
        latitude=Decimal("13.080000"),
        longitude=Decimal("80.270000"),
        last_assigned_at=datetime.now(UTC) - timedelta(days=1),
    )
    order_id = create_order(
        customer_id=customer.id,
        creator_id=customer.id,
        pickup_zone_id=ids["pickup_zone_id"],
        drop_zone_id=ids["drop_zone_id"],
        rate_card_id=ids["rate_card_id"],
    )

    response = client.post(
        f"/admin/orders/{order_id}/auto-assign", headers=auth_header(admin)
    )

    assert response.status_code == 200
    assert response.json()["current_agent_id"] == older.id
    assert response.json()["current_agent_id"] != newer.id


def test_auto_assignment_zone_fallback_and_no_candidate_no_mutation() -> None:
    ids = create_config()
    admin = create_user(UserRole.ADMIN)
    customer = create_user(UserRole.CUSTOMER)
    zone_agent = create_user(
        UserRole.DELIVERY_AGENT,
        availability=AgentAvailability.AVAILABLE,
        current_zone_id=ids["pickup_zone_id"],
    )
    order_id = create_order(
        customer_id=customer.id,
        creator_id=customer.id,
        pickup_zone_id=ids["pickup_zone_id"],
        drop_zone_id=ids["drop_zone_id"],
        rate_card_id=ids["rate_card_id"],
    )

    assigned = client.post(
        f"/admin/orders/{order_id}/auto-assign", headers=auth_header(admin)
    )

    assert assigned.status_code == 200
    assert assigned.json()["current_agent_id"] == zone_agent.id

    second_order_id = create_order(
        customer_id=customer.id,
        creator_id=customer.id,
        pickup_zone_id=ids["pickup_zone_id"],
        drop_zone_id=ids["drop_zone_id"],
        rate_card_id=ids["rate_card_id"],
    )
    blocked = client.post(
        f"/admin/orders/{second_order_id}/auto-assign", headers=auth_header(admin)
    )

    assert blocked.status_code == 409
    with SessionLocal() as db:
        second = db.get(Order, second_order_id)
        assert second is not None
        assert second.current_status == OrderStatus.CREATED
        assert second.current_agent_id is None


def test_same_agent_cannot_be_assigned_to_two_orders_concurrently() -> None:
    admin, customer, agent, ids, order_id = assignment_setup()
    other_order_id = create_order(
        customer_id=customer.id,
        creator_id=customer.id,
        pickup_zone_id=ids["pickup_zone_id"],
        drop_zone_id=ids["drop_zone_id"],
        rate_card_id=ids["rate_card_id"],
    )
    barrier = Barrier(2)
    results: list[str] = []

    def worker(target_order_id: int) -> None:
        with SessionLocal() as db:
            actor = db.get(User, admin.id)
            assert actor is not None
            barrier.wait()
            try:
                assignment.assign_order_to_agent(
                    db, order_id=target_order_id, agent_id=agent.id, actor=actor
                )
                db.commit()
                results.append("assigned")
            except assignment.AssignmentConflictError:
                db.rollback()
                results.append("conflict")

    threads = [Thread(target=worker, args=(order_id,)), Thread(target=worker, args=(other_order_id,))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == ["assigned", "conflict"]
    with SessionLocal() as db:
        assigned_orders = db.scalars(
            select(Order).where(Order.current_agent_id == agent.id)
        ).all()
        assert len(assigned_orders) == 1


def test_agent_lifecycle_progression_attempts_tracking_and_order_listing() -> None:
    admin, _, agent, _, order_id = assignment_setup()
    assert client.post(
        f"/admin/orders/{order_id}/assign",
        headers=auth_header(admin),
        json={"agent_id": agent.id},
    ).status_code == 200

    invalid_skip = client.patch(
        f"/agent/orders/{order_id}/status",
        headers=auth_header(agent),
        json={"target_status": "DELIVERED"},
    )
    assert invalid_skip.status_code == 409

    for target in ["PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED"]:
        response = client.patch(
            f"/agent/orders/{order_id}/status",
            headers=auth_header(agent),
            json={"target_status": target},
        )
        assert response.status_code == 200
        assert response.json()["current_status"] == target

    with SessionLocal() as db:
        attempt = db.scalar(
            select(DeliveryAttempt).where(DeliveryAttempt.order_id == order_id)
        )
        profile = db.get(AgentProfile, agent.id)
        order = db.get(Order, order_id)
        assert attempt is not None
        assert profile is not None
        assert order is not None
        assert attempt.agent_id == agent.id
        assert attempt.status == DeliveryAttemptStatus.DELIVERED
        assert attempt.started_at is not None
        assert attempt.completed_at is not None
        assert profile.availability == AgentAvailability.AVAILABLE
        assert order.current_agent_id is None

    listing = client.get("/agent/orders", headers=auth_header(agent))
    tracking = client.get(f"/orders/{order_id}/tracking", headers=auth_header(agent))
    events = [
        item["to_status"]
        for item in tracking.json()["history"]
    ]

    assert any(item["id"] == order_id for item in listing.json()["items"])
    assert events == [
        OrderStatus.CREATED,
        OrderStatus.ASSIGNED,
        OrderStatus.PICKED_UP,
        OrderStatus.IN_TRANSIT,
        OrderStatus.OUT_FOR_DELIVERY,
        OrderStatus.DELIVERED,
    ]


def test_wrong_agent_cannot_update_assigned_order() -> None:
    admin, _, agent, _, order_id = assignment_setup()
    other_agent = create_user(UserRole.DELIVERY_AGENT)
    assert client.post(
        f"/admin/orders/{order_id}/assign",
        headers=auth_header(admin),
        json={"agent_id": agent.id},
    ).status_code == 200

    response = client.patch(
        f"/agent/orders/{order_id}/status",
        headers=auth_header(other_agent),
        json={"target_status": "PICKED_UP"},
    )

    assert response.status_code == 404


def test_admin_override_requires_reason_and_maintains_availability() -> None:
    admin, _, agent, _, order_id = assignment_setup()
    assert client.post(
        f"/admin/orders/{order_id}/assign",
        headers=auth_header(admin),
        json={"agent_id": agent.id},
    ).status_code == 200

    missing_reason = client.post(
        f"/admin/orders/{order_id}/override-status",
        headers=auth_header(admin),
        json={"target_status": "DELIVERED", "reason": " "},
    )
    delivered = client.post(
        f"/admin/orders/{order_id}/override-status",
        headers=auth_header(admin),
        json={"target_status": "DELIVERED", "reason": "Customer confirmed delivery"},
    )

    assert missing_reason.status_code == 422
    assert delivered.status_code == 200
    with SessionLocal() as db:
        profile = db.get(AgentProfile, agent.id)
        history = db.scalar(
            select(OrderStatusHistory).where(
                OrderStatusHistory.order_id == order_id,
                OrderStatusHistory.to_status == OrderStatus.DELIVERED,
                OrderStatusHistory.reason == "Customer confirmed delivery",
            )
        )
        event = db.scalar(
            select(OutboxEvent).where(
                OutboxEvent.order_id == order_id,
                OutboxEvent.event_type == "ORDER_DELIVERED",
            )
        )
        assert profile is not None
        assert profile.availability == AgentAvailability.AVAILABLE
        assert history is not None
        assert event is not None


def cleanup() -> None:
    with SessionLocal() as db:
        test_user_ids = select(User.id).where(User.email.endswith("@assignment-test.com"))
        test_zone_ids = select(Zone.id).where(Zone.name.startswith("Assign"))
        test_order_ids = select(Order.id).where(
            or_(
                Order.customer_id.in_(test_user_ids),
                Order.created_by_id.in_(test_user_ids),
                Order.pickup_zone_id.in_(test_zone_ids),
                Order.drop_zone_id.in_(test_zone_ids),
            )
        )
        db.execute(delete(DeliveryAttempt).where(DeliveryAttempt.order_id.in_(test_order_ids)))
        db.execute(delete(OutboxEvent).where(OutboxEvent.order_id.in_(test_order_ids)))
        db.execute(
            delete(OrderStatusHistory).where(OrderStatusHistory.order_id.in_(test_order_ids))
        )
        db.execute(delete(Order).where(Order.id.in_(test_order_ids)))
        db.execute(
            delete(RateCard).where(
                or_(
                    RateCard.origin_zone_id.in_(test_zone_ids),
                    RateCard.destination_zone_id.in_(test_zone_ids),
                )
            )
        )
        db.execute(delete(AgentProfile).where(AgentProfile.user_id.in_(test_user_ids)))
        db.execute(delete(Zone).where(Zone.id.in_(test_zone_ids)))
        db.execute(delete(User).where(User.id.in_(test_user_ids)))
        db.commit()
