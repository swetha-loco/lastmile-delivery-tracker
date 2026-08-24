# Data Model

This document freezes the minimum relational model for implementation. Use
PostgreSQL as the source of truth, integer primary keys, database foreign keys,
timezone-aware timestamps, and UTC in storage.

## Enums

### UserRole

- CUSTOMER
- DELIVERY_AGENT
- ADMIN

### OrderType

- B2B
- B2C

### PaymentType

- PREPAID
- COD

### OrderStatus

Assignment-defined delivery statuses:

- PICKED_UP
- IN_TRANSIT
- OUT_FOR_DELIVERY
- DELIVERED
- FAILED

Internal workflow statuses:

- CREATED
- ASSIGNED
- RESCHEDULED

### AgentAvailability

- AVAILABLE
- BUSY
- OFFLINE

### DeliveryAttemptStatus

- PLANNED
- IN_PROGRESS
- DELIVERED
- FAILED

### NotificationChannel

- EMAIL
- SMS

### NotificationStatus

- PENDING
- RETRY
- SENT
- FAILED

## Tables

### users

Columns:

- `id`
- `name`
- `email`
- `phone`
- `password_hash`
- `role`
- `created_at`
- `updated_at`

Rules and constraints:

- `email` is required and unique.
- Email is normalized to lowercase in application logic.
- `phone` is required for CUSTOMER registration because SMS notification is
  required.
- `phone` may be nullable for non-customer roles.
- Passwords are never stored directly.
- Public registration creates CUSTOMER accounts only.
- ADMIN accounts are initially seeded.
- Delivery-agent accounts can be created by an admin and may be seeded for
  demos.

Authentication decisions:

- Access-token JWT only.
- 60-minute expiration.
- Signing secret comes from environment configuration.
- No refresh-token or session table initially.

Indexes:

- Unique index on `email`.

### zones

Columns:

- `id`
- `name`
- `is_active`
- `created_at`
- `updated_at`

Rules and constraints:

- Zone name is unique.
- Name must be non-empty.

### areas

Columns:

- `id`
- `name`
- `postal_code`
- `zone_id`
- `is_active`
- `created_at`
- `updated_at`

Rules and constraints:

- Every area belongs to exactly one zone.
- Normalized postal code is unique.
- Do not assume postal codes are numeric or exactly six digits.
- Unsupported postal codes fail quote/order processing instead of being guessed.

Indexes:

- Unique index on `postal_code`.
- Index on `zone_id` for admin zone-related lookups.

### rate_cards

Columns:

- `id`
- `origin_zone_id`
- `destination_zone_id`
- `order_type`
- `rate_per_kg`
- `is_active`
- `created_at`
- `updated_at`

Rules and constraints:

- Origin and destination reference valid zones.
- `rate_per_kg > 0`.
- One configured row per `(origin_zone_id, destination_zone_id, order_type)`.
- Same origin/destination zone means intra-zone pricing.
- Different origin/destination zones means inter-zone pricing.

Not included initially:

- slabs
- minimum charges
- first/additional kg fields
- taxes
- discounts
- fuel charges

Indexes:

- Unique composite index on
  `(origin_zone_id, destination_zone_id, order_type)`.

### cod_surcharges

Columns:

- `id`
- `order_type`
- `amount`
- `is_active`
- `created_at`
- `updated_at`

Rules and constraints:

- One row per order type.
- `amount >= 0`.

Indexes:

- Unique index on `order_type`.

### agent_profiles

One-to-one delivery-agent profile. Primary key is also a foreign key to
`users.id`.

Columns:

- `user_id`
- `availability`
- `current_latitude`
- `current_longitude`
- `current_zone_id`
- `location_updated_at`
- `last_assigned_at`

Rules and constraints:

- `user_id` references a DELIVERY_AGENT user.
- Latitude and longitude are either both present or both absent.
- Latitude range is `-90` to `90`.
- Longitude range is `-180` to `180`.
- `current_zone_id` may be nullable and represents the latest known zone.
- Availability is explicit and is not inferred solely from order records.
- Do not create a continuous GPS history table initially.

Indexes:

