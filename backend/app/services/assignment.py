from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from math import asin, cos, radians, sin, sqrt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AgentAvailability,
    AgentProfile,
    DeliveryAttempt,
    DeliveryAttemptStatus,
    Order,
    OrderStatus,
    User,
    UserRole,
)
from app.services import lifecycle


ASSIGNABLE_STATUSES = {OrderStatus.CREATED, OrderStatus.RESCHEDULED}
NEVER_ASSIGNED_AT = datetime(1970, 1, 1, tzinfo=UTC)


class AssignmentConflictError(Exception):
    pass


class AssignmentNotFoundError(Exception):
    pass


def assign_order_to_agent(
    db: Session, *, order_id: int, agent_id: int, actor: User
) -> Order:
    order = lock_order(db, order_id)
    profile = lock_agent_profile(db, agent_id)
    if profile.user.role != UserRole.DELIVERY_AGENT:
        raise AssignmentNotFoundError("Agent not found")
    if profile.availability != AgentAvailability.AVAILABLE:
        raise AssignmentConflictError("Agent is not available")
    assign_locked_order(db, order=order, profile=profile, actor=actor)
    return order


def auto_assign_order(db: Session, *, order_id: int, actor: User) -> Order:
    order = lock_order(db, order_id)
    candidates = ranked_coordinate_candidates(db, order)
    if not candidates:
        candidates = ranked_zone_candidates(db, order)
    for profile in candidates:
        locked = db.scalar(
            select(AgentProfile)
            .where(AgentProfile.user_id == profile.user_id)
            .with_for_update()
        )
        if locked is None or locked.availability != AgentAvailability.AVAILABLE:
            continue
        assign_locked_order(db, order=order, profile=locked, actor=actor)
        return order
    raise AssignmentConflictError("No available agent")


def lock_order(db: Session, order_id: int) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise AssignmentNotFoundError("Order not found")
    if order.current_status not in ASSIGNABLE_STATUSES:
        raise AssignmentConflictError("Order is not assignable")
    if order.current_agent_id is not None:
        raise AssignmentConflictError("Order already has an assigned agent")
    return order


def lock_agent_profile(db: Session, agent_id: int) -> AgentProfile:
    profile = db.scalar(
        select(AgentProfile)
        .where(AgentProfile.user_id == agent_id)
        .with_for_update()
    )
    if profile is None:
        raise AssignmentNotFoundError("Agent not found")
    return profile


def assign_locked_order(
    db: Session, *, order: Order, profile: AgentProfile, actor: User
) -> None:
    attempt = attempt_for_assignment(db, order)
    attempt.agent = profile
    order.current_agent = profile
    profile.availability = AgentAvailability.BUSY
    profile.last_assigned_at = lifecycle.now_utc()
    lifecycle.transition_order(
        db,
        order=order,
        actor=actor,
        target_status=OrderStatus.ASSIGNED,
    )


def attempt_for_assignment(db: Session, order: Order) -> DeliveryAttempt:
    if order.current_status == OrderStatus.CREATED:
        existing = lifecycle.current_attempt(db, order)
        if existing is not None:
            raise AssignmentConflictError("Order already has a delivery attempt")
        attempt = DeliveryAttempt(
            order=order,
            attempt_number=1,
            scheduled_date=datetime.now(UTC).date(),
            status=DeliveryAttemptStatus.PLANNED,
        )
        db.add(attempt)
        db.flush()
        return attempt

    attempt = lifecycle.current_attempt(db, order)
    if (
        attempt is None
        or attempt.status != DeliveryAttemptStatus.PLANNED
        or attempt.agent_id is not None
    ):
        raise AssignmentConflictError("Order has no planned attempt to assign")
    return attempt


def ranked_coordinate_candidates(db: Session, order: Order) -> list[AgentProfile]:
    profiles = db.scalars(
        select(AgentProfile).where(
            AgentProfile.availability == AgentAvailability.AVAILABLE,
            AgentProfile.current_latitude.is_not(None),
            AgentProfile.current_longitude.is_not(None),
        )
    ).all()
    return sorted(
        profiles,
        key=lambda profile: (
            haversine_km(
                profile.current_latitude,
                profile.current_longitude,
                order.pickup_latitude,
                order.pickup_longitude,
            ),
            last_assigned_key(profile),
            profile.user_id,
        ),
    )


def ranked_zone_candidates(db: Session, order: Order) -> list[AgentProfile]:
    profiles = db.scalars(
        select(AgentProfile).where(
            AgentProfile.availability == AgentAvailability.AVAILABLE,
            AgentProfile.current_zone_id == order.pickup_zone_id,
        )
    ).all()
    return sorted(profiles, key=lambda profile: (last_assigned_key(profile), profile.user_id))


def last_assigned_key(profile: AgentProfile) -> datetime:
    return profile.last_assigned_at or NEVER_ASSIGNED_AT


def haversine_km(
    lat1: Decimal, lon1: Decimal, lat2: Decimal, lon2: Decimal
) -> Decimal:
    radius_km = Decimal("6371.0088")
    lat1_r = radians(float(lat1))
    lon1_r = radians(float(lon1))
    lat2_r = radians(float(lat2))
    lon2_r = radians(float(lon2))
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2) ** 2
    return radius_km * Decimal(str(2 * asin(sqrt(a))))
