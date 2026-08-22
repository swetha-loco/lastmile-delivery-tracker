"""create initial delivery schema

Revision ID: 7fd34db0ff33
Revises:
Create Date: 2026-08-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7fd34db0ff33"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


user_role = postgresql.ENUM(
    "CUSTOMER", "DELIVERY_AGENT", "ADMIN", name="user_role", create_type=False
)
order_type = postgresql.ENUM("B2B", "B2C", name="order_type", create_type=False)
payment_type = postgresql.ENUM(
    "PREPAID", "COD", name="payment_type", create_type=False
)
order_status = postgresql.ENUM(
    "CREATED",
    "ASSIGNED",
    "PICKED_UP",
    "IN_TRANSIT",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "FAILED",
    "RESCHEDULED",
    name="order_status",
    create_type=False,
)
agent_availability = postgresql.ENUM(
    "AVAILABLE", "BUSY", "OFFLINE", name="agent_availability", create_type=False
)
delivery_attempt_status = postgresql.ENUM(
    "PLANNED",
    "IN_PROGRESS",
    "DELIVERED",
    "FAILED",
    name="delivery_attempt_status",
    create_type=False,
)
notification_channel = postgresql.ENUM(
    "EMAIL", "SMS", name="notification_channel", create_type=False
)
notification_status = postgresql.ENUM(
    "PENDING", "RETRY", "SENT", "FAILED", name="notification_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    order_type.create(bind, checkfirst=True)
    payment_type.create(bind, checkfirst=True)
    order_status.create(bind, checkfirst=True)
    agent_availability.create(bind, checkfirst=True)
    delivery_attempt_status.create(bind, checkfirst=True)
    notification_channel.create(bind, checkfirst=True)
    notification_status.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "zones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_zones_name_not_empty"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "cod_surcharges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_type", order_type, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_cod_surcharges_amount_non_negative"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_type"),
    )
    op.create_table(
        "areas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("postal_code", sa.String(length=32), nullable=False),
        sa.Column("zone_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("postal_code"),
    )
    op.create_index("ix_areas_zone_id", "areas", ["zone_id"])
    op.create_table(
        "rate_cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("origin_zone_id", sa.Integer(), nullable=False),
        sa.Column("destination_zone_id", sa.Integer(), nullable=False),
        sa.Column("order_type", order_type, nullable=False),
        sa.Column("rate_per_kg", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("rate_per_kg > 0", name="ck_rate_cards_rate_positive"),
        sa.ForeignKeyConstraint(["destination_zone_id"], ["zones.id"]),
        sa.ForeignKeyConstraint(["origin_zone_id"], ["zones.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "origin_zone_id",
            "destination_zone_id",
            "order_type",
            name="uq_rate_cards_zone_type",
        ),
    )
    op.create_table(
        "agent_profiles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("availability", agent_availability, server_default="OFFLINE", nullable=False),
        sa.Column("current_latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("current_longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("current_zone_id", sa.Integer(), nullable=True),
        sa.Column("location_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(current_latitude IS NULL AND current_longitude IS NULL) OR "
            "(current_latitude IS NOT NULL AND current_longitude IS NOT NULL)",
            name="ck_agent_profiles_coordinates_together",
        ),
        sa.CheckConstraint(
            "current_latitude IS NULL OR "
            "(current_latitude >= -90 AND current_latitude <= 90)",
            name="ck_agent_profiles_latitude_range",
        ),
        sa.CheckConstraint(
            "current_longitude IS NULL OR "
            "(current_longitude >= -180 AND current_longitude <= 180)",
            name="ck_agent_profiles_longitude_range",
        ),
        sa.ForeignKeyConstraint(["current_zone_id"], ["zones.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_agent_profiles_availability", "agent_profiles", ["availability"])
    op.create_index("ix_agent_profiles_current_zone_id", "agent_profiles", ["current_zone_id"])
    op.create_index("ix_agent_profiles_last_assigned_at", "agent_profiles", ["last_assigned_at"])
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("pickup_address", sa.String(length=500), nullable=False),
        sa.Column("pickup_postal_code", sa.String(length=32), nullable=False),
        sa.Column("pickup_latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("pickup_longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("pickup_zone_id", sa.Integer(), nullable=False),
        sa.Column("drop_address", sa.String(length=500), nullable=False),
        sa.Column("drop_postal_code", sa.String(length=32), nullable=False),
        sa.Column("drop_latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("drop_longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("drop_zone_id", sa.Integer(), nullable=False),
        sa.Column("length_cm", sa.Numeric(10, 3), nullable=False),
        sa.Column("breadth_cm", sa.Numeric(10, 3), nullable=False),
        sa.Column("height_cm", sa.Numeric(10, 3), nullable=False),
        sa.Column("actual_weight_kg", sa.Numeric(10, 3), nullable=False),
        sa.Column("volumetric_weight_kg", sa.Numeric(10, 3), nullable=False),
        sa.Column("billable_weight_kg", sa.Numeric(10, 3), nullable=False),
        sa.Column("order_type", order_type, nullable=False),
        sa.Column("payment_type", payment_type, nullable=False),
        sa.Column("rate_card_id", sa.Integer(), nullable=False),
        sa.Column("rate_per_kg", sa.Numeric(12, 2), nullable=False),
        sa.Column("delivery_charge", sa.Numeric(12, 2), nullable=False),
        sa.Column("cod_surcharge", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_charge", sa.Numeric(12, 2), nullable=False),
        sa.Column("current_status", order_status, nullable=False),
        sa.Column("current_agent_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length_cm > 0", name="ck_orders_length_positive"),
        sa.CheckConstraint("breadth_cm > 0", name="ck_orders_breadth_positive"),
        sa.CheckConstraint("height_cm > 0", name="ck_orders_height_positive"),
        sa.CheckConstraint("actual_weight_kg > 0", name="ck_orders_actual_weight_positive"),
        sa.CheckConstraint("volumetric_weight_kg > 0", name="ck_orders_volumetric_weight_positive"),
        sa.CheckConstraint("billable_weight_kg > 0", name="ck_orders_billable_weight_positive"),
        sa.CheckConstraint("rate_per_kg > 0", name="ck_orders_rate_positive"),
        sa.CheckConstraint("delivery_charge >= 0", name="ck_orders_delivery_charge_non_negative"),
        sa.CheckConstraint("cod_surcharge >= 0", name="ck_orders_cod_surcharge_non_negative"),
        sa.CheckConstraint("total_charge >= 0", name="ck_orders_total_charge_non_negative"),
        sa.CheckConstraint("pickup_latitude >= -90 AND pickup_latitude <= 90", name="ck_orders_pickup_latitude_range"),
        sa.CheckConstraint("pickup_longitude >= -180 AND pickup_longitude <= 180", name="ck_orders_pickup_longitude_range"),
        sa.CheckConstraint("drop_latitude >= -90 AND drop_latitude <= 90", name="ck_orders_drop_latitude_range"),
        sa.CheckConstraint("drop_longitude >= -180 AND drop_longitude <= 180", name="ck_orders_drop_longitude_range"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["current_agent_id"], ["agent_profiles.user_id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["drop_zone_id"], ["zones.id"]),
        sa.ForeignKeyConstraint(["pickup_zone_id"], ["zones.id"]),
        sa.ForeignKeyConstraint(["rate_card_id"], ["rate_cards.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orders_created_at", "orders", ["created_at"])
    op.create_index("ix_orders_current_agent_id", "orders", ["current_agent_id"])
    op.create_index("ix_orders_current_status", "orders", ["current_status"])
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_drop_zone_id", "orders", ["drop_zone_id"])
    op.create_index("ix_orders_pickup_zone_id", "orders", ["pickup_zone_id"])
    op.create_table(
        "delivery_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=True),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("status", delivery_attempt_status, nullable=False),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("attempt_number > 0", name="ck_delivery_attempts_number_positive"),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_profiles.user_id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "attempt_number", name="uq_delivery_attempts_order_attempt"),
    )
    op.create_index("ix_delivery_attempts_agent_id", "delivery_attempts", ["agent_id"])
    op.create_index("ix_delivery_attempts_order_id", "delivery_attempts", ["order_id"])
    op.create_table(
        "order_status_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("from_status", order_status, nullable=True),
        sa.Column("to_status", order_status, nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("actor_role", user_role, nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_order_status_history_order_created_id",
        "order_status_history",
        ["order_id", "created_at", "id"],
    )
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("status", notification_status, nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("attempt_count >= 0", name="ck_notification_deliveries_attempt_count_non_negative"),
        sa.ForeignKeyConstraint(["event_id"], ["outbox_events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "channel", name="uq_notification_deliveries_event_channel"),
    )
    op.create_index(
        "ix_notification_deliveries_status_next_attempt",
        "notification_deliveries",
        ["status", "next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_deliveries_status_next_attempt", table_name="notification_deliveries")
    op.drop_table("notification_deliveries")
    op.drop_table("outbox_events")
    op.drop_index("ix_order_status_history_order_created_id", table_name="order_status_history")
    op.drop_table("order_status_history")
    op.drop_index("ix_delivery_attempts_order_id", table_name="delivery_attempts")
    op.drop_index("ix_delivery_attempts_agent_id", table_name="delivery_attempts")
    op.drop_table("delivery_attempts")
    op.drop_index("ix_orders_pickup_zone_id", table_name="orders")
    op.drop_index("ix_orders_drop_zone_id", table_name="orders")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_index("ix_orders_current_status", table_name="orders")
    op.drop_index("ix_orders_current_agent_id", table_name="orders")
    op.drop_index("ix_orders_created_at", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_agent_profiles_last_assigned_at", table_name="agent_profiles")
    op.drop_index("ix_agent_profiles_current_zone_id", table_name="agent_profiles")
    op.drop_index("ix_agent_profiles_availability", table_name="agent_profiles")
    op.drop_table("agent_profiles")
    op.drop_table("rate_cards")
    op.drop_index("ix_areas_zone_id", table_name="areas")
    op.drop_table("areas")
    op.drop_table("cod_surcharges")
    op.drop_table("zones")
    op.drop_table("users")

    bind = op.get_bind()
    notification_status.drop(bind, checkfirst=True)
    notification_channel.drop(bind, checkfirst=True)
    delivery_attempt_status.drop(bind, checkfirst=True)
    agent_availability.drop(bind, checkfirst=True)
    order_status.drop(bind, checkfirst=True)
    payment_type.drop(bind, checkfirst=True)
    order_type.drop(bind, checkfirst=True)
    user_role.drop(bind, checkfirst=True)
