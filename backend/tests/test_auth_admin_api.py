from decimal import Decimal
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.main import app
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
from app.security import JWT_ALGORITHM, hash_password, verify_password

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_api_test_rows() -> None:
    cleanup_test_rows()
    yield
    cleanup_test_rows()


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@test-lastmile.com"


def unique_name(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def create_user(role: UserRole, password: str = "password123") -> User:
    with SessionLocal() as db:
        user = User(
            name=unique_name(role.value),
            email=unique_email(role.value.lower()),
            phone="+15550000000" if role == UserRole.CUSTOMER else None,
            password_hash=hash_password(password),
            role=role,
        )
        db.add(user)
        db.flush()
        if role == UserRole.DELIVERY_AGENT:
            db.add(AgentProfile(user=user, availability=AgentAvailability.OFFLINE))
        db.commit()
        db.refresh(user)
        return user


def auth_header(user: User, password: str = "password123") -> dict[str, str]:
    response = client.post(
        "/auth/login",
        data={"username": user.email, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def get_user(email: str) -> User:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        return user


def test_register_creates_customer_with_hashed_password_and_normalized_email() -> None:
    email = unique_email("register").upper()

    response = client.post(
        "/auth/register",
        json={
            "name": "  New Customer  ",
            "email": email,
            "phone": "  +15551234567  ",
            "password": "password123",
            "role": "ADMIN",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == UserRole.CUSTOMER
    assert body["email"] == email.lower()
    assert "password_hash" not in body

    user = get_user(email.lower())
    assert user.password_hash != "password123"
    assert verify_password("password123", user.password_hash)


def test_register_duplicate_email_returns_409() -> None:
    email = unique_email("duplicate")
    payload = {
        "name": "Customer",
        "email": email,
        "phone": "+15551234567",
        "password": "password123",
    }

    assert client.post("/auth/register", json=payload).status_code == 201
    response = client.post("/auth/register", json=payload)

    assert response.status_code == 409


def test_register_validation_errors() -> None:
    base = {
        "name": "Customer",
        "email": unique_email("valid"),
        "phone": "+15551234567",
        "password": "password123",
    }

    invalid_email = {**base, "email": "not-an-email"}
    missing_phone = {key: value for key, value in base.items() if key != "phone"}
    short_password = {**base, "email": unique_email("short"), "password": "short"}

    assert client.post("/auth/register", json=invalid_email).status_code == 422
    assert client.post("/auth/register", json=missing_phone).status_code == 422
    assert client.post("/auth/register", json=short_password).status_code == 422


def test_login_success_failure_and_token_payload() -> None:
    user = create_user(UserRole.CUSTOMER, password="password123")

    response = client.post(
        "/auth/login",
        data={"username": user.email.upper(), "password": "password123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert "password_hash" not in body
    payload = jwt.decode(
        body["access_token"], get_settings().jwt_secret, algorithms=[JWT_ALGORITHM]
    )
    assert payload["sub"] == str(user.id)
    assert "exp" in payload

    wrong_password = client.post(
        "/auth/login", data={"username": user.email, "password": "wrong-password"}
    )
    unknown_user = client.post(
        "/auth/login",
        data={"username": unique_email("missing"), "password": "password123"},
    )
    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401


def test_auth_me_requires_valid_bearer_token() -> None:
    user = create_user(UserRole.CUSTOMER)

    ok = client.get("/auth/me", headers=auth_header(user))
    no_token = client.get("/auth/me")
    bad_token = client.get("/auth/me", headers={"Authorization": "Bearer nope"})

    assert ok.status_code == 200
    assert ok.json()["email"] == user.email
    assert "password_hash" not in ok.json()
    assert no_token.status_code == 401
    assert bad_token.status_code == 401


def test_rbac_allows_admin_and_blocks_customer_and_agent() -> None:
    admin = create_user(UserRole.ADMIN)
    customer = create_user(UserRole.CUSTOMER)
    agent = create_user(UserRole.DELIVERY_AGENT)

    assert client.get("/admin/zones", headers=auth_header(admin)).status_code == 200
    assert client.get("/admin/zones", headers=auth_header(customer)).status_code == 403
    assert client.get("/admin/zones", headers=auth_header(agent)).status_code == 403


def test_admin_can_create_agent_with_offline_profile_and_list_agents() -> None:
    admin = create_user(UserRole.ADMIN)
    email = unique_email("agent-create")

    response = client.post(
        "/admin/agents",
        headers=auth_header(admin),
        json={
            "name": "Delivery Agent",
            "email": email,
            "password": "password123",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == UserRole.DELIVERY_AGENT
    assert "password_hash" not in body

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        assert user.agent_profile is not None
        assert user.agent_profile.availability == AgentAvailability.OFFLINE

    duplicate = client.post(
        "/admin/agents",
        headers=auth_header(admin),
        json={
            "name": "Delivery Agent",
            "email": email,
            "password": "password123",
        },
    )
    listing = client.get(
        "/admin/agents", headers=auth_header(admin), params={"page": 1, "page_size": 5}
    )

    assert duplicate.status_code == 409
    assert listing.status_code == 200
    assert {"items", "page", "page_size", "total", "pages"} <= set(listing.json())


def test_non_admins_cannot_create_agent() -> None:
    customer = create_user(UserRole.CUSTOMER)
    agent = create_user(UserRole.DELIVERY_AGENT)
    payload = {
        "name": "Delivery Agent",
        "email": unique_email("blocked-agent"),
        "password": "password123",
    }

    assert client.post("/admin/agents", headers=auth_header(customer), json=payload).status_code == 403
    assert client.post("/admin/agents", headers=auth_header(agent), json=payload).status_code == 403


def test_zone_admin_create_duplicate_patch_and_non_admin_block() -> None:
    admin = create_user(UserRole.ADMIN)
    customer = create_user(UserRole.CUSTOMER)
    name = unique_name("Zone")

    created = client.post(
        "/admin/zones", headers=auth_header(admin), json={"name": f" {name} "}
    )
    duplicate = client.post(
        "/admin/zones", headers=auth_header(admin), json={"name": name}
    )
    patched = client.patch(
        f"/admin/zones/{created.json()['id']}",
        headers=auth_header(admin),
        json={"name": f"{name}-patched", "is_active": False},
    )
    blocked = client.post(
        "/admin/zones", headers=auth_header(customer), json={"name": unique_name("No")}
    )

    assert created.status_code == 201
    assert duplicate.status_code == 409
    assert patched.status_code == 200
    assert patched.json()["is_active"] is False
    assert blocked.status_code == 403


def test_area_create_duplicate_missing_zone_and_filter() -> None:
    admin = create_user(UserRole.ADMIN)
    zone_id = create_zone_direct()
    postal_code = f"D{uuid4().hex[:12]}"

    created = client.post(
        "/admin/areas",
        headers=auth_header(admin),
        json={"name": "Demo Area", "postal_code": postal_code.lower(), "zone_id": zone_id},
    )
    duplicate = client.post(
        "/admin/areas",
        headers=auth_header(admin),
        json={"name": "Demo Area", "postal_code": postal_code, "zone_id": zone_id},
    )
    missing_zone = client.post(
        "/admin/areas",
        headers=auth_header(admin),
        json={"name": "Nowhere", "postal_code": f"D{uuid4().hex[:12]}", "zone_id": 0},
    )
    filtered = client.get(
        "/admin/areas", headers=auth_header(admin), params={"zone_id": zone_id}
    )

    assert created.status_code == 201
    assert created.json()["postal_code"] == postal_code.upper()
    assert duplicate.status_code == 409
    assert missing_zone.status_code == 404
    assert any(area["id"] == created.json()["id"] for area in filtered.json())


def test_rate_card_create_duplicate_missing_zone_and_patch_decimal() -> None:
    admin = create_user(UserRole.ADMIN)
    origin_id = create_zone_direct()
    destination_id = create_zone_direct()

    payload = {
        "origin_zone_id": origin_id,
        "destination_zone_id": destination_id,
        "order_type": OrderType.B2B,
        "rate_per_kg": "42.50",
    }
    created = client.post("/admin/rate-cards", headers=auth_header(admin), json=payload)
    duplicate = client.post("/admin/rate-cards", headers=auth_header(admin), json=payload)
    missing_zone = client.post(
        "/admin/rate-cards",
        headers=auth_header(admin),
        json={**payload, "origin_zone_id": 0, "order_type": OrderType.B2C},
    )
    patched = client.patch(
        f"/admin/rate-cards/{created.json()['id']}",
        headers=auth_header(admin),
        json={"rate_per_kg": "45.75", "is_active": False},
    )

    assert created.status_code == 201
    assert duplicate.status_code == 409
    assert missing_zone.status_code == 404
    assert patched.status_code == 200
    assert Decimal(patched.json()["rate_per_kg"]) == Decimal("45.75")
    assert patched.json()["is_active"] is False


def test_cod_surcharge_put_create_update_and_negative_validation() -> None:
    admin = create_user(UserRole.ADMIN)

    created = client.put(
        "/admin/cod-surcharges/B2B",
        headers=auth_header(admin),
        json={"amount": "12.25"},
    )
    updated = client.put(
        "/admin/cod-surcharges/B2B",
        headers=auth_header(admin),
        json={"amount": "13.50", "is_active": False},
    )
    negative = client.put(
        "/admin/cod-surcharges/B2C",
        headers=auth_header(admin),
        json={"amount": "-0.01"},
    )

    assert created.status_code == 200
    assert updated.status_code == 200
    assert Decimal(updated.json()["amount"]) == Decimal("13.50")
    assert updated.json()["is_active"] is False
    assert negative.status_code == 422


def test_openapi_has_oauth2_password_scheme_and_no_password_hash_schema() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    spec = response.json()
    assert "OAuth2PasswordBearer" in spec["components"]["securitySchemes"]
    serialized = str(spec)
    assert "password_hash" not in serialized


def create_zone_direct() -> int:
    with SessionLocal() as db:
        zone = Zone(name=unique_name("DirectZone"))
        db.add(zone)
        db.commit()
        db.refresh(zone)
        return zone.id


def cleanup_test_rows() -> None:
    with SessionLocal() as db:
        test_zone_ids = select(Zone.id).where(
            or_(Zone.name.startswith("Zone-"), Zone.name.startswith("DirectZone-"))
        )
        test_user_ids = select(User.id).where(User.email.endswith("@test-lastmile.com"))

        db.execute(
            delete(RateCard).where(
                or_(
                    RateCard.origin_zone_id.in_(test_zone_ids),
                    RateCard.destination_zone_id.in_(test_zone_ids),
                )
            )
        )
        db.execute(
            delete(Area).where(
                or_(Area.zone_id.in_(test_zone_ids), Area.name.in_(["Demo Area", "Nowhere"]))
            )
        )
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
