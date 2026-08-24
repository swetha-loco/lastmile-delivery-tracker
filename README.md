# Last-Mile Delivery Tracker

A full-stack logistics delivery platform for transparent pricing, role-based operations, intelligent agent assignment, delivery tracking, failed-attempt rescheduling, and reliable customer notifications.

## Live Demo

- **Frontend:** https://last-mile-delivery-tracker-black.vercel.app/
- **Backend API:** https://lastmile-delivery-tracker-ushp.onrender.com
- **Swagger / OpenAPI:** https://lastmile-delivery-tracker-ushp.onrender.com/docs
- **Health:** https://lastmile-delivery-tracker-ushp.onrender.com/health

> The demo backend uses Render's free tier, so the first request after inactivity may take time while the service wakes up.


## Demo Address / Service-Area Inputs

The hosted demo is configured for a small set of Chennai service areas. For the most reliable evaluation, enter a **normal full address that includes one of the supported PIN codes below**.

| Service area | Zone | Recommended demo input |
| --- | --- | --- |
| Chennai GPO / George Town | Central | `Chennai GPO, George Town, Chennai, Tamil Nadu 600001, India` |
| Anna Road / Anna Salai | Central | `Anna Salai, Chennai, Tamil Nadu 600002, India` |
| Park Town | North | `Park Town, Chennai, Tamil Nadu 600003, India` |
| Mylapore | South | `Mylapore, Chennai, Tamil Nadu 600004, India` |
| Adyar | South | `Adyar, Chennai, Tamil Nadu 600020, India` |

Recommended test route:

```text
Pickup: Mylapore, Chennai, Tamil Nadu 600004, India
Drop:   Adyar, Chennai, Tamil Nadu 600020, India
```

Another inter-zone example:

```text
Pickup: Park Town, Chennai, Tamil Nadu 600003, India
Drop:   Mylapore, Chennai, Tamil Nadu 600004, India
```

> **Important:** Geoapify geocodes the entered text and the backend maps the returned postcode to an admin-configured service area. For a deterministic demo, include the supported PIN code. Locality-only inputs such as `Mylapore, Chennai` may be rejected if the geocoding response does not contain enough postcode/locality information. Avoid combining a locality with the wrong PIN code because the geocoder may resolve it unexpectedly.

The backend also contains a conservative locality-name fallback when Geoapify returns no postcode but provides a uniquely matching configured locality. It deliberately does not use broad fuzzy matching or guess unsupported zones.

## Demo Accounts

All seeded demo accounts use the password **`unthinkable`**.

| Role | Email |
| --- | --- |
| Admin | `admin@lastmile-demo.com` |
| Customer | `customer@lastmile-demo.com` |
| Delivery Agent 1 | `agent1@lastmile-demo.com` |
| Delivery Agent 2 | `agent2@lastmile-demo.com` |

> Seeded agents start as `OFFLINE`. For notification-provider testing, register a customer with an email/phone number permitted by your Resend/Twilio account.

## What the Application Supports

### Customer
- Register and log in.
- Enter pickup/drop addresses, package dimensions, actual weight, B2B/B2C type, and Prepaid/COD payment mode.
- Add package description, fragile handling, and delivery instructions.
- Get an authoritative quote before confirmation.
- View current order status and immutable tracking timeline.
- Reschedule a failed delivery for a future date.

### Admin
- Create orders on behalf of customers.
- Manage zones, service areas, B2B/B2C rate cards, and COD surcharges.
- View/filter orders by status, zone, and agent.
- Manually assign an agent or trigger nearest-available auto-assignment.
- Create/list delivery agents.
- Override status with a mandatory audit reason.

### Delivery Agent
- View profile, availability, and assigned/recent orders.
- Update current location.
- Move assigned orders through the permitted lifecycle.
- Mark an out-for-delivery attempt as failed with a reason.
- View package description, fragile flag, and delivery instructions.

## Architecture

