# Test Plan

Prioritize business correctness over coverage percentage. Do not add
meaningless tests solely to increase coverage.

## Pricing

Test:

- actual weight greater than volumetric weight
- volumetric weight greater than actual weight
- equal actual and volumetric weights
- B2B rate selection
- B2C rate selection
- intra-zone pricing
- inter-zone pricing
- PREPAID without COD surcharge
- COD with configured surcharge
- unsupported service-area postal code
- inactive or missing rate card
- negative measurements rejected
- zero measurements rejected
- Decimal rounding for final money

## Authentication And RBAC

Test:

- registration creates CUSTOMER
- password is hashed
- login succeeds with valid credentials
- login fails with invalid credentials
- role restrictions
- customer cannot access another customer's order
- agent cannot access another agent's assignment
- admin permissions
- JWT expiration behavior at a representative level

## Orders

Test:

- quote persists nothing
- order confirmation recalculates price
- frontend-submitted totals are not trusted
- historical price remains unchanged after rate-card edit
- admin can create an order on behalf of a customer
- customer order listing returns only caller's orders
- admin filtering by status, zone, and agent
- deterministic pagination ordering

## Lifecycle And History

Test:

- every valid normal transition
- important invalid transitions return conflict
- immutable history sequence
- timeline ordering by timestamp and id
- actor and actor role are captured
- timestamp is captured
- admin override reason is required
- admin override appends history
- historical rows are not updated or deleted by application behavior

## Agent Assignment

Test:

- only AVAILABLE candidates are considered
- nearest coordinates wins
- BUSY agents are ignored
- OFFLINE agents are ignored
- least-recently-assigned tie behavior
- deterministic id tie-breaker
- zone fallback when no coordinates are usable
- no candidate returns 409 and does not mutate order
- assignment marks selected agent BUSY
- assignment sets `last_assigned_at`
- manual assignment validates selected agent eligibility
- concurrency test demonstrates the same agent cannot be successfully assigned
  to two orders

## Failed Delivery And Rescheduling

Test:

- failure reason is required
- failed attempt is preserved
- customer notification event is recorded
- previous agent is released
- reschedule creates the next attempt number
- previous attempt remains unchanged
- new attempt starts with null agent and PLANNED status
- reassignment uses the new attempt
- previous failed agent is not automatically preferred

## Notifications

Use fake providers. Automated tests must not call real providers.

Test:

- email send success
- SMS send success
- one channel can succeed while another retries
- idempotency prevents duplicate send after success
- retry schedule: 1 minute, 5 minutes, 15 minutes, 60 minutes
- terminal failure after fifth attempt
- provider outage never rolls back order status
- successful channel is not resent because another channel failed

## API

Integration tests should cover representative:

- `201 Created`
- `401 Unauthorized`
- `403 Forbidden`
- `404 Not Found`
- `409 Conflict`
- `422 Unprocessable Entity`

Also cover:

- pagination shape
- ownership filtering
- concise FastAPI-compatible error details

## Database And Migrations

Later validate:

- fresh database can migrate from zero to head
- important unique constraints behave correctly
- important check constraints behave correctly
- foreign keys prevent orphaned records
- assignment row-locking behavior protects against double assignment

## Frontend Contract

When frontend work begins, test representative flows supported by the API:

- customer auth
- customer quote and confirm
- customer order details and timeline
- customer failed-delivery reschedule
- agent availability/location
- agent assigned orders
- agent status update and failure
- admin order filters
- admin agents
- admin zones/areas
- admin rates/COD surcharge
- admin assignment
- admin status override
