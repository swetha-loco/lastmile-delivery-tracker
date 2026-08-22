from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AgentAvailability,
    DeliveryAttempt,
    DeliveryAttemptStatus,
    Order,
    OrderStatus,
    OrderStatusHistory,
    OutboxEvent,
    User,
)


NORMAL_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.CREATED: {OrderStatus.ASSIGNED},
    OrderStatus.RESCHEDULED: {OrderStatus.ASSIGNED},
    OrderStatus.ASSIGNED: {OrderStatus.PICKED_UP},
    OrderStatus.PICKED_UP: {OrderStatus.IN_TRANSIT},
    OrderStatus.IN_TRANSIT: {OrderStatus.OUT_FOR_DELIVERY},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED},
}

AGENT_TARGET_STATUSES = {
    OrderStatus.PICKED_UP,
    OrderStatus.IN_TRANSIT,
    OrderStatus.OUT_FOR_DELIVERY,
    OrderStatus.DELIVERED,
}

EVENT_TYPES: dict[OrderStatus, str] = {
    OrderStatus.ASSIGNED: "ORDER_ASSIGNED",
    OrderStatus.PICKED_UP: "ORDER_PICKED_UP",
    OrderStatus.IN_TRANSIT: "ORDER_IN_TRANSIT",
    OrderStatus.OUT_FOR_DELIVERY: "ORDER_OUT_FOR_DELIVERY",
    OrderStatus.DELIVERED: "ORDER_DELIVERED",
    OrderStatus.CREATED: "ORDER_STATUS_OVERRIDDEN",
    OrderStatus.RESCHEDULED: "ORDER_STATUS_OVERRIDDEN",
}


class LifecycleConflictError(Exception):
    pass


def transition_order(
    db: Session,
    *,
    order: Order,
    actor: User,
    target_status: OrderStatus,
    reason: str | None = None,
    override: bool = False,
) -> None:
    if override:
        apply_override_consistency(db, order=order, target_status=target_status)
    else:
        allowed_targets = NORMAL_TRANSITIONS.get(order.current_status, set())
        if target_status not in allowed_targets:
            raise LifecycleConflictError("Invalid status transition")
        apply_normal_attempt_changes(db, order=order, target_status=target_status)

    from_status = order.current_status
    order.current_status = target_status
    db.add(
        OrderStatusHistory(
            order=order,
            from_status=from_status,
            to_status=target_status,
            actor_id=actor.id,
            actor_role=actor.role,
            reason=reason,
        )
    )
    db.add(
        OutboxEvent(
            event_type=EVENT_TYPES.get(target_status, "ORDER_STATUS_OVERRIDDEN"),
            order=order,
            payload={
                "order_id": order.id,
                "customer_id": order.customer_id,
                "status": target_status.value,
                "actor_id": actor.id,
                "actor_role": actor.role.value,
            },
        )
    )
    db.flush()


def apply_normal_attempt_changes(
    db: Session, *, order: Order, target_status: OrderStatus
) -> None:
    if target_status == OrderStatus.PICKED_UP:
        attempt = require_current_attempt(db, order)
        attempt.status = DeliveryAttemptStatus.IN_PROGRESS
        if attempt.started_at is None:
            attempt.started_at = now_utc()
    elif target_status == OrderStatus.DELIVERED:
        attempt = require_current_attempt(db, order)
        attempt.status = DeliveryAttemptStatus.DELIVERED
        attempt.completed_at = now_utc()
        release_current_agent(order)


def apply_override_consistency(
    db: Session, *, order: Order, target_status: OrderStatus
) -> None:
    if target_status == OrderStatus.FAILED:
        raise LifecycleConflictError("Failed delivery handling is not implemented yet")

    attempt = current_attempt(db, order)
    if target_status in {
        OrderStatus.PICKED_UP,
        OrderStatus.IN_TRANSIT,
        OrderStatus.OUT_FOR_DELIVERY,
    }:
        if order.current_agent is None or attempt is None:
            raise LifecycleConflictError("Order has no active assigned attempt")
        order.current_agent.availability = AgentAvailability.BUSY
        attempt.status = DeliveryAttemptStatus.IN_PROGRESS
        if attempt.started_at is None:
            attempt.started_at = now_utc()
    elif target_status == OrderStatus.DELIVERED:
        if attempt is not None:
            attempt.status = DeliveryAttemptStatus.DELIVERED
            attempt.completed_at = now_utc()
        release_current_agent(order)
    elif target_status in {OrderStatus.CREATED, OrderStatus.RESCHEDULED}:
        release_current_agent(order)
    elif target_status == OrderStatus.ASSIGNED:
        if order.current_agent is None:
            raise LifecycleConflictError("Assigned status requires an assigned agent")
        order.current_agent.availability = AgentAvailability.BUSY
        if attempt is None:
            raise LifecycleConflictError("Assigned status requires a delivery attempt")
        attempt.status = DeliveryAttemptStatus.PLANNED


def current_attempt(db: Session, order: Order) -> DeliveryAttempt | None:
    return db.scalar(
        select(DeliveryAttempt)
        .where(DeliveryAttempt.order_id == order.id)
        .order_by(DeliveryAttempt.attempt_number.desc())
        .limit(1)
    )


def require_current_attempt(db: Session, order: Order) -> DeliveryAttempt:
    attempt = current_attempt(db, order)
    if attempt is None or attempt.agent_id != order.current_agent_id:
        raise LifecycleConflictError("Order has no active assigned attempt")
    return attempt


def release_current_agent(order: Order) -> None:
    if order.current_agent is not None:
        order.current_agent.availability = AgentAvailability.AVAILABLE
    order.current_agent_id = None


def now_utc() -> datetime:
    return datetime.now(UTC)