- Index on `availability`.
- Index on `current_zone_id` for zone fallback assignment.
- Index on `last_assigned_at` for deterministic assignment ranking.

### orders

The order represents the shipment and stores immutable pricing snapshots.

Ownership columns:

- `id`
- `customer_id`
- `created_by_id`

Pickup snapshot:

- `pickup_address`
- `pickup_postal_code`
- `pickup_latitude`
- `pickup_longitude`
- `pickup_zone_id`

Drop snapshot:

- `drop_address`
- `drop_postal_code`
- `drop_latitude`
- `drop_longitude`
- `drop_zone_id`

Package columns:

- `length_cm`
- `breadth_cm`
- `height_cm`
- `package_description`
- `is_fragile`
- `delivery_instructions`
- `actual_weight_kg`
- `volumetric_weight_kg`
- `billable_weight_kg`

Commercial snapshot:

- `order_type`
- `payment_type`
- `rate_card_id`
- `rate_per_kg`
- `delivery_charge`
- `cod_surcharge`
- `total_charge`

Current workflow snapshot:

- `current_status`
- `current_agent_id`

Metadata:

- `created_at`
- `updated_at`

Rules and constraints:

- `customer_id` is the customer receiving/placing the shipment.
- `created_by_id` is the customer or admin who created the order.
- Input dimensions must be greater than 0.
- Actual weight must be greater than 0.
- `package_description` and `delivery_instructions` are optional operational
  handling fields and do not affect pricing.
- `is_fragile` defaults to false and does not add a surcharge.
- Calculated weights must be greater than 0.
- Monetary amounts cannot be negative.
- `rate_per_kg` must be positive.
- `current_agent_id` is nullable and references an agent profile.
- All calculated commercial values are snapshots.
- Later rate-card edits must never recalculate historical orders automatically.
- Do not store arbitrary frontend-supplied totals.

Decimal policy:

- Weights use 3 decimal places.
- Money uses 2 decimal places.
- Business calculations use Decimal and final money uses ROUND_HALF_UP.

Indexes:

- Index on `customer_id` for customer order listing.
- Index on `current_status` for status filtering.
- Index on `current_agent_id` for agent filtering and assigned-agent reads.
- Index on `pickup_zone_id` for admin zone filtering.
- Index on `drop_zone_id` for admin zone filtering.
- Index on `created_at` for default ordering.

Avoid broad composite indexes until query plans justify them.

### order_status_history

Immutable timeline table.

Columns:

- `id`
- `order_id`
- `from_status`
- `to_status`
- `actor_id`
- `actor_role`
- `reason`
- `created_at`

Rules and constraints:

- Initial CREATED event may have null `from_status`.
- `actor_role` is snapshotted.
- `reason` is optional for normal transitions.
- Admin override reason is mandatory.
- Application code must never update or delete historical rows.
- Normal timeline ordering is `created_at ASC, id ASC`.

Indexes:

- Composite index on `(order_id, created_at, id)` for timeline retrieval.

### delivery_attempts

Columns:

- `id`
- `order_id`
- `attempt_number`
- `agent_id`
- `scheduled_date`
- `status`
- `failure_reason`
- `started_at`
- `completed_at`
- `created_at`
- `updated_at`

Rules and constraints:

- `(order_id, attempt_number)` is unique.
- `agent_id` may initially be null for a rescheduled attempt awaiting
  assignment.
- Failure reason is required when an attempt becomes FAILED.
- Failed/completed attempts remain historical.
- Never overwrite a failed attempt to turn it into the next attempt.

Initial behavior:

- First assignment creates attempt 1, attaches the selected agent, and sets
  status to PLANNED.
- PICKED_UP moves the current attempt to IN_PROGRESS and sets `started_at` if
  not already set.
- DELIVERED moves the current attempt to DELIVERED, populates `completed_at`,
  and releases the agent from BUSY.
- FAILED moves the current attempt to FAILED, requires failure reason, populates
  `completed_at`, releases the agent, and creates a customer notification event.
- Reschedule creates the next attempt number with requested `scheduled_date`,
  null agent, PLANNED status, and order status RESCHEDULED.
