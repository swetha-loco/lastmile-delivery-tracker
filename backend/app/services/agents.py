from math import ceil

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AgentAvailability, AgentProfile, User, UserRole
from app.security import hash_password


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
