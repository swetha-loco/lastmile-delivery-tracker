from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Area, CodSurcharge, OrderType, RateCard, Zone


def require_zone(db: Session, zone_id: int) -> Zone:
    zone = db.get(Zone, zone_id)
    if zone is None:
        raise LookupError("Zone not found")
    return zone


def create_zone(db: Session, *, name: str, is_active: bool) -> Zone:
    zone = Zone(name=name.strip(), is_active=is_active)
    db.add(zone)
    flush_or_raise(db)
    return zone


def create_area(
    db: Session, *, name: str, postal_code: str, zone_id: int, is_active: bool
) -> Area:
    zone = require_zone(db, zone_id)
    area = Area(
        name=name.strip(),
        postal_code=normalize_postal_code(postal_code),
        zone=zone,
        is_active=is_active,
    )
    db.add(area)
    flush_or_raise(db)
    return area


def create_rate_card(
    db: Session,
    *,
    origin_zone_id: int,
    destination_zone_id: int,
    order_type: OrderType,
    rate_per_kg: Decimal,
    is_active: bool,
) -> RateCard:
    origin = require_zone(db, origin_zone_id)
    destination = require_zone(db, destination_zone_id)
    rate_card = RateCard(
        origin_zone=origin,
        destination_zone=destination,
        order_type=order_type,
        rate_per_kg=rate_per_kg,
        is_active=is_active,
    )
    db.add(rate_card)
    flush_or_raise(db)
    return rate_card


def upsert_cod_surcharge(
    db: Session, *, order_type: OrderType, amount: Decimal, is_active: bool
) -> CodSurcharge:
    surcharge = db.scalar(
        select(CodSurcharge).where(CodSurcharge.order_type == order_type)
    )
    if surcharge is None:
        surcharge = CodSurcharge(
            order_type=order_type, amount=amount, is_active=is_active
        )
        db.add(surcharge)
    else:
        surcharge.amount = amount
        surcharge.is_active = is_active
    flush_or_raise(db)
    return surcharge


def normalize_postal_code(postal_code: str) -> str:
    return postal_code.strip().upper()


def flush_or_raise(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise
