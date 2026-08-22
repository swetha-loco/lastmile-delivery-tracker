from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import AgentAvailability, UserRole

if TYPE_CHECKING:
    from app.models.configuration import Zone
    from app.models.delivery import DeliveryAttempt, Order, OrderStatusHistory


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    agent_profile: Mapped[AgentProfile | None] = relationship(
        back_populates="user", uselist=False
    )
    customer_orders: Mapped[list[Order]] = relationship(
        back_populates="customer", foreign_keys="Order.customer_id"
    )
    created_orders: Mapped[list[Order]] = relationship(
        back_populates="creator", foreign_keys="Order.created_by_id"
    )
    status_history_entries: Mapped[list[OrderStatusHistory]] = relationship(
        back_populates="actor"
    )


class AgentProfile(Base):
    __tablename__ = "agent_profiles"
    __table_args__ = (
        CheckConstraint(
            "(current_latitude IS NULL AND current_longitude IS NULL) OR "
            "(current_latitude IS NOT NULL AND current_longitude IS NOT NULL)",
            name="ck_agent_profiles_coordinates_together",
        ),
        CheckConstraint(
            "current_latitude IS NULL OR "
            "(current_latitude >= -90 AND current_latitude <= 90)",
            name="ck_agent_profiles_latitude_range",
        ),
        CheckConstraint(
            "current_longitude IS NULL OR "
            "(current_longitude >= -180 AND current_longitude <= 180)",
            name="ck_agent_profiles_longitude_range",
        ),
        Index("ix_agent_profiles_availability", "availability"),
        Index("ix_agent_profiles_current_zone_id", "current_zone_id"),
        Index("ix_agent_profiles_last_assigned_at", "last_assigned_at"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    availability: Mapped[AgentAvailability] = mapped_column(
        Enum(AgentAvailability, name="agent_availability"),
        nullable=False,
        server_default=AgentAvailability.OFFLINE.value,
    )
    current_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    current_longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    current_zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id"))
    location_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="agent_profile")
    current_zone: Mapped[Zone | None] = relationship(back_populates="agent_profiles")
    current_orders: Mapped[list[Order]] = relationship(back_populates="current_agent")
    delivery_attempts: Mapped[list[DeliveryAttempt]] = relationship(
        back_populates="agent"
    )
