from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_admin
from app.models import (
    Area,
    CodSurcharge,
    Order,
    OrderStatus,
    OrderType,
    RateCard,
    User,
    UserRole,
    Zone,
)
from app.schemas.admin import (
    AgentCreateRequest,
    AreaCreateRequest,
    AreaResponse,
    AreaUpdateRequest,
    CodSurchargePutRequest,
    CodSurchargeResponse,
    ManualAssignRequest,
    OverrideStatusRequest,
    RateCardCreateRequest,
    RateCardResponse,
    RateCardUpdateRequest,
    ZoneCreateRequest,
    ZoneResponse,
    ZoneUpdateRequest,
)
from app.schemas.orders import AdminOrderCreateRequest, OrderDetail, OrderPage
from app.schemas.users import AgentPage, UserPublic
from app.services import agents as agent_service
from app.services import assignment
from app.services import configuration as config_service
from app.services import geocoding
from app.services import lifecycle
from app.services import orders as order_service
from app.routers.orders import order_detail, order_http_exception

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.post("/agents", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentCreateRequest, db: Annotated[Session, Depends(get_db)]
) -> User:
    try:
        user = agent_service.create_agent(
            db,
            name=payload.name,
            email=str(payload.email),
            phone=payload.phone,
            password=payload.password,
        )
        db.commit()
    except IntegrityError as exc:
        raise conflict("Email already exists") from exc
    db.refresh(user)
    return user


@router.get("/agents", response_model=AgentPage)
def list_agents(
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, object]:
    return agent_service.list_agents(db, page=page, page_size=page_size)


@router.get("/zones", response_model=list[ZoneResponse])
def list_zones(db: Annotated[Session, Depends(get_db)]) -> list[Zone]:
    return list(db.scalars(select(Zone).order_by(Zone.id)))


