# Preliminary Architecture

This is a planning document only. It describes the intended shape of the system
before application code is written.

Related planning documents:

- Data model: `docs/data-model.md`
- REST API and permissions: `docs/api-contract.md`
- Test plan: `docs/test-plan.md`

## System Context

The platform supports customers, delivery agents, and admins. Customers request
quotes, confirm orders, view current status, and inspect tracking history.
Admins configure service areas, zones, rate cards, COD surcharges, and agent
assignments. Delivery agents update delivery progress.

PostgreSQL is the source of truth for users, orders, quote/order pricing
snapshots, zones, postal-code service areas, rate cards, agent availability,
delivery attempts, tracking history, and notification state.

## Major Modules

- Identity and access: registration, login, password hashing, JWT issuance, and
  role-based authorization.
- Users: customer, delivery-agent, and admin profile data.
- Zones/rates: admin-managed zones, postal-code service areas, active/inactive
  rate cards, and COD surcharge configuration.
- Pricing: zone detection inputs, volumetric/billable weight calculation, rate
  card lookup, COD surcharge application, quote responses, and order pricing
  snapshots.
- Orders: order confirmation, current status, admin listing/filtering, and
  customer order views.
- Tracking/lifecycle: status transition validation, admin overrides, immutable
  history entries, and timeline reads.
- Agents/assignment: explicit agent availability, location data, manual
  assignment, and admin-triggered auto-assignment.
- Delivery attempts/rescheduling: one shipment's delivery attempts, failed
  attempt preservation, reschedule requests, and reassignment for new attempts.
- Notifications/outbox: durable notification events, email/SMS delivery records,
  retries, and provider adapters.
- Integrations: Geoapify, Resend, and Twilio provider-specific code.

These are modules inside one modular monolith, not separate services.

## Expected Request Flow

Backend requests should generally follow:

`router -> domain/service logic -> SQLAlchemy/PostgreSQL`

Routers handle HTTP concerns, authentication, request parsing, and response
mapping. Domain/service functions enforce business rules and own meaningful
transaction boundaries. SQLAlchemy models and queries persist state directly; a
repository layer is not planned unless later complexity justifies it.

Services should not scatter `commit()` calls through helper functions. A single
service operation should control each business transaction.

## Pricing And Quote Flow

A quote is not an order. The customer must receive a quote before confirming an
order.

Initial quote flow:

1. Geocode pickup and drop addresses with Geoapify.
2. Normalize each postal code.
3. Resolve each postal code to an admin-configured Area.
4. Resolve each Area to its Zone.
5. Calculate volumetric weight as
   `length_cm * breadth_cm * height_cm / 5000`.
6. Calculate billable weight as the greater of actual and volumetric weight.
7. Select the active rate card by origin zone, destination zone, and order type.
8. Calculate delivery charge as `billable_weight * rate_per_kg`.
9. Add the configured COD surcharge only for COD orders.

The quote response should eventually expose pickup zone, drop zone, actual
weight, volumetric weight, billable weight, rate per kg, delivery charge, COD
surcharge, and total charge.

When an order is confirmed, the backend must recalculate the price from current
authoritative configuration and must never trust a frontend-submitted total. The
confirmed order should snapshot the pricing inputs/results needed to preserve
the historical charge even if admins later change rate cards.

## Zone Detection

An Area initially represents a supported postal-code/service area assigned to
exactly one Zone. If an address geocodes successfully but its postal code is not
configured in an active admin-managed Area, the quote/order should be rejected
as outside unsupported service areas. The system should not guess the nearest
zone.

Polygon-based zones, PostGIS, and external routing APIs are not part of the
initial design.

## Lifecycle And Status History

Initial order lifecycle:

`CREATED -> ASSIGNED -> PICKED_UP -> IN_TRANSIT -> OUT_FOR_DELIVERY -> DELIVERED`

Failure may occur after a delivery attempt has begun:

`... -> FAILED`

After the customer chooses a new delivery date:

`FAILED -> RESCHEDULED -> ASSIGNED -> ...`

`CREATED`, `ASSIGNED`, and `RESCHEDULED` are internal implementation statuses.
`PICKED_UP`, `IN_TRANSIT`, `OUT_FOR_DELIVERY`, `DELIVERED`, and `FAILED` are the
delivery statuses explicitly named by the assignment.

Orders may keep `current_status` for efficient reads. Every actual transition
must atomically update the current status and append an immutable
status-history row containing from status, to status, timestamp, actor/user,
actor role, and optional reason. Application code must not update or delete
historical status rows.

