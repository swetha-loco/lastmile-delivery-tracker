from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, or_, select

from app.config import get_settings
from app.db import SessionLocal
from app.main import app
from app.models import (
    AgentProfile,
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
from app.security import hash_password
from app.services import geocoding
from app.services.pricing import MissingCodSurchargeError, calculate_price

client = TestClient(app)

PICKUP_POSTCODE = "699001"
DROP_POSTCODE = "699020"
ALT_POSTCODE = "699003"


@pytest.fixture(autouse=True)
def clean_order_test_rows() -> None:
    cleanup()
    yield
    cleanup()


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@order-test.com"


def unique_name(prefix: str) -> str:
    return f"Order{prefix}-{uuid4().hex[:12]}"


def auth_header(user: User, password: str = "password123") -> dict[str, str]:
    response = client.post(
        "/auth/login", data={"username": user.email, "password": password}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_user(role: UserRole) -> User:
    with SessionLocal() as db:
        user = User(
            name=unique_name(role.value),
            email=unique_email(role.value.lower()),
            phone="+15550000000" if role == UserRole.CUSTOMER else None,
            password_hash=hash_password("password123"),
            role=role,
        )
        db.add(user)
        db.flush()
        if role == UserRole.DELIVERY_AGENT:
            db.add(AgentProfile(user=user))
        db.commit()
        db.refresh(user)
        return user


def create_config(*, rate: Decimal = Decimal("40.00"), b2b_rate: Decimal = Decimal("35.00")) -> dict[str, int]:
    with SessionLocal() as db:
        pickup_zone = Zone(name=unique_name("PickupZone"))
        drop_zone = Zone(name=unique_name("DropZone"))
        alt_zone = Zone(name=unique_name("AltZone"))
        db.add_all([pickup_zone, drop_zone, alt_zone])
        db.flush()
        db.add_all(
            [
                Area(name=unique_name("PickupArea"), postal_code=PICKUP_POSTCODE, zone=pickup_zone),
                Area(name=unique_name("DropArea"), postal_code=DROP_POSTCODE, zone=drop_zone),
                Area(name=unique_name("AltArea"), postal_code=ALT_POSTCODE, zone=alt_zone),
                RateCard(
                    origin_zone=pickup_zone,
                    destination_zone=drop_zone,
                    order_type=OrderType.B2C,
                    rate_per_kg=rate,
                ),
                RateCard(
                    origin_zone=pickup_zone,
                    destination_zone=pickup_zone,
                    order_type=OrderType.B2C,
                    rate_per_kg=Decimal("30.00"),
                ),
                RateCard(
                    origin_zone=pickup_zone,
                    destination_zone=drop_zone,
                    order_type=OrderType.B2B,
                    rate_per_kg=b2b_rate,
                ),
            ]
        )
        b2c = db.scalar(select(CodSurcharge).where(CodSurcharge.order_type == OrderType.B2C))
        b2b = db.scalar(select(CodSurcharge).where(CodSurcharge.order_type == OrderType.B2B))
        if b2c is None:
            db.add(CodSurcharge(order_type=OrderType.B2C, amount=Decimal("25.00")))
        else:
            b2c.amount = Decimal("25.00")
            b2c.is_active = True
        if b2b is None:
            db.add(CodSurcharge(order_type=OrderType.B2B, amount=Decimal("10.00")))
        else:
            b2b.amount = Decimal("10.00")
            b2b.is_active = True
        db.commit()
        return {
            "pickup_zone_id": pickup_zone.id,
            "drop_zone_id": drop_zone.id,
            "alt_zone_id": alt_zone.id,
        }


def order_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "pickup_address": "Pickup address",
        "drop_address": "Drop address",
        "length_cm": "10.000",
        "breadth_cm": "10.000",
        "height_cm": "10.000",
        "actual_weight_kg": "1.000",
        "order_type": "B2C",
        "payment_type": "PREPAID",
    }
    payload.update(overrides)
    return payload


def install_fake_geocoder(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(address: str) -> geocoding.GeocodedAddress:
        if "pickup" in address.lower():
            return geocoding.GeocodedAddress(
                formatted_address="Pickup formatted",
                postal_code=PICKUP_POSTCODE,
                latitude=Decimal("13.082700"),
                longitude=Decimal("80.270700"),
            )
        return geocoding.GeocodedAddress(
            formatted_address="Drop formatted",
            postal_code=DROP_POSTCODE,
            latitude=Decimal("13.006700"),
            longitude=Decimal("80.257800"),
        )

    monkeypatch.setattr(geocoding, "geocode_address", fake)


def test_pure_pricing_weights_order_types_zones_payment_and_rounding() -> None:
    rate_card = RateCard(id=1, rate_per_kg=Decimal("10.005"))
    surcharge = CodSurcharge(amount=Decimal("4.335"))

    actual_wins = calculate_price(
        length_cm=Decimal("10"),
        breadth_cm=Decimal("10"),
        height_cm=Decimal("10"),
        actual_weight_kg=Decimal("1.2344"),
        payment_type=PaymentType.PREPAID,
        rate_card=rate_card,
        cod_surcharge=None,
    )
    volumetric_wins = calculate_price(
        length_cm=Decimal("100"),
        breadth_cm=Decimal("100"),
        height_cm=Decimal("10"),
        actual_weight_kg=Decimal("1"),
        payment_type=PaymentType.COD,
        rate_card=RateCard(id=2, rate_per_kg=Decimal("7.00")),
        cod_surcharge=surcharge,
    )
    equal_weights = calculate_price(
        length_cm=Decimal("100"),
        breadth_cm=Decimal("100"),
        height_cm=Decimal("1"),
        actual_weight_kg=Decimal("2.000"),
        payment_type=PaymentType.PREPAID,
        rate_card=RateCard(id=3, rate_per_kg=Decimal("30.00"), order_type=OrderType.B2B),
        cod_surcharge=None,
    )

    assert actual_wins.actual_weight_kg == Decimal("1.234")
    assert actual_wins.volumetric_weight_kg == Decimal("0.200")
    assert actual_wins.billable_weight_kg == Decimal("1.234")
    assert actual_wins.delivery_charge == Decimal("12.35")
    assert actual_wins.cod_surcharge == Decimal("0.00")
    assert volumetric_wins.billable_weight_kg == Decimal("20.000")
    assert volumetric_wins.delivery_charge == Decimal("140.00")
    assert volumetric_wins.cod_surcharge == Decimal("4.34")
    assert equal_weights.billable_weight_kg == Decimal("2.000")


def test_pure_pricing_missing_cod_surcharge_for_cod() -> None:
    with pytest.raises(MissingCodSurchargeError):
        calculate_price(
            length_cm=Decimal("10"),
            breadth_cm=Decimal("10"),
            height_cm=Decimal("10"),
            actual_weight_kg=Decimal("1"),
            payment_type=PaymentType.COD,
            rate_card=RateCard(id=1, rate_per_kg=Decimal("10.00")),
            cod_surcharge=None,
        )


def test_geoapify_parsing_and_provider_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("GEOAPIFY_API_KEY", "test-key")

    class Response:
        def __init__(self, payload: dict[str, object]) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self.payload

    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: Response(
            {
                "results": [
                    {
                        "formatted": "Chennai GPO",
                        "postcode": "600001",
                        "lat": 13.0827,
                        "lon": 80.2707,
                    }
                ]
            }
        ),
    )
    result = geocoding.geocode_address("Chennai GPO")
    assert result.postal_code == "600001"

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: Response({"results": []}))
    with pytest.raises(geocoding.GeocodingNoResultError):
        geocoding.geocode_address("missing")

    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: Response({"results": [{"lat": 1, "lon": 2}]}),
    )
    with pytest.raises(geocoding.GeocodingMissingPostcodeError):
        geocoding.geocode_address("no postcode")

    def fail(*args, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "get", fail)
    with pytest.raises(geocoding.GeocodingProviderError):
        geocoding.geocode_address("provider failure")
    get_settings.cache_clear()