```text
                    +----------------------+
                    |   React + Vite UI    |
                    |      (Vercel)        |
                    +----------+-----------+
                               |
                               | HTTPS / JWT
                               v
                    +----------------------+
                    |    FastAPI Backend   |
                    |      (Render)        |
                    +----+------------+----+
                         |            |
                         | SQLAlchemy | Provider APIs
                         v            v
              +----------------+   +---------------------+
              |   PostgreSQL   |   | Geoapify / Resend  |
              |    (Render)    |   |      / Twilio      |
              +----------------+   +---------------------+
                       ^
                       |
               notification worker
               polls delivery rows
```

The backend is a modular monolith organized around:

```text
router -> service/domain logic -> SQLAlchemy/PostgreSQL
```

This keeps transaction and business rules explicit without unnecessary repository, broker, or microservice layers.

## Technology Stack

### Frontend
- React
- TypeScript
- Vite
- React Router
- Tailwind CSS

### Backend
- FastAPI
- SQLAlchemy 2.x
- PostgreSQL
- Alembic
- Pydantic Settings
- PyJWT
- Argon2 password hashing via `pwdlib`
- Pytest

### Integrations
- **Geoapify:** address geocoding and postal-code resolution
- **Resend:** transactional email
- **Twilio:** SMS notifications

### Deployment
- **Vercel:** frontend
- **Render:** FastAPI web service + PostgreSQL

## Database Schema

```mermaid
erDiagram
    USERS ||--o| AGENT_PROFILES : "agent profile"
    USERS ||--o{ ORDERS : "customer"
    USERS ||--o{ ORDERS : "created by"
    ZONES ||--o{ AREAS : contains
    ZONES ||--o{ RATE_CARDS : origin
    ZONES ||--o{ RATE_CARDS : destination
    ZONES ||--o{ ORDERS : pickup
    ZONES ||--o{ ORDERS : drop
    RATE_CARDS ||--o{ ORDERS : priced_with
    AGENT_PROFILES ||--o{ ORDERS : current_agent
    ORDERS ||--o{ ORDER_STATUS_HISTORY : history
    ORDERS ||--o{ DELIVERY_ATTEMPTS : attempts
    AGENT_PROFILES ||--o{ DELIVERY_ATTEMPTS : assigned_agent
    ORDERS ||--o{ OUTBOX_EVENTS : emits
    OUTBOX_EVENTS ||--o{ NOTIFICATION_DELIVERIES : delivered_via

    USERS {
      int id PK
      string name
      string email UK
      string phone
      string role
    }
    ZONES {
      int id PK
      string name UK
      bool is_active
    }
    AREAS {
      int id PK
      string postal_code UK
      int zone_id FK
      bool is_active
    }
    RATE_CARDS {
      int id PK
      int origin_zone_id FK
      int destination_zone_id FK
      string order_type
      decimal rate_per_kg
      bool is_active
    }
    COD_SURCHARGES {
      int id PK
      string order_type UK
      decimal amount
      bool is_active
    }
    AGENT_PROFILES {
      int user_id PK,FK
      string availability
      decimal current_latitude
      decimal current_longitude
      int current_zone_id FK
      datetime last_assigned_at
    }
    ORDERS {
      int id PK
      int customer_id FK
      int created_by_id FK
      int pickup_zone_id FK
      int drop_zone_id FK
      decimal actual_weight_kg
      decimal volumetric_weight_kg
      decimal billable_weight_kg
      decimal rate_per_kg
      decimal delivery_charge
      decimal cod_surcharge
      decimal total_charge
      string current_status
      int current_agent_id FK
      bool is_fragile
    }
    ORDER_STATUS_HISTORY {
      int id PK
      int order_id FK
      string from_status
      string to_status
      int actor_id FK
      string actor_role
      string reason
      datetime created_at
    }
    DELIVERY_ATTEMPTS {
      int id PK
      int order_id FK
      int attempt_number
      int agent_id FK
      date scheduled_date
      string status
      string failure_reason
    }
    OUTBOX_EVENTS {
      int id PK
      int order_id FK
      string event_type
      json payload
      datetime created_at
    }
    NOTIFICATION_DELIVERIES {
      int id PK
      int event_id FK
      string channel
      string status
      int attempt_count
      datetime next_attempt_at
      string provider_message_id
    }
```