@router.post("/zones", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
def create_zone(
    payload: ZoneCreateRequest, db: Annotated[Session, Depends(get_db)]
) -> Zone:
    try:
        zone = config_service.create_zone(
            db, name=payload.name, is_active=payload.is_active
        )
        db.commit()
    except IntegrityError as exc:
        raise conflict("Zone name already exists") from exc
    db.refresh(zone)
    return zone


@router.patch("/zones/{zone_id}", response_model=ZoneResponse)
def update_zone(
    zone_id: int,
    payload: ZoneUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Zone:
    zone = db.get(Zone, zone_id)
    if zone is None:
        raise not_found("Zone not found")
    if payload.name is not None:
        zone.name = payload.name
    if payload.is_active is not None:
        zone.is_active = payload.is_active
    try:
        db.commit()
    except IntegrityError as exc:
        raise conflict("Zone name already exists") from exc
    db.refresh(zone)
    return zone


@router.get("/areas", response_model=list[AreaResponse])
def list_areas(
    db: Annotated[Session, Depends(get_db)],
    zone_id: int | None = None,
) -> list[Area]:
    query = select(Area)
    if zone_id is not None:
        query = query.where(Area.zone_id == zone_id)
    return list(db.scalars(query.order_by(Area.id)))


@router.post("/areas", response_model=AreaResponse, status_code=status.HTTP_201_CREATED)
def create_area(
    payload: AreaCreateRequest, db: Annotated[Session, Depends(get_db)]
) -> Area:
    try:
        area = config_service.create_area(
            db,
            name=payload.name,
            postal_code=payload.postal_code,
            zone_id=payload.zone_id,
            is_active=payload.is_active,
        )
        db.commit()
    except LookupError as exc:
        raise not_found("Zone not found") from exc
    except IntegrityError as exc:
        raise conflict("Postal code already exists") from exc
    db.refresh(area)
    return area


@router.patch("/areas/{area_id}", response_model=AreaResponse)
def update_area(
    area_id: int,
    payload: AreaUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Area:
    area = db.get(Area, area_id)
    if area is None:
        raise not_found("Area not found")
    if payload.zone_id is not None:
        area.zone = config_service.require_zone(db, payload.zone_id)
    if payload.name is not None:
        area.name = payload.name
    if payload.postal_code is not None:
        area.postal_code = config_service.normalize_postal_code(payload.postal_code)
    if payload.is_active is not None:
        area.is_active = payload.is_active
    try:
        db.commit()
    except LookupError as exc:
        raise not_found("Zone not found") from exc
    except IntegrityError as exc:
        raise conflict("Postal code already exists") from exc
    db.refresh(area)
    return area


@router.get("/rate-cards", response_model=list[RateCardResponse])
def list_rate_cards(
    db: Annotated[Session, Depends(get_db)],
    origin_zone_id: int | None = None,
    destination_zone_id: int | None = None,
    order_type: OrderType | None = None,
    is_active: bool | None = None,
) -> list[RateCard]:
    query = select(RateCard)
    if origin_zone_id is not None:
        query = query.where(RateCard.origin_zone_id == origin_zone_id)
    if destination_zone_id is not None:
        query = query.where(RateCard.destination_zone_id == destination_zone_id)
    if order_type is not None:
        query = query.where(RateCard.order_type == order_type)
    if is_active is not None:
        query = query.where(RateCard.is_active == is_active)
    return list(db.scalars(query.order_by(RateCard.id)))


@router.post(
    "/rate-cards", response_model=RateCardResponse, status_code=status.HTTP_201_CREATED
)
def create_rate_card(
    payload: RateCardCreateRequest, db: Annotated[Session, Depends(get_db)]
) -> RateCard:
    try:
        rate_card = config_service.create_rate_card(db, **payload.model_dump())
        db.commit()
    except LookupError as exc:
        raise not_found("Zone not found") from exc
    except IntegrityError as exc:
        raise conflict("Rate card already exists") from exc
    db.refresh(rate_card)
    return rate_card


@router.patch("/rate-cards/{rate_card_id}", response_model=RateCardResponse)
def update_rate_card(
    rate_card_id: int,
    payload: RateCardUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> RateCard:
    rate_card = db.get(RateCard, rate_card_id)
    if rate_card is None:
        raise not_found("Rate card not found")
    if payload.rate_per_kg is not None:
        rate_card.rate_per_kg = payload.rate_per_kg
    if payload.is_active is not None:
        rate_card.is_active = payload.is_active
    db.commit()
    db.refresh(rate_card)
    return rate_card


@router.get("/cod-surcharges", response_model=list[CodSurchargeResponse])
def list_cod_surcharges(
    db: Annotated[Session, Depends(get_db)]
) -> list[CodSurcharge]:
    return list(db.scalars(select(CodSurcharge).order_by(CodSurcharge.id)))


@router.put("/cod-surcharges/{order_type}", response_model=CodSurchargeResponse)
def put_cod_surcharge(
    order_type: OrderType,
    payload: CodSurchargePutRequest,
    db: Annotated[Session, Depends(get_db)],
) -> CodSurcharge:
    surcharge = config_service.upsert_cod_surcharge(
        db,
        order_type=order_type,
        amount=payload.amount,
        is_active=payload.is_active,
    )
    db.commit()
    db.refresh(surcharge)
    return surcharge


@router.post("/orders", response_model=OrderDetail, status_code=status.HTTP_201_CREATED)
def create_order_for_customer(
    payload: AdminOrderCreateRequest,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    customer = db.get(User, payload.customer_id)
    if customer is None:
        raise not_found("Customer not found")
    if customer.role != UserRole.CUSTOMER:
        raise HTTPException(
            status_code=422,
            detail="Target user must be a customer",
        )
    try:
        order = order_service.create_confirmed_order(
            db, payload=payload, customer=customer, creator=admin
        )
        db.commit()
    except (
        geocoding.GeocodingNoResultError,
        geocoding.GeocodingMissingPostcodeError,
        geocoding.GeocodingConfigurationError,
        geocoding.GeocodingProviderError,
        order_service.UnsupportedServiceAreaError,
        order_service.PricingConfigurationError,
    ) as exc:
        db.rollback()
        raise order_http_exception(exc) from exc
    db.refresh(order)
    return order_detail(order)


@router.get("/orders", response_model=OrderPage)
def list_orders(
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: OrderStatus | None = None,
    zone_id: int | None = None,
    agent_id: int | None = None,
) -> dict[str, object]:
    return order_service.list_admin_orders(
        db,
        page=page,
        page_size=page_size,
        status=status,
        zone_id=zone_id,
        agent_id=agent_id,
    )


@router.post("/orders/{order_id}/assign", response_model=OrderDetail)
def assign_order(
    order_id: int,
    payload: ManualAssignRequest,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    try:
        order = assignment.assign_order_to_agent(
            db, order_id=order_id, agent_id=payload.agent_id, actor=admin
        )
        db.commit()
    except assignment.AssignmentNotFoundError as exc:
        db.rollback()
        raise not_found(str(exc)) from exc
    except assignment.AssignmentConflictError as exc:
        db.rollback()
        raise conflict(str(exc)) from exc
    db.refresh(order)
    return order_detail(order)


@router.post("/orders/{order_id}/auto-assign", response_model=OrderDetail)
def auto_assign_order(
    order_id: int,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    try:
        order = assignment.auto_assign_order(db, order_id=order_id, actor=admin)
        db.commit()
    except assignment.AssignmentNotFoundError as exc:
        db.rollback()
        raise not_found(str(exc)) from exc
    except assignment.AssignmentConflictError as exc:
        db.rollback()
        raise conflict(str(exc)) from exc
    db.refresh(order)
    return order_detail(order)


@router.post("/orders/{order_id}/override-status", response_model=OrderDetail)
def override_order_status(
    order_id: int,
    payload: OverrideStatusRequest,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise not_found("Order not found")
    try:
        lifecycle.transition_order(
            db,
            order=order,
            actor=admin,
            target_status=payload.target_status,
            reason=payload.reason,
            override=True,
        )
        db.commit()
    except lifecycle.LifecycleConflictError as exc:
        db.rollback()
        raise conflict(str(exc)) from exc
    db.refresh(order)
    return order_detail(order)


def conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