def test_geocoding_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.delenv("GEOAPIFY_API_KEY", raising=False)
    with pytest.raises(geocoding.GeocodingConfigurationError):
        geocoding.geocode_address("Chennai")
    get_settings.cache_clear()


def test_quote_customer_admin_rbac_response_and_non_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    create_config()
    customer = create_user(UserRole.CUSTOMER)
    admin = create_user(UserRole.ADMIN)
    agent = create_user(UserRole.DELIVERY_AGENT)
    install_fake_geocoder(monkeypatch)

    before = count_order_tables()
    customer_quote = client.post(
        "/orders/quote", headers=auth_header(customer), json=order_payload()
    )
    admin_quote = client.post(
        "/orders/quote", headers=auth_header(admin), json=order_payload()
    )
    agent_quote = client.post(
        "/orders/quote", headers=auth_header(agent), json=order_payload()
    )
    after = count_order_tables()

    assert customer_quote.status_code == 200
    assert admin_quote.status_code == 200
    assert agent_quote.status_code == 403
    assert customer_quote.json()["pickup"]["zone_name"].startswith("OrderPickupZone")
    assert Decimal(customer_quote.json()["total_charge"]) == Decimal("40.00")
    assert before == after


def test_quote_uses_b2b_and_intra_zone_rate_cards(monkeypatch: pytest.MonkeyPatch) -> None:
    create_config(b2b_rate=Decimal("35.00"))
    customer = create_user(UserRole.CUSTOMER)
    install_fake_geocoder(monkeypatch)

    b2b = client.post(
        "/orders/quote",
        headers=auth_header(customer),
        json=order_payload(order_type="B2B"),
    )

    def same_zone_geocoder(address: str) -> geocoding.GeocodedAddress:
        return geocoding.GeocodedAddress(
            formatted_address=f"{address} formatted",
            postal_code=PICKUP_POSTCODE,
            latitude=Decimal("13.082700"),
            longitude=Decimal("80.270700"),
        )

    monkeypatch.setattr(geocoding, "geocode_address", same_zone_geocoder)
    intra = client.post(
        "/orders/quote",
        headers=auth_header(customer),
        json=order_payload(),
    )

    assert b2b.status_code == 200
    assert Decimal(b2b.json()["rate_per_kg"]) == Decimal("35.00")
    assert intra.status_code == 200
    assert intra.json()["pickup"]["zone_id"] == intra.json()["drop"]["zone_id"]
    assert Decimal(intra.json()["rate_per_kg"]) == Decimal("30.00")


