from dataclasses import dataclass
from decimal import Decimal
from math import ceil

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    Area,
    CodSurcharge,
    DeliveryAttempt,
    Order,
    OrderStatus,
    OrderStatusHistory,
    OrderType,
    OutboxEvent,
    PaymentType,
    RateCard,
    User,
    UserRole,
    Zone,
)
from app.schemas.orders import OrderInput
from app.services import geocoding
from app.services.configuration import normalize_postal_code
from app.services.pricing import MissingCodSurchargeError, PriceBreakdown, calculate_price


@dataclass(frozen=True)
class ResolvedAddress:
    formatted_address: str
    postal_code: str
    latitude: Decimal
    longitude: Decimal
    zone: Zone


@dataclass(frozen=True)
class QuoteResult:
    pickup: ResolvedAddress
    drop: ResolvedAddress
    price: PriceBreakdown
    order_type: OrderType
    payment_type: PaymentType


def build_quote(db: Session, payload: OrderInput) -> QuoteResult:
    pickup = resolve_address(db, payload.pickup_address)
    drop = resolve_address(db, payload.drop_address)
    rate_card = db.scalar(
        select(RateCard).where(
            RateCard.origin_zone_id == pickup.zone.id,
            RateCard.destination_zone_id == drop.zone.id,
            RateCard.order_type == payload.order_type,
            RateCard.is_active.is_(True),
        )
    )
    if rate_card is None:
        raise PricingConfigurationError("No active rate card is configured")

    surcharge = None
    if payload.payment_type == PaymentType.COD:
        surcharge = db.scalar(
            select(CodSurcharge).where(
                CodSurcharge.order_type == payload.order_type,
                CodSurcharge.is_active.is_(True),
            )
        )
        if surcharge is None:
            raise PricingConfigurationError("No active COD surcharge is configured")

    try:
        price = calculate_price(
            length_cm=payload.length_cm,
            breadth_cm=payload.breadth_cm,
            height_cm=payload.height_cm,
            actual_weight_kg=payload.actual_weight_kg,
            payment_type=payload.payment_type,
            rate_card=rate_card,
            cod_surcharge=surcharge,
        )
    except MissingCodSurchargeError as exc:
        raise PricingConfigurationError("No active COD surcharge is configured") from exc

    return QuoteResult(
        pickup=pickup,
        drop=drop,
        price=price,
        order_type=payload.order_type,
        payment_type=payload.payment_type,
    )


def create_confirmed_order(
    db: Session, *, payload: OrderInput, customer: User, creator: User
) -> Order:
    quote = build_quote(db, payload)
    order = Order(
        customer=customer,
        creator=creator,
        pickup_address=quote.pickup.formatted_address,
        pickup_postal_code=quote.pickup.postal_code,
        pickup_latitude=quote.pickup.latitude,
        pickup_longitude=quote.pickup.longitude,
        pickup_zone=quote.pickup.zone,
        drop_address=quote.drop.formatted_address,
        drop_postal_code=quote.drop.postal_code,
        drop_latitude=quote.drop.latitude,
        drop_longitude=quote.drop.longitude,
        drop_zone=quote.drop.zone,
        length_cm=payload.length_cm,
        breadth_cm=payload.breadth_cm,
        height_cm=payload.height_cm,
        actual_weight_kg=quote.price.actual_weight_kg,
        volumetric_weight_kg=quote.price.volumetric_weight_kg,
        billable_weight_kg=quote.price.billable_weight_kg,
        order_type=payload.order_type,
        payment_type=payload.payment_type,
        rate_card_id=quote.price.rate_card_id,
        rate_per_kg=quote.price.rate_per_kg,
        delivery_charge=quote.price.delivery_charge,
        cod_surcharge=quote.price.cod_surcharge,
        total_charge=quote.price.total_charge,
        current_status=OrderStatus.CREATED,
        current_agent_id=None,
    )
    db.add(order)
    db.flush()
    db.add(
        OrderStatusHistory(
            order=order,
            from_status=None,
            to_status=OrderStatus.CREATED,
            actor_id=creator.id,
            actor_role=creator.role,
        )
    )
    db.add(
        OutboxEvent(
            event_type="ORDER_CREATED",
            order=order,
            payload={
                "order_id": order.id,
                "customer_id": customer.id,
                "customer_email": customer.email,
                "customer_phone": customer.phone,
                "status": OrderStatus.CREATED.value,
                "total_charge": str(order.total_charge),
            },
        )
    )
    db.flush()
    return order


