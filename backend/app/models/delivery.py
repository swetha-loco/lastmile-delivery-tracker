from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy import UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import (
    DeliveryAttemptStatus,
    OrderStatus,
    OrderType,
    PaymentType,
    UserRole,
)

if TYPE_CHECKING:
    from app.models.configuration import RateCard, Zone
    from app.models.notifications import OutboxEvent
    from app.models.users import AgentProfile, User


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("length_cm > 0", name="ck_orders_length_positive"),
        CheckConstraint("breadth_cm > 0", name="ck_orders_breadth_positive"),
        CheckConstraint("height_cm > 0", name="ck_orders_height_positive"),
        CheckConstraint("actual_weight_kg > 0", name="ck_orders_actual_weight_positive"),
        CheckConstraint(
            "volumetric_weight_kg > 0", name="ck_orders_volumetric_weight_positive"
        ),
        CheckConstraint(
            "billable_weight_kg > 0", name="ck_orders_billable_weight_positive"
        ),
        CheckConstraint("rate_per_kg > 0", name="ck_orders_rate_positive"),
        CheckConstraint(
            "delivery_charge >= 0", name="ck_orders_delivery_charge_non_negative"
        ),
        CheckConstraint(
            "cod_surcharge >= 0", name="ck_orders_cod_surcharge_non_negative"
        ),
        CheckConstraint("total_charge >= 0", name="ck_orders_total_charge_non_negative"),
        CheckConstraint(
            "pickup_latitude >= -90 AND pickup_latitude <= 90",
            name="ck_orders_pickup_latitude_range",
        ),
        CheckConstraint(
            "pickup_longitude >= -180 AND pickup_longitude <= 180",
            name="ck_orders_pickup_longitude_range",
        ),
        CheckConstraint(
            "drop_latitude >= -90 AND drop_latitude <= 90",
            name="ck_orders_drop_latitude_range",
        ),
        CheckConstraint(
            "drop_longitude >= -180 AND drop_longitude <= 180",
            name="ck_orders_drop_longitude_range",
        ),
        Index("ix_orders_customer_id", "customer_id"),
        Index("ix_orders_current_status", "current_status"),
        Index("ix_orders_current_agent_id", "current_agent_id"),
        Index("ix_orders_pickup_zone_id", "pickup_zone_id"),
        Index("ix_orders_drop_zone_id", "drop_zone_id"),
        Index("ix_orders_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    pickup_address: Mapped[str] = mapped_column(String(500), nullable=False)
    pickup_postal_code: Mapped[str] = mapped_column(String(32), nullable=False)
    pickup_latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    pickup_longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    pickup_zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), nullable=False)
    drop_address: Mapped[str] = mapped_column(String(500), nullable=False)
    drop_postal_code: Mapped[str] = mapped_column(String(32), nullable=False)
    drop_latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    drop_longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    drop_zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), nullable=False)
    length_cm: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    breadth_cm: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    height_cm: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    actual_weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    package_description: Mapped[str | None] = mapped_column(String(200))
    is_fragile: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    delivery_instructions: Mapped[str | None] = mapped_column(String(500))
    volumetric_weight_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 3), nullable=False
    )
    billable_weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    order_type: Mapped[OrderType] = mapped_column(
        Enum(OrderType, name="order_type"), nullable=False
    )
    payment_type: Mapped[PaymentType] = mapped_column(
        Enum(PaymentType, name="payment_type"), nullable=False
    )
    rate_card_id: Mapped[int] = mapped_column(ForeignKey("rate_cards.id"), nullable=False)
    rate_per_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    delivery_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cod_surcharge: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    current_status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"), nullable=False
    )
    current_agent_id: Mapped[int | None] = mapped_column(
        ForeignKey("agent_profiles.user_id")
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

    customer: Mapped[User] = relationship(
        back_populates="customer_orders", foreign_keys=[customer_id]
    )
    creator: Mapped[User] = relationship(
        back_populates="created_orders", foreign_keys=[created_by_id]
    )
    pickup_zone: Mapped[Zone] = relationship(
        back_populates="pickup_orders", foreign_keys=[pickup_zone_id]
    )
    drop_zone: Mapped[Zone] = relationship(
        back_populates="drop_orders", foreign_keys=[drop_zone_id]
    )
    rate_card: Mapped[RateCard] = relationship(back_populates="orders")
    current_agent: Mapped[AgentProfile | None] = relationship(
        back_populates="current_orders"
    )
    status_history: Mapped[list[OrderStatusHistory]] = relationship(
        back_populates="order"
    )
    delivery_attempts: Mapped[list[DeliveryAttempt]] = relationship(
        back_populates="order"
    )
    outbox_events: Mapped[list[OutboxEvent]] = relationship(back_populates="order")


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"
    __table_args__ = (
        Index("ix_order_status_history_order_created_id", "order_id", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    from_status: Mapped[OrderStatus | None] = mapped_column(
        Enum(OrderStatus, name="order_status")
    )
    to_status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"), nullable=False
    )
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    actor_role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order: Mapped[Order] = relationship(back_populates="status_history")
    actor: Mapped[User] = relationship(back_populates="status_history_entries")


class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"
    __table_args__ = (
        UniqueConstraint("order_id", "attempt_number", name="uq_delivery_attempts_order_attempt"),
        CheckConstraint("attempt_number > 0", name="ck_delivery_attempts_number_positive"),
        Index("ix_delivery_attempts_order_id", "order_id"),
        Index("ix_delivery_attempts_agent_id", "agent_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(nullable=False)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agent_profiles.user_id"))
    scheduled_date: Mapped[date] = mapped_column(nullable=False)
    status: Mapped[DeliveryAttemptStatus] = mapped_column(
        Enum(DeliveryAttemptStatus, name="delivery_attempt_status"), nullable=False
    )
    failure_reason: Mapped[str | None] = mapped_column(String(500))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    order: Mapped[Order] = relationship(back_populates="delivery_attempts")
    agent: Mapped[AgentProfile | None] = relationship(back_populates="delivery_attempts")
