# Assumptions And Open Decisions

This document separates explicit assignment requirements from implementation
decisions. Items are marked DECIDED or STILL OPEN so later schema and API work
does not drift.

## DECIDED: Units And Validation Policy

- Assignment requires: orders include package length, breadth, height, and
  actual weight, but does not specify units.
- Initial assumption: dimensions are entered in centimeters and weight is entered
  in kilograms.
- Initial validation policy: zero or negative dimensions and weight must be
  rejected later through request validation/domain validation.
- Easy to change later: add display-unit conversion at the API or frontend
  boundary without changing the core pricing formula.

## DECIDED: Numerical Handling

- Assignment requires: volumetric weight, billable weight, and charge
  calculation, but does not specify numeric precision or rounding.
- Initial assumption: use decimal arithmetic for business calculations.
  Dimensions are decimal values. Weights are stored to 3 decimal places. Money
  is stored to 2 decimal places. Currency calculations use Decimal, and final
  monetary amounts use ROUND_HALF_UP to 2 decimal places.
- Not assumed: no rounding of weight to the next 0.5 kg or any other increment,
  because the assignment does not specify it.
- Easy to change later: adjust precision or introduce explicit weight rounding
  if the assignment or product owner later requires it.

## DECIDED: Rate-Card Charging Model

- Assignment requires: choose an admin-configured rate card by pickup/drop zones
  and B2B/B2C order type, use billable weight, apply COD surcharge when needed,
  support intra-zone and inter-zone pricing, and avoid hardcoded business rates.
- Initial assumption: a rate card is identified by origin zone, destination
  zone, and order type, and contains rate per kg plus active/inactive state.
  Origin zone equal to destination zone represents intra-zone pricing. Origin
  zone different from destination zone represents inter-zone pricing.
- Initial formula: delivery charge is `billable_weight * rate_per_kg`. COD
  surcharge is configured separately by order type and added only for COD
  orders.
- Not assumed: minimum charge, weight slabs, first-kg/additional-kg logic, fuel
  surcharge, taxes, or discounts.
- Easy to change later: replace the formula with slabs, minimums, or more
  detailed tariffs while keeping the pricing-service boundary.

## DECIDED: Address To Area And Zone Mapping

- Assignment requires: detect pickup and drop zones; admins manage zones and
  areas assigned to zones.
- Initial assumption: zone detection flows from address -> Geoapify geocoding
  -> normalized postal code -> admin-configured Area -> Zone.
- Initial Area meaning: a supported postal-code/service area assigned to exactly
  one zone.
- Unsupported area behavior: if an address geocodes but its postal code is not
  configured in an active admin-managed Area, reject the quote/order as outside
  configured service areas. Do not guess the zone or choose the geographically
  nearest zone.
- Not assumed: polygon matching or PostGIS.
- Easy to change later: replace postal-code matching with polygon matching or
  more advanced geography without changing pricing logic.

## DECIDED: Quote Behavior

- Assignment requires: show the charge before the customer confirms the order.
- Initial assumption: a quote is not an order. The quote response should expose
  pickup zone, drop zone, actual weight, volumetric weight, billable weight,
  rate per kg, delivery charge, COD surcharge, and total charge.
- Confirmation policy: when the customer confirms, the backend recalculates the
  price from current authoritative configuration and never trusts a total sent
  back by the frontend.
- Historical pricing policy: order creation snapshots the pricing inputs/results
  needed to preserve the historical charge even if admins later change rate
  cards.
- Easy to change later: persist quote records with expirations if needed.

## DECIDED: Live Order Status

- Assignment requires: customers can view current/live order status and complete
  tracking timeline, but does not explicitly require continuous GPS tracking.
- Initial assumption: `orders.current_status` is the latest persisted status,
  immutable tracking history supplies the full timeline, and the frontend
  periodically polls for updates.
- Not assumed: WebSockets, SSE, continuous driver GPS streaming, or live map
  tracking.
- Easy to change later: add push updates or GPS streams behind the tracking API
  without changing the immutable history model.

## DECIDED: Order Lifecycle

