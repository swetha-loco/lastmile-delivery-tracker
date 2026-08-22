from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import OrderStatus, OrderType, PaymentType, UserRole
from app.schemas.auth import clean_required


class OrderInput(BaseModel):
    pickup_address: str = Field(max_length=500)
    drop_address: str = Field(max_length=500)
    length_cm: Decimal = Field(gt=0)
    breadth_cm: Decimal = Field(gt=0)
    height_cm: Decimal = Field(gt=0)
    actual_weight_kg: Decimal = Field(gt=0)
    order_type: OrderType
    payment_type: PaymentType

    @field_validator("pickup_address", "drop_address")
    @classmethod
    def clean_address(cls, value: str) -> str:
        return clean_required(value)


class AdminOrderCreateRequest(OrderInput):
    customer_id: int


class ResolvedAddressResponse(BaseModel):
    formatted_address: str
    postal_code: str
    latitude: Decimal
    longitude: Decimal
    zone_id: int
    zone_name: str


class QuoteResponse(BaseModel):
    pickup: ResolvedAddressResponse
    drop: ResolvedAddressResponse
    actual_weight_kg: Decimal
    volumetric_weight_kg: Decimal
    billable_weight_kg: Decimal
    order_type: OrderType
    payment_type: PaymentType
    rate_per_kg: Decimal
    delivery_charge: Decimal
    cod_surcharge: Decimal
    total_charge: Decimal


class OrderSummary(BaseModel):
    id: int
    pickup_address: str
    pickup_zone_id: int
    pickup_zone_name: str
    drop_address: str
    drop_zone_id: int
    drop_zone_name: str
    current_status: OrderStatus
    total_charge: Decimal
    current_agent_id: int | None
    created_at: datetime


class OrderPage(BaseModel):
    items: list[OrderSummary]
    page: int
    page_size: int
    total: int
    pages: int


class OrderDetail(OrderSummary):
    customer_id: int
    created_by_id: int
    pickup_postal_code: str
    pickup_latitude: Decimal
    pickup_longitude: Decimal
    drop_postal_code: str
    drop_latitude: Decimal
    drop_longitude: Decimal
    length_cm: Decimal
    breadth_cm: Decimal
    height_cm: Decimal
    actual_weight_kg: Decimal
    volumetric_weight_kg: Decimal
    billable_weight_kg: Decimal
    order_type: OrderType
    payment_type: PaymentType
    rate_card_id: int
    rate_per_kg: Decimal
    delivery_charge: Decimal
    cod_surcharge: Decimal
    updated_at: datetime


class TrackingHistoryEntry(BaseModel):
    id: int
    from_status: OrderStatus | None
    to_status: OrderStatus
    actor_id: int
    actor_role: UserRole
    reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrackingResponse(BaseModel):
    order_id: int
    current_status: OrderStatus
    history: list[TrackingHistoryEntry]