Core tables: `users`, `zones`, `areas`, `rate_cards`, `cod_surcharges`, `agent_profiles`, `orders`, `order_status_history`, `delivery_attempts`, `outbox_events`, and `notification_deliveries`.

## Rate Calculation Logic

Pricing is calculated only from authoritative backend configuration.

### 1. Zone detection
Pickup and drop addresses are geocoded through Geoapify. The returned postal codes are normalized and matched against active admin-configured `areas`, each of which belongs to one `zone`.

If Geoapify returns no postcode, the backend may conservatively match a uniquely identified configured locality. If the address still cannot be resolved to an active configured area, the quote is rejected rather than guessing a zone.

For the hosted demo, use one of the supported Chennai addresses/PIN codes listed in **Demo Address / Service-Area Inputs** above.

### 2. Volumetric weight

```text
volumetric_weight_kg = length_cm * breadth_cm * height_cm / 5000
```

### 3. Billable weight

```text
billable_weight_kg = max(actual_weight_kg, volumetric_weight_kg)
```

### 4. Rate-card lookup
An active rate card is selected by:

```text
(origin_zone, destination_zone, order_type)
```

- same origin/destination zone -> intra-zone rate
- different zones -> inter-zone rate
- B2B and B2C have separate rates

### 5. Charge

```text
delivery_charge = billable_weight_kg * rate_per_kg

total_charge = delivery_charge + cod_surcharge   # only for COD
```

The application uses `Decimal`, stores weights to 3 decimal places, and money to 2 decimal places with `ROUND_HALF_UP`.

When an order is confirmed, the backend recalculates pricing and snapshots the rate and totals. Historical orders therefore do not change when an admin later edits rate cards.

## Auto-Assignment

Agents explicitly have one of three availability states:

```text
AVAILABLE | BUSY | OFFLINE
```

Auto-assignment:

1. considers only AVAILABLE agents;
2. calculates Haversine distance from each agent's current coordinates to pickup;
3. selects the nearest agent;
4. uses least-recently-assigned and agent ID as deterministic tie-breaks;
5. falls back to an AVAILABLE agent in the pickup zone when coordinates are unavailable;
6. leaves the order unassigned with `409 Conflict` if nobody is eligible.

PostgreSQL row-level locking rechecks availability during assignment so two concurrent orders cannot successfully claim the same agent.

## Order Lifecycle and Failed Delivery

Normal lifecycle:

```text
CREATED -> ASSIGNED -> PICKED_UP -> IN_TRANSIT
        -> OUT_FOR_DELIVERY -> DELIVERED
```

Failure path:

```text
OUT_FOR_DELIVERY -> FAILED -> RESCHEDULED -> ASSIGNED -> ...
```

Every transition appends an immutable status-history row containing the actor, actor role, timestamp, previous status, next status, and optional reason.

A failed delivery attempt is preserved rather than overwritten. Rescheduling creates the next `DeliveryAttempt`, initially unassigned and `PLANNED`, after which normal manual/auto assignment runs again.

## Notifications

Status-changing operations create an immutable `outbox_event` and separate EMAIL/SMS `notification_deliveries` in the same database transaction.

A worker sends notifications through Resend and Twilio after the transaction commits. This means a provider outage does not roll back a successful delivery-status update.

Retry policy per channel:

```text
maximum attempts: 5
retry delays: 1 min -> 5 min -> 15 min -> 60 min
```

Email and SMS succeed/fail independently, and `(event_id, channel)` uniqueness prevents duplicate delivery records. `SENT` records are not resent.

For Twilio trial accounts, `TWILIO_TRIAL_MODE=true` uses Twilio's permitted predefined trial templates; full accounts can use the normal custom SMS path.

## Local Setup

### Prerequisites

- Git
- Docker Desktop / Docker Engine
- Python 3.13 recommended
- Node.js 20+ / current LTS
- npm

### 1. Clone

```bash
git clone https://github.com/swetha-loco/lastmile-delivery-tracker.git
cd lastmile-delivery-tracker
```