- Assignment requires: delivery agents can update PICKED_UP, IN_TRANSIT,
  OUT_FOR_DELIVERY, DELIVERED, and FAILED. Internal statuses such as CREATED or
  ASSIGNED may be introduced if distinguished from assignment-named statuses.
- Initial lifecycle:
  `CREATED -> ASSIGNED -> PICKED_UP -> IN_TRANSIT -> OUT_FOR_DELIVERY -> DELIVERED`
- Failure path: failure may occur after a delivery attempt has begun and results
  in `FAILED`.
- Reschedule path: after the customer chooses a new date,
  `FAILED -> RESCHEDULED -> ASSIGNED -> ...`.
- Internal statuses: CREATED, ASSIGNED, and RESCHEDULED are implementation
  statuses.
- History policy: every actual status transition must atomically update current
  order status and append immutable status history containing from status, to
  status, timestamp, actor/user, actor role, and optional reason.
- Admin override policy: admin overrides create history entries and require an
  override reason.
- Not allowed: application code must not update or delete historical status rows.
- Easy to change later: refine valid transition rules while preserving immutable
  history.

## DECIDED: Agent Availability

- Assignment requires: automatic assignment chooses the nearest available agent,
  and agent availability must be explicitly modelled.
- Initial assumption: delivery-agent availability states are AVAILABLE, BUSY,
  and OFFLINE.
- Initial profile location fields: current latitude, current longitude, current
  zone, and location-updated timestamp.
- Not assumed: availability inferred solely from open orders.
- Easy to change later: add shift schedules or workload limits while preserving
  explicit availability.

## DECIDED: Auto-Assignment Semantics

- Assignment requires: admins can manually assign an agent or trigger automatic
  assignment.
- Initial assumption: creating an order does not automatically assign an agent.
  The order begins as CREATED and unassigned. Admins may manually assign or
  explicitly trigger auto-assignment.
- Candidate rule: auto-assignment candidates must be AVAILABLE.
- Primary algorithm: find AVAILABLE agents with usable current coordinates,
  calculate Haversine distance from each agent to pickup coordinates, select the
  nearest, assign inside a database transaction, re-check/lock availability
  before final assignment, mark the selected agent BUSY, and create appropriate
  assignment/status history.
- Fallback: if no available agent has usable coordinates, consider AVAILABLE
  agents whose current zone equals the pickup zone and choose deterministically.
- No-agent behavior: if there are no eligible agents, leave the order unassigned
  and CREATED, and return/report a clear no-available-agent result.
- Not assumed: route optimization, external routing APIs, PostGIS, or a strategy
  framework.
- Easy to change later: replace the assignment algorithm behind a focused
  assignment service.

## DECIDED: Delivery-Attempt Semantics

- Assignment requires: failed deliveries are captured, customers can choose a
  new date, deliveries are rescheduled, agents are reassigned, and previous
  attempts are preserved.
- Initial assumption: an Order represents the shipment, and a DeliveryAttempt
  represents one actual attempt to deliver it.
- Attempt data conceptually includes order, attempt number, assigned agent,
  scheduled date, attempt status, failure reason when applicable, and relevant
  timestamps.
- Failed attempt behavior: when delivery fails, preserve that attempt as FAILED,
  release or update the current agent from the failed attempt as appropriate,
  notify the customer, and allow the customer to select a new delivery date.
- Reschedule behavior: create a new DeliveryAttempt, do not reuse or overwrite
  the failed attempt, and perform agent assignment again. The previous agent is
  not automatically preferred.
- Easy to change later: refine exact table fields in the schema phase.

## DECIDED: Notification Reliability Semantics

- Assignment requires: customers receive email and SMS notifications on delivery
  status changes.
- Initial assumption: order/status requests must not directly depend on Resend
  or Twilio being available.
- Outbox policy: within the same database transaction as the business change,
  apply the mutation, append immutable history where applicable, and insert an
  outbox event. After commit, a separate worker processes pending events.
- Initial reliability: at-least-once worker processing, idempotent notification
  records, uniqueness based on domain event plus notification channel, separate
  email and SMS channels, provider failure does not undo committed order status,
  and failed sends can be retried.
