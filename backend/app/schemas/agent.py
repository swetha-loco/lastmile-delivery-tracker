from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import AgentAvailability, OrderStatus
from app.schemas.orders import OrderPage


class AgentLocationRequest(BaseModel):
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)


class AgentAvailabilityRequest(BaseModel):
    availability: AgentAvailability


class AgentProfileResponse(BaseModel):
    user_id: int
    availability: AgentAvailability
    current_latitude: Decimal | None
    current_longitude: Decimal | None
    current_zone_id: int | None
    location_updated_at: datetime | None
    last_assigned_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AgentStatusUpdateRequest(BaseModel):
    target_status: OrderStatus
    reason: str | None = Field(default=None, max_length=500)


class AgentOrderPage(OrderPage):
    pass
