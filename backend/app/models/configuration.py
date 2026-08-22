from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy import UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import OrderType

if TYPE_CHECKING:
    from app.models.delivery import Order
    from app.models.users import AgentProfile


class Zone(Base):
    __tablename__ = "zones"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_zones_name_not_empty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    areas: Mapped[list[Area]] = relationship(back_populates="zone")
    origin_rate_cards: Mapped[list[RateCard]] = relationship(
        back_populates="origin_zone", foreign_keys="RateCard.origin_zone_id"
    )
    destination_rate_cards: Mapped[list[RateCard]] = relationship(
        back_populates="destination_zone", foreign_keys="RateCard.destination_zone_id"
    )
    pickup_orders: Mapped[list[Order]] = relationship(
        back_populates="pickup_zone", foreign_keys="Order.pickup_zone_id"
    )
    drop_orders: Mapped[list[Order]] = relationship(
        back_populates="drop_zone", foreign_keys="Order.drop_zone_id"
    )
    agent_profiles: Mapped[list[AgentProfile]] = relationship(back_populates="current_zone")


class Area(Base):
    __tablename__ = "areas"
    __table_args__ = (Index("ix_areas_zone_id", "zone_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    zone: Mapped[Zone] = relationship(back_populates="areas")


class RateCard(Base):
    __tablename__ = "rate_cards"
    __table_args__ = (
        UniqueConstraint(
            "origin_zone_id",
            "destination_zone_id",
            "order_type",
            name="uq_rate_cards_zone_type",
        ),
        CheckConstraint("rate_per_kg > 0", name="ck_rate_cards_rate_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    origin_zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), nullable=False)
    destination_zone_id: Mapped[int] = mapped_column(
        ForeignKey("zones.id"), nullable=False
    )
    order_type: Mapped[OrderType] = mapped_column(
        Enum(OrderType, name="order_type"), nullable=False
    )
    rate_per_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    origin_zone: Mapped[Zone] = relationship(
        back_populates="origin_rate_cards", foreign_keys=[origin_zone_id]
    )
    destination_zone: Mapped[Zone] = relationship(
        back_populates="destination_rate_cards", foreign_keys=[destination_zone_id]
    )
    orders: Mapped[list[Order]] = relationship(back_populates="rate_card")


class CodSurcharge(Base):
    __tablename__ = "cod_surcharges"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_cod_surcharges_amount_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_type: Mapped[OrderType] = mapped_column(
        Enum(OrderType, name="order_type"), nullable=False, unique=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