- Retry policy: bounded retry count and backoff timing are documented in
  `docs/data-model.md`.
- Not assumed: Kafka, Redis, Celery, or RabbitMQ.
- Easy to change later: introduce a broker if genuinely needed because the
  durable outbox isolates business changes from provider delivery.

## DECIDED: External Provider Limits

- Assignment requires: email and SMS notifications; provider choice is an
  implementation decision.
- Initial assumption: Geoapify, Resend, and Twilio may be constrained by
  free-tier quotas, sandbox sending rules, verified sender requirements, or test
  phone restrictions.
- Easy to change later: swap providers because provider-specific code remains
  behind integration boundaries.

## DECIDED: Transaction Boundaries

- Assignment requires: consistent pricing, assignment, lifecycle history, failed
  delivery handling, and notifications.
- Initial assumption: services later own meaningful business transactions rather
  than helper functions committing independently.
- Required conceptual transactions: order creation, status transition, agent
  assignment, failed delivery, and rescheduling, as detailed in
  `docs/architecture.md`.
- Easy to change later: refine isolation levels or locking details during schema
  and API design.

## DECIDED: API Contract And Error Semantics

- Assignment requires: role-based access, customer/admin/agent order workflows,
  admin management, status updates, tracking, and notifications.
- Initial assumption: `docs/api-contract.md` freezes the minimum REST endpoint
  groups, permissions matrix, pagination shape, and error semantics.
- Initial error policy: use standard FastAPI behavior where appropriate, concise
  `HTTPException` details for domain errors, `409 Conflict` for business-state
  conflicts, and `422 Unprocessable Entity` for validation or unprocessable
  quote/order inputs.
- Easy to change later: refine response fields during implementation while
  preserving the documented permissions and status-code intent.

## DECIDED: Database Tables, Constraints, And Indexes

- Assignment requires: persistent users, orders, zones, areas, rate cards, COD
  surcharge configuration, agent availability, tracking history, failed delivery
  attempts, and notifications.
- Initial assumption: `docs/data-model.md` freezes the compact relational table
  plan, enums, useful foreign keys, unique/check constraints, and justified
  indexes.
- Not assumed: audit tables for everything, soft deletion everywhere, event
  sourcing, CQRS, generic metadata columns, or speculative indexes.
- Easy to change later: add measured indexes or fields when implementation or
  query plans demonstrate a need.

## DECIDED: Notification Retry Policy

- Assignment requires: customers receive email and SMS notifications on status
  changes.
- Initial assumption: notification deliveries retry up to 5 total send attempts
  per channel. Retry delays after failures are 1 minute, 5 minutes, 15 minutes,
  and 60 minutes. After the fifth failed attempt, status becomes FAILED.
- Initial idempotency policy: `(event_id, channel)` is unique, successful
  channels are not resent because another channel failed, and real providers are
  replaced by fake providers in automated tests.
- Easy to change later: tune retry timing behind configuration without adding a
  generic retry framework.

## DECIDED: Admin Order Pagination And Filtering

- Assignment requires: admins can view all orders and filter by status, zone,
  and agent.
- Initial assumption: admin order listing supports offset pagination with
  `page` and `page_size`, filters by `status`, `zone_id`, and `agent_id`, treats
  `zone_id` as matching pickup or drop zone, and orders by
  `created_at DESC, id DESC`.
- Easy to change later: add more filters or cursor pagination if measured usage
  justifies it.

## STILL OPEN Before Implementation

No known unresolved planning item currently blocks Phase 1 implementation. New
questions should be recorded here only if they affect schema, API contract, or
core business behavior.

## DECIDED: Deployment Target And Timing

- Assignment deliverable requires: a hosted application URL eventually.
- Current implementation target: Vercel for the React/Vite frontend, Render for
  the FastAPI web service, Render PostgreSQL, and a later Render
  notification/background worker.
- Deployment policy: complete and validate the required application locally
  first, then perform production deployment near the end of implementation.
- Easy to change later: deployment configuration can be adjusted without
  changing the modular-monolith application design.
