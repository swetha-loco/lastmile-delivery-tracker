from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import AgentAvailability, UserRole


class UserPublic(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str | None
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class AgentPublic(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str | None
    availability: AgentAvailability
    current_zone_id: int | None
    current_latitude: Decimal | None
    current_longitude: Decimal | None
    location_updated_at: datetime | None
    last_assigned_at: datetime | None


class AgentPage(BaseModel):
    items: list[AgentPublic]
    page: int
    page_size: int
    total: int
    pages: int
