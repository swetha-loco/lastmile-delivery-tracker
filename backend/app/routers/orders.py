from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user, require_customer, require_role
from app.models import Order, OrderStatusHistory, User, UserRole
from app.schemas.orders import (
    OrderDetail,
    OrderInput,
    OrderPage,
    QuoteResponse,
    TrackingResponse,
)
from app.services import geocoding
from app.services import orders as order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "/quote",
    response_model=QuoteResponse,
    dependencies=[Depends(require_role(UserRole.CUSTOMER, UserRole.ADMIN))],
)
def quote_order(
    payload: OrderInput, db: Annotated[Session, Depends(get_db)]
) -> dict[str, object]:
    quote = build_or_raise_quote(db, payload)
    return quote_response(quote)


@router.post("", response_model=OrderDetail, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderInput,
    customer: Annotated[User, Depends(require_customer)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    try:
        order = order_service.create_confirmed_order(
            db, payload=payload, customer=customer, creator=customer
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


@router.get("", response_model=OrderPage)
def list_orders(
    customer: Annotated[User, Depends(require_customer)],
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, object]:
    return order_service.list_customer_orders(
        db, customer_id=customer.id, page=page, page_size=page_size
    )


@router.get("/{order_id}", response_model=OrderDetail)
def get_order(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    order = order_service.get_visible_order(db, order_id=order_id, user=current_user)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order_detail(order)


@router.get("/{order_id}/tracking", response_model=TrackingResponse)
def get_tracking(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    order = order_service.get_visible_order(db, order_id=order_id, user=current_user)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    history = db.scalars(
        select(OrderStatusHistory)
        .where(OrderStatusHistory.order_id == order.id)
        .order_by(OrderStatusHistory.created_at, OrderStatusHistory.id)
    ).all()
    return {
        "order_id": order.id,
        "current_status": order.current_status,
        "history": history,
    }


def build_or_raise_quote(db: Session, payload: OrderInput) -> order_service.QuoteResult:
    try:
        return order_service.build_quote(db, payload)
    except (
        geocoding.GeocodingNoResultError,
        geocoding.GeocodingMissingPostcodeError,
        order_service.UnsupportedServiceAreaError,
        order_service.PricingConfigurationError,
    ) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except geocoding.GeocodingConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except geocoding.GeocodingProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


def order_http_exception(exc: Exception) -> HTTPException:
    if isinstance(
        exc,
        (
            geocoding.GeocodingNoResultError,
            geocoding.GeocodingMissingPostcodeError,
            order_service.UnsupportedServiceAreaError,
            order_service.PricingConfigurationError,
        ),
    ):
        return HTTPException(
            status_code=422, detail=str(exc)
        )
    if isinstance(exc, geocoding.GeocodingConfigurationError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


def quote_response(quote: order_service.QuoteResult) -> dict[str, object]:
    return {
        "pickup": address_response(quote.pickup),
        "drop": address_response(quote.drop),
        "actual_weight_kg": quote.price.actual_weight_kg,
        "volumetric_weight_kg": quote.price.volumetric_weight_kg,
        "billable_weight_kg": quote.price.billable_weight_kg,
        "order_type": quote.order_type,
        "payment_type": quote.payment_type,
        "rate_per_kg": quote.price.rate_per_kg,
        "delivery_charge": quote.price.delivery_charge,
        "cod_surcharge": quote.price.cod_surcharge,
        "total_charge": quote.price.total_charge,
    }


def address_response(address: order_service.ResolvedAddress) -> dict[str, object]:
    return {
        "formatted_address": address.formatted_address,
        "postal_code": address.postal_code,
        "latitude": address.latitude,
        "longitude": address.longitude,
        "zone_id": address.zone.id,
        "zone_name": address.zone.name,
    }


def order_detail(order: Order) -> dict[str, object]:
    return {
        **order_service.order_summary(order),
        "customer_id": order.customer_id,
        "created_by_id": order.created_by_id,
        "pickup_postal_code": order.pickup_postal_code,
        "pickup_latitude": order.pickup_latitude,
        "pickup_longitude": order.pickup_longitude,
        "drop_postal_code": order.drop_postal_code,
        "drop_latitude": order.drop_latitude,
        "drop_longitude": order.drop_longitude,
        "length_cm": order.length_cm,
        "breadth_cm": order.breadth_cm,
        "height_cm": order.height_cm,
        "actual_weight_kg": order.actual_weight_kg,
        "volumetric_weight_kg": order.volumetric_weight_kg,
        "billable_weight_kg": order.billable_weight_kg,
        "order_type": order.order_type,
        "payment_type": order.payment_type,
        "rate_card_id": order.rate_card_id,
        "rate_per_kg": order.rate_per_kg,
        "delivery_charge": order.delivery_charge,
        "cod_surcharge": order.cod_surcharge,
        "updated_at": order.updated_at,
    }