- A later assignment associates an eligible agent with the new attempt and
  transitions the order to ASSIGNED.
- The previous failed agent is not automatically reused.

Indexes:

- Index on `order_id`.
- Index on `agent_id`.
- Unique index on `(order_id, attempt_number)`.

### outbox_events

Immutable notification-producing domain events.

Columns:

- `id`
- `event_type`
- `order_id`
- `payload`
- `created_at`

Rules and constraints:

- `payload` uses PostgreSQL JSON/JSONB.
- Events are inserted in the same transaction as the business change.
- Historical outbox event payloads are not mutated.

### notification_deliveries

Rows processed by the notification worker.

Columns:

- `id`
- `event_id`
- `channel`
- `recipient`
- `status`
- `attempt_count`
- `next_attempt_at`
- `provider_message_id`
- `last_error`
- `sent_at`
- `created_at`
- `updated_at`

Rules and constraints:

- `(event_id, channel)` is unique.
- Worker processes delivery rows instead of request handlers calling email/SMS.
- Email and SMS delivery can succeed or fail independently.

Retry policy:

- Maximum 5 total send attempts per channel.
- First attempt may occur immediately.
- Retry delays after failures: 1 minute, 5 minutes, 15 minutes, 60 minutes.
- After the fifth failed attempt, status becomes FAILED.
- Provider failure never rolls back an already committed business transaction.
- Successful channels are not resent merely because another channel failed.
- Policy should be configurable in code later without generic retry
  infrastructure.

Indexes:

- Unique index on `(event_id, channel)`.
- Index on `(status, next_attempt_at)` for worker lookup.

## Lifecycle Rules

Normal workflow:

- `CREATED -> ASSIGNED`
- `ASSIGNED -> PICKED_UP`
- `PICKED_UP -> IN_TRANSIT`
- `IN_TRANSIT -> OUT_FOR_DELIVERY`
- `OUT_FOR_DELIVERY -> DELIVERED`
- `OUT_FOR_DELIVERY -> FAILED`
- `FAILED -> RESCHEDULED`
- `RESCHEDULED -> ASSIGNED`

Normal delivery agents may only perform transitions appropriate to their
currently assigned order.

Customer rescheduling performs `FAILED -> RESCHEDULED`.

Admin assignment performs `CREATED -> ASSIGNED` or `RESCHEDULED -> ASSIGNED`.

Invalid normal transitions return a business conflict and do not silently change
state.

Admin status override may bypass the normal graph, but it must require a
non-empty reason, append history, maintain delivery-attempt and
agent-availability consistency, and never bypass database integrity rules.

One lifecycle/service boundary should own status-transition invariants.

## Assignment Concurrency

The important race is two orders attempting to assign the same AVAILABLE agent.

Assignment uses a PostgreSQL transaction and row-level locking, such as
`SELECT ... FOR UPDATE` through SQLAlchemy.

Assignment must:

1. verify the order is assignable
2. find eligible AVAILABLE candidates
3. choose the nearest candidate
4. lock/re-check the selected agent before assigning
5. ensure it is still AVAILABLE
6. associate it with the order/current attempt
7. mark the agent BUSY
8. set `last_assigned_at`
9. transition the order to ASSIGNED
10. append history
11. commit atomically

If availability changed while waiting, retry candidate selection or report no
available agent. Do not use distributed locks or Redis.

Auto-assignment ranking:

- Only AVAILABLE agents are candidates.
- Agents with valid coordinates are ranked by Haversine distance to pickup
  location.
- Smallest distance wins.
- Ties prefer the least recently assigned agent using `last_assigned_at`.
- Final deterministic tie-breaker is agent user id.
- If no AVAILABLE agent has usable coordinates, consider AVAILABLE agents whose
  `current_zone_id` equals pickup zone, then prefer least recently assigned and
  finally lower id.
- If still no eligible agent exists, leave the order unchanged/unassigned and
  return a business conflict.

## Index Discipline

Indexes in this document are justified by expected quote lookup, admin filters,
customer/agent order lists, timeline retrieval, uniqueness, and worker polling.
Measure query plans before adding further indexes.