def test_quote_validation_and_service_area_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    create_config()
    customer = create_user(UserRole.CUSTOMER)
    install_fake_geocoder(monkeypatch)

    invalid = client.post(
        "/orders/quote",
        headers=auth_header(customer),
        json=order_payload(length_cm="0"),
    )
    assert invalid.status_code == 422

    monkeypatch.setattr(
        geocoding,
        "geocode_address",
        lambda address: geocoding.GeocodedAddress(
            "Unsupported", "000000", Decimal("1"), Decimal("2")
        ),
    )
    unsupported = client.post(
        "/orders/quote", headers=auth_header(customer), json=order_payload()
    )
    assert unsupported.status_code == 422


def test_inactive_area_and_zone_are_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    ids = create_config()
    customer = create_user(UserRole.CUSTOMER)
    install_fake_geocoder(monkeypatch)

    with SessionLocal() as db:
        area = db.scalar(select(Area).where(Area.postal_code == PICKUP_POSTCODE))
        assert area is not None
        area.is_active = False
        db.commit()
    inactive_area = client.post(
        "/orders/quote", headers=auth_header(customer), json=order_payload()
    )
    assert inactive_area.status_code == 422

    with SessionLocal() as db:
        area = db.scalar(select(Area).where(Area.postal_code == PICKUP_POSTCODE))
        zone = db.get(Zone, ids["pickup_zone_id"])
        assert area is not None and zone is not None
        area.is_active = True
        zone.is_active = False
        db.commit()
    inactive_zone = client.post(
        "/orders/quote", headers=auth_header(customer), json=order_payload()
    )
    assert inactive_zone.status_code == 422


def test_geocoding_failures_map_to_http_statuses(monkeypatch: pytest.MonkeyPatch) -> None:
    create_config()
    customer = create_user(UserRole.CUSTOMER)

    error_cases = [
        (geocoding.GeocodingNoResultError("No matching address found"), 422),
        (geocoding.GeocodingMissingPostcodeError("Address has no postcode"), 422),
        (geocoding.GeocodingProviderError("Geocoding provider unavailable"), 502),
    ]
    for exc, expected in error_cases:
        monkeypatch.setattr(geocoding, "geocode_address", lambda address, exc=exc: (_ for _ in ()).throw(exc))
        response = client.post(
            "/orders/quote", headers=auth_header(customer), json=order_payload()
        )
        assert response.status_code == expected


