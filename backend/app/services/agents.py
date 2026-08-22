from datetime import UTC, datetime
from decimal import Decimal
from math import ceil

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    AgentAvailability,
    AgentProfile,
    DeliveryAttempt,
    Order,
    OrderStatus,
    User,
    UserRole,
)
from app.security import hash_password
from app.services.orders import paginate_orders


def create_agent(
    db: Session, *, name: str, email: str, phone: str | None, password: str
) -> User:
    user = User(
        name=name.strip(),
        email=email.strip().lower(),
        phone=phone.strip() if phone else None,
        password_hash=hash_password(password),
        role=UserRole.DELIVERY_AGENT,
    )
    profile = AgentProfile(user=user, availability=AgentAvailability.OFFLINE)
    db.add_all([user, profile])
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise
    return user


def list_agents(db: Session, *, page: int, page_size: int) -> dict[str, object]:
    total = db.scalar(
        select(func.count()).select_from(User).where(User.role == UserRole.DELIVERY_AGENT)
    )
    total = int(total or 0)
    rows = db.scalars(
        select(User)
        .where(User.role == UserRole.DELIVERY_AGENT)
        .join(User.agent_profile)
        .order_by(User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "availability": user.agent_profile.availability,
            "current_zone_id": user.agent_profile.current_zone_id,
            "current_latitude": user.agent_profile.current_latitude,
            "current_longitude": user.agent_profile.current_longitude,
            "location_updated_at": user.agent_profile.location_updated_at,
            "last_assigned_at": user.agent_profile.last_assigned_at,
        }
        for user in rows
    ]
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": ceil(total / page_size) if total else 0,
    }


def update_location(
    db: Session, *, agent: User, latitude: Decimal, longitude: Decimal
) -> AgentProfile:
    profile = require_profile(db, agent)
    profile.current_latitude = latitude
    profile.current_longitude = longitude
    profile.current_zone_id = None
    profile.location_updated_at = datetime.now(UTC)
    db.flush()
    return profile


def update_availability(
    db: Session, *, agent: User, availability: AgentAvailability
) -> AgentProfile:
    if availability == AgentAvailability.BUSY:
        raise AgentAvailabilityError("Agents cannot manually set BUSY")
    profile = require_profile(db, agent)
    if profile.availability == AgentAvailability.BUSY and has_active_assignment(
        db, agent.id
    ):
        raise AgentAvailabilityConflictError("Agent has an active assignment")
    profile.availability = availability
    db.flush()
    return profile


def list_agent_orders(
    db: Session, *, agent_id: int, page: int, page_size: int
) -> dict[str, object]:
    query = (
        select(Order)
        .outerjoin(DeliveryAttempt, DeliveryAttempt.order_id == Order.id)
        .where(
            or_(Order.current_agent_id == agent_id, DeliveryAttempt.agent_id == agent_id)
        )
        .distinct()
    )
    return paginate_orders(db, query, page=page, page_size=page_size)


def has_active_assignment(db: Session, agent_id: int) -> bool:
    return (
        db.scalar(
            select(Order.id)
            .where(
                Order.current_agent_id == agent_id,
                Order.current_status.not_in(
                    [OrderStatus.DELIVERED, OrderStatus.FAILED]
                ),
            )
            .limit(1)
        )
        is not None
    )


def require_profile(db: Session, agent: User) -> AgentProfile:
    profile = db.get(AgentProfile, agent.id)
    if profile is None:
        raise LookupError("Agent profile not found")
    return profile


class AgentAvailabilityError(Exception):
    pass


class AgentAvailabilityConflictError(Exception):
    pass