def resolve_address(db: Session, address: str) -> ResolvedAddress:
    geocoded = geocoding.geocode_address(address)
    postal_code = normalize_postal_code(geocoded.postal_code)
    area = db.scalar(
        select(Area)
        .join(Area.zone)
        .where(
            Area.postal_code == postal_code,
            Area.is_active.is_(True),
            Zone.is_active.is_(True),
        )
    )
    if area is None:
        raise UnsupportedServiceAreaError("Unsupported service area")
    return ResolvedAddress(
        formatted_address=geocoded.formatted_address,
        postal_code=postal_code,
        latitude=geocoded.latitude,
        longitude=geocoded.longitude,
        zone=area.zone,
    )


def get_visible_order(db: Session, *, order_id: int, user: User) -> Order | None:
    order = db.get(Order, order_id)
    if order is None:
        return None
    if user.role == UserRole.ADMIN:
        return order
    if user.role == UserRole.CUSTOMER and order.customer_id == user.id:
        return order
    if user.role == UserRole.DELIVERY_AGENT:
        if order.current_agent_id == user.id or has_agent_attempt(
            db, order_id=order.id, agent_id=user.id
        ):
            return order
    return None


def lock_agent_order(db: Session, *, order_id: int, agent_id: int) -> Order | None:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None or order.current_agent_id != agent_id:
        return None
    return order


def has_agent_attempt(db: Session, *, order_id: int, agent_id: int) -> bool:
    return (
        db.scalar(
            select(DeliveryAttempt.id)
            .where(
                DeliveryAttempt.order_id == order_id,
                DeliveryAttempt.agent_id == agent_id,
            )
            .limit(1)
        )
        is not None
    )


def list_customer_orders(
    db: Session, *, customer_id: int, page: int, page_size: int
) -> dict[str, object]:
    return paginate_orders(
        db,
        select(Order).where(Order.customer_id == customer_id),
        page=page,
        page_size=page_size,
    )


def list_admin_orders(
    db: Session,
    *,
    page: int,
    page_size: int,
    status: OrderStatus | None = None,
    zone_id: int | None = None,
    agent_id: int | None = None,
) -> dict[str, object]:
    query = select(Order)
    if status is not None:
        query = query.where(Order.current_status == status)
    if zone_id is not None:
        query = query.where(
            or_(Order.pickup_zone_id == zone_id, Order.drop_zone_id == zone_id)
        )
    if agent_id is not None:
        query = query.where(Order.current_agent_id == agent_id)
    return paginate_orders(db, query, page=page, page_size=page_size)


def paginate_orders(
    db: Session, query, *, page: int, page_size: int
) -> dict[str, object]:
    total = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    rows = db.scalars(
        query.order_by(Order.created_at.desc(), Order.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [order_summary(order) for order in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": ceil(total / page_size) if total else 0,
    }


def order_summary(order: Order) -> dict[str, object]:
    return {
        "id": order.id,
        "pickup_address": order.pickup_address,
        "pickup_zone_id": order.pickup_zone_id,
        "pickup_zone_name": order.pickup_zone.name,
        "drop_address": order.drop_address,
        "drop_zone_id": order.drop_zone_id,
        "drop_zone_name": order.drop_zone.name,
        "current_status": order.current_status,
        "total_charge": order.total_charge,
        "current_agent_id": order.current_agent_id,
        "created_at": order.created_at,
    }


class PricingConfigurationError(Exception):
    pass


class UnsupportedServiceAreaError(Exception):
    pass
