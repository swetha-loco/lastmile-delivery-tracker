from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import OrderStatus, OrderType
from app.schemas.auth import clean_required


class AgentCreateRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    password: str = Field(min_length=8)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return clean_required(value)

    @field_validator("phone")
    @classmethod
    def clean_optional_phone(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class ZoneCreateRequest(BaseModel):
    name: str
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return clean_required(value)


class ZoneUpdateRequest(BaseModel):
    name: str | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        return clean_required(value) if value is not None else None


class ZoneResponse(BaseModel):
    id: int
    name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AreaCreateRequest(BaseModel):
    name: str
    postal_code: str
    zone_id: int
    is_active: bool = True

    @field_validator("name", "postal_code")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return clean_required(value)

    @field_validator("postal_code")
    @classmethod
    def normalize_postal_code(cls, value: str) -> str:
        return value.strip().upper()


class AreaUpdateRequest(BaseModel):
    name: str | None = None
    postal_code: str | None = None
    zone_id: int | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        return clean_required(value) if value is not None else None

    @field_validator("postal_code")
    @classmethod
    def clean_postal_code(cls, value: str | None) -> str | None:
        return clean_required(value).upper() if value is not None else None


class AreaResponse(BaseModel):
    id: int
    name: str
    postal_code: str
    zone_id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class RateCardCreateRequest(BaseModel):
    origin_zone_id: int
    destination_zone_id: int
    order_type: OrderType
    rate_per_kg: Decimal = Field(gt=0)
    is_active: bool = True


class RateCardUpdateRequest(BaseModel):
    rate_per_kg: Decimal | None = Field(default=None, gt=0)
    is_active: bool | None = None


class RateCardResponse(BaseModel):
    id: int
    origin_zone_id: int
    destination_zone_id: int
    order_type: OrderType
    rate_per_kg: Decimal
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CodSurchargePutRequest(BaseModel):
    amount: Decimal = Field(ge=0)
    is_active: bool = True


class CodSurchargeResponse(BaseModel):
    id: int
    order_type: OrderType
    amount: Decimal
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ManualAssignRequest(BaseModel):
    agent_id: int


class OverrideStatusRequest(BaseModel):
    target_status: OrderStatus
    reason: str = Field(max_length=500)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: str) -> str:
        return clean_required(value)
