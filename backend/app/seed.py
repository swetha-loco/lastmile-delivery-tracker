from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import (
    AgentAvailability,
    AgentProfile,
    Area,
    CodSurcharge,
    OrderType,
    RateCard,
    User,
    UserRole,
    Zone,
)
from app.security import hash_password


ZONE_NAMES = ["Central", "North", "South"]
AREA_ROWS = [
    ("Chennai GPO", "600001", "Central"),
    ("Anna Road", "600002", "Central"),
    ("Parktown", "600003", "North"),
    ("Mylapore", "600004", "South"),
    ("Adyar", "600020", "South"),
]
LEGACY_DEMO_POSTAL_CODES = ["DEMO1001", "DEMO1002", "DEMO2001", "DEMO3001"]
COD_SURCHARGES = {
    OrderType.B2B: Decimal("10.00"),
    OrderType.B2C: Decimal("25.00"),
}
DEMO_USERS = [
    ("Admin Demo", "admin@lastmile-demo.com", None, UserRole.ADMIN),
    ("Customer Demo", "customer@lastmile-demo.com", "+10000000001", UserRole.CUSTOMER),
    ("Agent One Demo", "agent1@lastmile-demo.com", None, UserRole.DELIVERY_AGENT),
    ("Agent Two Demo", "agent2@lastmile-demo.com", None, UserRole.DELIVERY_AGENT),
]


def get_or_create_zone(db: Session, name: str) -> Zone:
    zone = db.scalar(select(Zone).where(Zone.name == name))
    if zone is None:
        zone = Zone(name=name)
        db.add(zone)
        db.flush()
    else:
        zone.is_active = True
    return zone


def seed_configuration(db: Session) -> None:
    zones = {name: get_or_create_zone(db, name) for name in ZONE_NAMES}

    for name, postal_code, zone_name in AREA_ROWS:
        area = db.scalar(select(Area).where(Area.postal_code == postal_code))
        if area is None:
            db.add(
                Area(
                    name=name,
                    postal_code=postal_code,
                    zone=zones[zone_name],
                )
            )
        else:
            area.name = name
            area.zone = zones[zone_name]
            area.is_active = True

    for postal_code in LEGACY_DEMO_POSTAL_CODES:
        area = db.scalar(select(Area).where(Area.postal_code == postal_code))
        if area is not None:
            area.is_active = False

    db.flush()

    for origin in zones.values():
        for destination in zones.values():
            for order_type in OrderType:
                rate_card = db.scalar(
                    select(RateCard).where(
                        RateCard.origin_zone == origin,
                        RateCard.destination_zone == destination,
                        RateCard.order_type == order_type,
                    )
                )
                rate = demo_rate(origin.name == destination.name, order_type)
                if rate_card is None:
                    db.add(
                        RateCard(
                            origin_zone=origin,
                            destination_zone=destination,
                            order_type=order_type,
                            rate_per_kg=rate,
                        )
                    )
                else:
                    rate_card.rate_per_kg = rate
                    rate_card.is_active = True

    for order_type, amount in COD_SURCHARGES.items():
        surcharge = db.scalar(
            select(CodSurcharge).where(CodSurcharge.order_type == order_type)
        )
        if surcharge is None:
            db.add(CodSurcharge(order_type=order_type, amount=amount))
        else:
            surcharge.amount = amount
            surcharge.is_active = True


def seed_demo_users(db: Session, demo_password: str) -> None:
    for name, email, phone, role in DEMO_USERS:
        normalized_email = email.lower()
        user = db.scalar(select(User).where(User.email == normalized_email))
        if user is None:
            user = User(
                name=name,
                email=normalized_email,
                phone=phone,
                password_hash=hash_password(demo_password),
                role=role,
            )
            db.add(user)
            db.flush()
        else:
            user.name = name
            user.phone = phone
            user.role = role

        if role == UserRole.DELIVERY_AGENT and user.agent_profile is None:
            db.add(
                AgentProfile(
                    user=user,
                    availability=AgentAvailability.OFFLINE,
                )
            )


def demo_rate(is_intra_zone: bool, order_type: OrderType) -> Decimal:
    if is_intra_zone:
        return Decimal("35.00") if order_type == OrderType.B2B else Decimal("40.00")
    return Decimal("55.00") if order_type == OrderType.B2B else Decimal("65.00")


def main() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        seed_configuration(db)
        seed_demo_users(db, settings.demo_password)
        db.commit()
    print("Seeded demo configuration data and demo users.")


if __name__ == "__main__":
    main()