### 2. Start PostgreSQL

```bash
docker compose up -d
```

Local PostgreSQL is exposed on host port `5434`.

### 3. Backend environment

```bash
cd backend
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
```

macOS/Linux:

```bash
source .venv/bin/activate
cp .env.example .env
```

Install dependencies:

```bash
pip install -r requirements.txt
```

At minimum, configure `backend/.env`:

```env
APP_ENV=development
DATABASE_URL=postgresql+psycopg://lastmile:lastmile@localhost:5434/lastmile
FRONTEND_URL=http://localhost:5173
JWT_SECRET=replace-me
ACCESS_TOKEN_EXPIRE_MINUTES=60
DEMO_PASSWORD=unthinkable
GEOAPIFY_API_KEY=your_geoapify_key
GEOCODING_COUNTRY_CODE=in
RESEND_API_KEY=
EMAIL_FROM=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
TWILIO_TRIAL_MODE=false
RUN_NOTIFICATION_WORKER=false
```

Never commit `.env` files or real credentials.

### 4. Migrate and seed

```bash
alembic upgrade head
python -m app.seed
```

The seed is idempotent and creates demo zones, supported areas, rates, COD surcharges, and demo users.

Seeded service areas:

| Area | Postal code | Zone |
| --- | --- | --- |
| Chennai GPO | 600001 | Central |
| Anna Road | 600002 | Central |
| Parktown | 600003 | North |
| Mylapore | 600004 | South |
| Adyar | 600020 | South |

Seeded rates:

| Route type | B2B | B2C |
| --- | ---: | ---: |
| Intra-zone | Rs. 35/kg | Rs. 40/kg |
| Inter-zone | Rs. 55/kg | Rs. 65/kg |

Seeded COD surcharge:

| Order type | Surcharge |
| --- | ---: |
| B2B | Rs. 10 |
| B2C | Rs. 25 |

### 5. Start backend

```bash
uvicorn app.main:app --reload
```

Backend:

```text
http://localhost:8000
http://localhost:8000/docs
```

### 6. Optional standalone notification worker

In another terminal:

```bash
cd backend
python -m app.worker
```

For normal local development keep `RUN_NOTIFICATION_WORKER=false`; the standalone worker is the clean process model.

### 7. Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env` from `.env.example`:

```env
VITE_API_URL=http://localhost:8000
```

Then:

```bash
npm run dev
```

Frontend:

```text
http://localhost:5173
```

## Environment Variables

### Backend

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | Runtime environment |
| `DATABASE_URL` | PostgreSQL SQLAlchemy connection URL |
| `FRONTEND_URL` | Allowed frontend CORS origin |
| `JWT_SECRET` | JWT signing secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token TTL |
| `DEMO_PASSWORD` | Seeded demo-account password |
| `GEOAPIFY_API_KEY` | Address geocoding |
| `GEOCODING_COUNTRY_CODE` | Geocoding country filter |
| `RESEND_API_KEY` | Email provider credential |
| `EMAIL_FROM` | Email sender |
| `TWILIO_ACCOUNT_SID` | Twilio account identifier |
| `TWILIO_AUTH_TOKEN` | Twilio credential |
| `TWILIO_FROM_NUMBER` | SMS sender for full Twilio accounts |
| `TWILIO_TRIAL_MODE` | Uses trial-compatible predefined Twilio bodies |
| `RUN_NOTIFICATION_WORKER` | Runs polling worker inside API process when enabled |

### Frontend

| Variable | Purpose |
| --- | --- |
| `VITE_API_URL` | FastAPI base URL |

## API Overview

Full interactive API documentation is available at `/docs`.

### Public / Auth

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Service/database health |
| POST | `/auth/register` | Register CUSTOMER |
| POST | `/auth/login` | Login |
| GET | `/auth/me` | Current authenticated user |