Admin overrides still create history entries and should require an override
reason.

## Live Status

Initial "live/current status" means the latest persisted `orders.current_status`
plus the immutable tracking timeline. The frontend can periodically poll for
updates. WebSockets, SSE, continuous GPS tracking, and driver location streams
are not part of the initial design.

## Agent Availability And Assignment

Agent availability is explicit and uses these states:

- AVAILABLE
- BUSY
- OFFLINE

An agent profile may keep current latitude, current longitude, current zone, and
a location-updated timestamp. Availability must not be inferred solely from open
orders.

Creating an order does not automatically assign an agent. Orders begin as
CREATED and unassigned. Admins may manually assign an agent or explicitly
trigger auto-assignment.

Initial auto-assignment algorithm:

1. Find AVAILABLE agents with usable current coordinates.
2. Calculate Haversine distance from each agent to the pickup coordinates.
3. Select the nearest agent.
4. Assign inside a database transaction.
5. Re-check/lock availability before final assignment.
6. Mark the selected agent BUSY.
7. Create the assignment/status history and outbox events as applicable.

If no available agent has usable coordinates, the fallback is to consider
AVAILABLE agents whose current zone equals the pickup zone and choose
deterministically. If there are no eligible agents, leave the order unassigned
and CREATED, and return/report `409 Conflict`.

Route optimization, external routing APIs, PostGIS, and strategy frameworks are
not part of the initial design.

## Delivery Attempts

An Order represents the shipment. A DeliveryAttempt represents one actual
attempt to deliver it.

Each attempt should conceptually capture the order, attempt number, assigned
agent, scheduled date, attempt status, failure reason when applicable, and
relevant timestamps.

When delivery fails, preserve the attempt as FAILED, release or update the
agent's availability as appropriate, notify the customer, and allow the customer
to select a new delivery date. Rescheduling creates a new DeliveryAttempt and
does not reuse or overwrite the failed attempt. The previous agent is not
automatically preferred.

## Notification Outbox

Order/status requests must not directly depend on Resend or Twilio being
available.

Within the same database transaction as a business change, the service should
apply the mutation, append immutable history where applicable, and insert an
outbox event. After commit, a separate worker processes pending events.

Initial reliability semantics:

- worker processing is at least once
- notification records are idempotent
- uniqueness is based on domain event plus notification channel
- email and SMS are separate delivery channels
- provider failure does not undo an already committed order status
- failed sends can be retried
- bounded retry behavior is documented in `docs/data-model.md`

Provider-specific code must remain outside core order/pricing logic. Kafka,
Redis, Celery, and RabbitMQ are not part of the initial design. The outbox can
be designed so a broker could be introduced later if genuinely needed.

## Frontend Areas

High-level frontend areas are expected to include:

- auth screens for registration and login
- customer quote, charge explanation, and order confirmation
- customer order status and tracking timeline
- customer failed-delivery rescheduling
- admin order management with filters
- admin pricing/zone configuration
- admin assignment controls
- delivery-agent dashboard for assigned orders and status updates

## Planned Deployment Topology

- Vercel hosts the React/Vite frontend.
- Render hosts the FastAPI backend as a web service.
- Render hosts PostgreSQL.
- Render hosts a separate notification/background worker process later.

Deployment policy: complete and validate the required application locally first,
then perform production deployment near the end of implementation. Deployment
configuration will be added later.

## Major Transaction Boundaries

### Quote

Quote calculation reads authoritative configuration but does not create an
order. If the caller later confirms, pricing is recalculated.

### Order Creation

Atomically persist:

- order
- pricing inputs/results snapshot
- initial status-history entry
- relevant outbox event if required

### Status Transition

Atomically:

- validate current state
- update current status
- append history
- create relevant outbox event

### Agent Assignment

Atomically:

- validate the order is assignable
- select/re-check eligible agent
- prevent concurrent double assignment
- assign agent to the active attempt
- change availability
- append status history as applicable
- create outbox event as applicable

### Failed Delivery

Atomically:

- mark attempt failed
- update order state
- append history
- release/update agent availability
- create notification outbox event

### Rescheduling

Atomically:

- preserve the failed attempt
- capture the new delivery date
- create a new delivery attempt
- update order state to RESCHEDULED
- append history
- create relevant outbox event if required

## Later Design Decisions

- Detailed frontend component tree and screen layout.
- Exact provider adapter request/response mapping for Geoapify, Resend, and
  Twilio.
- Deployment configuration files and runtime process definitions.
- Performance tuning beyond the indexes documented in `docs/data-model.md`.