def test_missing_or_inactive_rate_and_cod_config_return_422(monkeypatch: pytest.MonkeyPatch) -> None:
    ids = create_config()
    customer = create_user(UserRole.CUSTOMER)
    install_fake_geocoder(monkeypatch)

    with SessionLocal() as db:
        rate_card = db.scalar(
            select(RateCard).where(
                RateCard.origin_zone_id == ids["pickup_zone_id"],
                RateCard.destination_zone_id == ids["drop_zone_id"],
                RateCard.order_type == OrderType.B2C,
            )
        )
        assert rate_card is not None
        rate_card.is_active = False
        db.commit()
    missing_rate = client.post(
        "/orders/quote", headers=auth_header(customer), json=order_payload()
    )
    assert missing_rate.status_code == 422

    cleanup()
    create_config()
    customer = create_user(UserRole.CUSTOMER)
    install_fake_geocoder(monkeypatch)
    with SessionLocal() as db:
        surcharge = db.scalar(select(CodSurcharge).where(CodSurcharge.order_type == OrderType.B2C))
        assert surcharge is not None
        surcharge.is_active = False
        db.commit()
    missing_cod = client.post(
        "/orders/quote",
        headers=auth_header(customer),
        json=order_payload(payment_type="COD"),
    )
    assert missing_cod.status_code == 422


def test_customer_order_creation_snapshot_history_outbox_list_detail_tracking(monkeypatch: pytest.MonkeyPatch) -> None:
    create_config()
    customer = create_user(UserRole.CUSTOMER)
    other_customer = create_user(UserRole.CUSTOMER)
    admin = create_user(UserRole.ADMIN)
    install_fake_geocoder(monkeypatch)

    response = client.post(
        "/orders",
        headers=auth_header(customer),
        json=order_payload(total_charge="0.01"),
    )

    assert response.status_code == 201
    body = response.json()
    order_id = body["id"]
    assert body["current_status"] == OrderStatus.CREATED
    assert body["current_agent_id"] is None
    assert Decimal(body["total_charge"]) == Decimal("40.00")

    with SessionLocal() as db:
        order = db.get(Order, order_id)
        assert order is not None
        assert db.scalar(select(OrderStatusHistory).where(OrderStatusHistory.order_id == order_id)).to_status == OrderStatus.CREATED
        event = db.scalar(select(OutboxEvent).where(OutboxEvent.order_id == order_id))
        assert event is not None
        assert event.event_type == "ORDER_CREATED"
        assert db.scalar(select(DeliveryAttempt).where(DeliveryAttempt.order_id == order_id)) is None

    listing = client.get("/orders", headers=auth_header(customer))
    detail = client.get(f"/orders/{order_id}", headers=auth_header(customer))
    admin_detail = client.get(f"/orders/{order_id}", headers=auth_header(admin))
    blocked = client.get(f"/orders/{order_id}", headers=auth_header(other_customer))
    tracking = client.get(f"/orders/{order_id}/tracking", headers=auth_header(customer))

    assert any(item["id"] == order_id for item in listing.json()["items"])
    assert detail.status_code == 200
    assert admin_detail.status_code == 200
    assert blocked.status_code == 404
    assert tracking.status_code == 200
    assert tracking.json()["history"][0]["to_status"] == OrderStatus.CREATED


def test_pricing_snapshot_invariance_and_new_quote_uses_new_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    create_config(rate=Decimal("40.00"))
    customer = create_user(UserRole.CUSTOMER)
    install_fake_geocoder(monkeypatch)

    created = client.post("/orders", headers=auth_header(customer), json=order_payload())
    assert created.status_code == 201
    order_id = created.json()["id"]

    with SessionLocal() as db:
        rate_card = db.get(RateCard, created.json()["rate_card_id"])
        assert rate_card is not None
        rate_card.rate_per_kg = Decimal("100.00")
        db.commit()

    historical = client.get(f"/orders/{order_id}", headers=auth_header(customer)).json()
    new_quote = client.post(
        "/orders/quote", headers=auth_header(customer), json=order_payload()
    ).json()

    assert Decimal(historical["rate_per_kg"]) == Decimal("40.00")
    assert Decimal(historical["delivery_charge"]) == Decimal("40.00")
    assert Decimal(historical["total_charge"]) == Decimal("40.00")
    assert Decimal(new_quote["rate_per_kg"]) == Decimal("100.00")
    assert Decimal(new_quote["total_charge"]) == Decimal("100.00")