### Customer

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/orders/quote` | Calculate quote |
| POST | `/orders` | Confirm/create own order |
| GET | `/orders` | List own orders |
| GET | `/orders/{id}` | Order detail |
| GET | `/orders/{id}/tracking` | Immutable tracking timeline |
| POST | `/orders/{id}/reschedule` | Reschedule failed order |

### Delivery Agent

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/agent/profile` | Profile/location/availability |
| GET | `/agent/orders` | Assigned/recent orders |
| PATCH | `/agent/availability` | Set AVAILABLE/OFFLINE |
| PATCH | `/agent/location` | Update current location |
| PATCH | `/agent/orders/{id}/status` | Perform delivery transition |

### Admin

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST/GET | `/admin/agents` | Create/list agents |
| GET/POST/PATCH | `/admin/zones` | Manage zones |
| GET/POST/PATCH | `/admin/areas` | Manage areas |
| GET/POST/PATCH | `/admin/rate-cards` | Manage rates |
| GET/PUT | `/admin/cod-surcharges` | Manage COD surcharges |
| POST | `/admin/orders` | Create order for customer |
| GET | `/admin/orders` | List/filter all orders |
| POST | `/admin/orders/{id}/assign` | Manual assignment |
| POST | `/admin/orders/{id}/auto-assign` | Nearest-agent assignment |
| POST | `/admin/orders/{id}/override-status` | Audited admin override |

See `docs/api-contract.md` for the detailed permission/error contract.

## Testing

Backend:

```bash
cd backend
python -m pytest
```

Current verified baseline: **88 backend tests passing**.

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

The backend test suite covers pricing, rounding, service-area failures, authentication/RBAC, ownership, admin configuration, persistence constraints, assignment/concurrency, lifecycle transitions, failed/reschedule/reassign behavior, notification retry/idempotency, and provider adapters.

## Project Structure

```text
last-mile-delivery-tracker/
├── backend/
│   ├── alembic/               # database migrations
│   ├── app/
│   │   ├── models/            # SQLAlchemy model groups
│   │   ├── routers/           # FastAPI HTTP routes
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── services/          # pricing, order, assignment, lifecycle, notifications
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── main.py
│   │   ├── security.py
│   │   ├── seed.py
│   │   └── worker.py
│   └── tests/
├── frontend/
│   ├── public/
│   └── src/
│       ├── api/
│       ├── components/
│       ├── lib/
│       └── pages/
├── docs/
│   ├── api-contract.md
│   ├── architecture.md
│   ├── data-model.md
│   ├── requirements.md
│   └── test-plan.md
└── compose.yaml
```

## Important Design Decisions

- PostgreSQL is the source of truth; no in-memory business state.
- Quote != order. Confirmation recalculates pricing from authoritative configuration.
- Historical orders snapshot pricing.
- Service zones use admin-managed postal-code areas instead of guessed proximity.
- Explicit AVAILABLE/BUSY/OFFLINE agent state.
- Haversine nearest-agent assignment with deterministic tie-breaks.
- PostgreSQL row locking prevents concurrent double assignment.
- Failed delivery attempts remain immutable historical attempts.
- Status history is append-only.
- Notifications use a transactional outbox and independent channel deliveries.
- Kafka, Redis, Celery, PostGIS, and microservices were intentionally avoided because they do not improve the assignment's required scale or correctness.

## Deployment Notes

The hosted demo uses:

```text
Vercel -> React frontend
Render Web Service -> FastAPI
Render PostgreSQL -> persistent data
```

The intended notification architecture is a separate `python -m app.worker` process. Because the free Render tier does not provide a separate free background worker, the demo can co-locate the same polling logic inside the FastAPI service with:

```env
RUN_NOTIFICATION_WORKER=true
```

The notification processing logic itself is shared; it is not duplicated.

## Documentation

- `docs/api-contract.md` - REST endpoints, permissions, errors
- `docs/data-model.md` - tables, constraints, lifecycle and concurrency rules
- `docs/architecture.md` - detailed architecture decisions
- `SYSTEM_DESIGN.md` - concise submission write-up (under 800 words)

## License / Use

Built as a technical assignment / portfolio demonstration of backend design, delivery workflow modelling, pricing, concurrency-safe assignment, and full-stack product implementation.
