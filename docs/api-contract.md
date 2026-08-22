# API Contract

This document freezes the minimum REST API contract for implementation. It
describes endpoint intent, permissions, pagination, and error semantics only.

## Error Semantics

Use standard FastAPI behavior where appropriate. Domain errors may use concise
`detail` messages compatible with FastAPI `HTTPException`.

- `200 OK`: successful reads/actions.
- `201 Created`: successful resource, order, or account creation.
- `401 Unauthorized`: missing or invalid authentication.
- `403 Forbidden`: authenticated but wrong role or ownership.
- `404 Not Found`: resource does not exist or is not visible to caller.
- `409 Conflict`: valid request conflicts with current business state.
- `422 Unprocessable Entity`: validation failure or semantically unprocessable
  order/quote input.

Examples of `409 Conflict`:

- invalid lifecycle transition
- no available agent
- assignment race lost
- duplicate business configuration where applicable

Examples of `422 Unprocessable Entity`:

- invalid package dimensions
- unsupported service-area postal code
- no applicable active rate card
- malformed request data

Do not build a large custom error framework.

## Pagination

Use offset pagination because assignment scale is small.

Query parameters:

- `page`, default 1, minimum 1
- `page_size`, default 20, minimum 1, maximum 100

Response shape:

- `items`
- `page`
- `page_size`
- `total`
- `pages`

Always use deterministic ordering when pagination is used. Admin orders default
to `created_at DESC, id DESC`. Do not implement cursor pagination initially.

## Permission Matrix

| Capability | CUSTOMER | DELIVERY_AGENT | ADMIN |
| --- | --- | --- | --- |
| Register/login | Yes | Login only | Login only |
| Read self | Yes | Yes | Yes |
| Quote | Yes | No | Yes |
| Create own order | Yes | No | No |
| List/read own orders | Yes | No | No |
| View own tracking | Yes | No | No |
| Reschedule own failed order | Yes | No | No |
| Update own location | No | Yes | No |
| Update permitted availability | No | Yes | No |
| List/read assigned orders | No | Yes | No |
| Perform permitted delivery transitions | No | Yes | No |
| Create order for customer | No | No | Yes |
| Read/filter all orders | No | No | Yes |
| Manage zones/areas | No | No | Yes |
| Manage rate cards/COD surcharge | No | No | Yes |
| Create/list agents | No | No | Yes |
| Manual/auto assignment | No | No | Yes |
| Status override | No | No | Yes |

Customers cannot access another customer's order by guessing an id. Agents
cannot access another agent's orders by guessing an id.

## Health

### GET /health

Public.

Returns service health.

## Authentication

### POST /auth/register

Public.

Creates CUSTOMER accounts only.

Request includes:

- `name`
- `email`
- `phone`
- `password`

Returns `201 Created`.

### POST /auth/login

Public.

Authenticates a user and returns a bearer access token.

### GET /auth/me

Any authenticated role.

Returns the current authenticated user.

## Quotes

### POST /orders/quote

Allowed roles:

- CUSTOMER
- ADMIN

Request includes:

- pickup address
- drop address
- package dimensions
- actual weight
- order type
- payment type

Response includes:

- pickup zone
- drop zone
- actual weight
- volumetric weight
- billable weight
- rate per kg
- delivery charge
- COD surcharge
- total charge

Quote calculation does not persist an order.

## Customer Orders

### POST /orders

CUSTOMER only.

Creates the caller's own order. The backend geocodes and recalculates
authoritative pricing again. Frontend-submitted totals are ignored.

Returns `201 Created`.

### GET /orders

CUSTOMER only.

Returns only the caller's orders. Uses pagination.

### GET /orders/{order_id}

Allowed:

- CUSTOMER owner
- ADMIN for any order
- assigned DELIVERY_AGENT for their assigned order

### GET /orders/{order_id}/tracking

Same access rules as order detail.

Returns the immutable status timeline ordered by `created_at ASC, id ASC`.

### POST /orders/{order_id}/reschedule

CUSTOMER owner only.

Allowed only when the order is FAILED.

Request includes:

- `scheduled_date`

`scheduled_date` must be a future date at request time.

Effect:

- create next delivery attempt
- keep failed attempt unchanged
- transition order to RESCHEDULED
- append history

## Agent Endpoints

### GET /agent/orders

DELIVERY_AGENT only.

Returns orders currently or recently assigned to that agent. Supports
pagination.

### PATCH /agent/availability

DELIVERY_AGENT only.

Agent may control AVAILABLE/OFFLINE when not BUSY. Application business logic
controls BUSY. An agent cannot manually change BUSY to AVAILABLE while an active
assignment exists.

### PATCH /agent/location

DELIVERY_AGENT only.

Request includes:

- `latitude`
- `longitude`

Updates current location. Current zone may be updated if it can be derived from
configured areas or known location metadata; otherwise current zone may remain
nullable.

No continuous GPS streaming initially.

### PATCH /agent/orders/{order_id}/status

DELIVERY_AGENT only.

Only the current assigned agent may use this endpoint.

Request includes:

- `target_status`
- optional `reason` or failure reason where relevant

Agents can perform only normal delivery transitions for their currently assigned
order.

## Admin Agents

### POST /admin/agents

ADMIN only.

Creates:

- DELIVERY_AGENT user
- agent profile

Returns `201 Created`.

### GET /admin/agents

ADMIN only.

Simple paginated list including availability and current zone.

## Admin Configuration

All endpoints in this section are ADMIN only. Do not add DELETE endpoints
initially; use active/inactive configuration instead.

### Zones

- `GET /admin/zones`
- `POST /admin/zones`
- `PATCH /admin/zones/{zone_id}`

### Areas

- `GET /admin/areas`
- `POST /admin/areas`
- `PATCH /admin/areas/{area_id}`

### Rate Cards

- `GET /admin/rate-cards`
- `POST /admin/rate-cards`
- `PATCH /admin/rate-cards/{rate_card_id}`

### COD Surcharges

- `GET /admin/cod-surcharges`
- `PUT /admin/cod-surcharges/{order_type}`

PUT acts as create/update for that order type.

## Admin Orders

### POST /admin/orders

ADMIN only.

Creates an order on behalf of an existing CUSTOMER.

Request includes:

- `customer_id`
- normal order input

Backend calculates authoritative price.

Returns `201 Created`.

### GET /admin/orders

ADMIN only.

Filters:

- `status`
- `zone_id`
- `agent_id`

`zone_id` matches either pickup zone or drop zone.

Uses pagination.

Default ordering:

- `created_at DESC`
- `id DESC`

### POST /admin/orders/{order_id}/assign

ADMIN only.

Manual assignment.

Request includes:

- `agent_id`

Allowed from CREATED or RESCHEDULED. Validates the selected agent is eligible
and AVAILABLE.

### POST /admin/orders/{order_id}/auto-assign

ADMIN only.

Runs nearest-available-agent algorithm.

If no eligible agent exists, returns `409 Conflict` and leaves the order
unchanged.

### POST /admin/orders/{order_id}/override-status

ADMIN only.

Request includes:

- `target_status`
- required non-empty `reason`

The override bypasses the normal transition graph but must maintain
delivery-attempt and agent-availability consistency.

## Frontend Areas Supported By API

Customer:

- auth
- dashboard/orders
- create/quote/confirm
- order details
- timeline
- reschedule

Agent:

- availability/location
- assigned orders
- status updates/failure

Admin:

- orders/filtering
- agents
- zones/areas
- rates/COD surcharge
- assignment
- status override

Frontend component trees are intentionally not designed yet.