def test_admin_order_creation_and_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    ids = create_config()
    admin = create_user(UserRole.ADMIN)
    customer = create_user(UserRole.CUSTOMER)
    agent = create_user(UserRole.DELIVERY_AGENT)
    install_fake_geocoder(monkeypatch)

    created = client.post(
        "/admin/orders",
        headers=auth_header(admin),
        json={"customer_id": customer.id, **order_payload()},
    )
    bad_target = client.post(
        "/admin/orders",
        headers=auth_header(admin),
        json={"customer_id": agent.id, **order_payload()},
    )

    assert created.status_code == 201
    body = created.json()
    assert body["customer_id"] == customer.id
    assert body["created_by_id"] == admin.id
    assert bad_target.status_code == 422

    with SessionLocal() as db:
        history = db.scalar(
            select(OrderStatusHistory).where(OrderStatusHistory.order_id == body["id"])
        )
        assert history is not None
        assert history.actor_id == admin.id

    all_orders = client.get("/admin/orders", headers=auth_header(admin))
    status_filter = client.get(
        "/admin/orders",
        headers=auth_header(admin),
        params={"status": "CREATED"},
    )
    zone_filter = client.get(
        "/admin/orders",
        headers=auth_header(admin),
        params={"zone_id": ids["pickup_zone_id"]},
    )
    agent_filter = client.get(
        "/admin/orders",
        headers=auth_header(admin),
        params={"agent_id": agent.id},
    )

    assert any(item["id"] == body["id"] for item in all_orders.json()["items"])
    assert any(item["id"] == body["id"] for item in status_filter.json()["items"])
    assert any(item["id"] == body["id"] for item in zone_filter.json()["items"])
    assert agent_filter.json()["items"] == []


def count_order_tables() -> tuple[int, int, int]:
    with SessionLocal() as db:
        return (
            int(db.scalar(select(func.count()).select_from(Order)) or 0),
            int(db.scalar(select(func.count()).select_from(OrderStatusHistory)) or 0),
            int(db.scalar(select(func.count()).select_from(OutboxEvent)) or 0),
        )


def cleanup() -> None:
    with SessionLocal() as db:
        test_user_ids = select(User.id).where(User.email.endswith("@order-test.com"))
        test_zone_ids = select(Zone.id).where(Zone.name.startswith("Order"))
        test_order_ids = select(Order.id).where(
            or_(
                Order.customer_id.in_(test_user_ids),
                Order.created_by_id.in_(test_user_ids),
                Order.pickup_zone_id.in_(test_zone_ids),
                Order.drop_zone_id.in_(test_zone_ids),
            )
        )
        db.execute(delete(DeliveryAttempt).where(DeliveryAttempt.order_id.in_(test_order_ids)))
        db.execute(delete(OutboxEvent).where(OutboxEvent.order_id.in_(test_order_ids)))
        db.execute(delete(OrderStatusHistory).where(OrderStatusHistory.order_id.in_(test_order_ids)))
        db.execute(delete(Order).where(Order.id.in_(test_order_ids)))
        db.execute(
            delete(RateCard).where(
                or_(
                    RateCard.origin_zone_id.in_(test_zone_ids),
                    RateCard.destination_zone_id.in_(test_zone_ids),
                )
            )
        )
        db.execute(delete(Area).where(Area.zone_id.in_(test_zone_ids)))
        db.execute(delete(Zone).where(Zone.id.in_(test_zone_ids)))
        db.execute(delete(AgentProfile).where(AgentProfile.user_id.in_(test_user_ids)))
        db.execute(delete(User).where(User.id.in_(test_user_ids)))
        b2b = db.scalar(select(CodSurcharge).where(CodSurcharge.order_type == OrderType.B2B))
        b2c = db.scalar(select(CodSurcharge).where(CodSurcharge.order_type == OrderType.B2C))
        if b2b is not None:
            b2b.amount = Decimal("10.00")
            b2b.is_active = True
        if b2c is not None:
            b2c.amount = Decimal("25.00")
            b2c.is_active = True
        db.commit()
