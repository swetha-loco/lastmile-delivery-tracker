# Requirements

This document records the assignment requirements only. Implementation choices
and unresolved decisions belong in `docs/assumptions.md`.

## Functional Requirements

### Users And Authorization

- The system has three roles: CUSTOMER, DELIVERY_AGENT, and ADMIN.
- Customers can register and log in.
- Role-based authorization is required.
- Admins can create orders on behalf of customers.

### Order Input

Each order contains:

- pickup address
- drop address
- package length, breadth, and height
- actual weight
- order type: B2B or B2C
- payment type: PREPAID or COD

### Pricing

The system must:

- detect pickup and drop zones
- calculate volumetric weight as `length x breadth x height / 5000`
- calculate billable weight as the greater of actual and volumetric weight
- select the correct admin-configured rate card based on zones and B2B/B2C order type
- apply the configured COD surcharge when payment type is COD
- calculate charges without hardcoded business rates
- show the charge before the customer confirms the order

Admins manage:

- zones
- areas assigned to zones
- rate cards
- intra-zone and inter-zone pricing
- separate B2B/B2C pricing
- COD surcharge configuration

The assignment does not define the internal mathematical structure of a rate
card beyond the requirements above.

### Agent Assignment

Admins must be able to:

- manually assign an agent
- trigger automatic assignment

Automatic assignment must choose the nearest available delivery agent based on
current location or zone. Agent availability must be explicitly modelled.

### Delivery Lifecycle And Tracking

Delivery agents can update delivery status using:

- PICKED_UP
- IN_TRANSIT
- OUT_FOR_DELIVERY
- DELIVERED
- FAILED

Internal statuses such as CREATED or ASSIGNED may be introduced where needed,
but must be distinguished from statuses explicitly named by the assignment.

Every status change must produce an immutable tracking-history entry containing
at least:

- timestamp
- actor

Customers can view:

- current/live order status
- complete tracking timeline

Admins can override an order's status.

### Failed Deliveries

When delivery fails:

- the customer must be notified
- the failure must be captured
- the customer can choose a new delivery date
- the delivery is rescheduled
- an agent is reassigned for the new attempt

The data model should preserve previous attempts rather than destroying
historical delivery information.

### Notifications

Customers must receive notifications on delivery status changes. The assignment
expects email and SMS.

### Admin Order Management

Admins can:

- view all orders
- filter orders by status
- filter orders by zone
- filter orders by agent
- override status
- manually assign agents
- trigger auto-assignment

## Technical Requirements

- Use a modular monolith.
- Default backend flow: router -> domain/service logic -> SQLAlchemy/PostgreSQL.
- Do not introduce a repository layer unless a concrete problem later justifies it.
- Use Python, FastAPI, Pydantic, synchronous SQLAlchemy 2.x, PostgreSQL,
  Alembic, PyJWT, `pwdlib` with Argon2, and pytest.
- Use React, TypeScript, Vite, React Router, and Tailwind CSS.
- Initial intended integrations are Geoapify for geocoding, Resend for email,
  and Twilio for SMS.
- Keep provider-specific integration code out of core business logic.
- Initial deployment target is Vercel for the frontend and Railway for FastAPI,
  PostgreSQL, and the notification worker.
- Do not introduce Kafka, Redis, Celery, RabbitMQ, Kubernetes, microservices,
  Redux, Next.js, PostGIS, Terraform, generic base services/repositories, or
  single-implementation interface pairs unless explicitly requested later.

## Required Deliverables

Eventually the project must provide:

- complete source code
- README/setup guide
- `.env.example`
- API documentation
- database schema documentation
- explanation of rate calculation logic
- hosted application URL
- system-design write-up of no more than 800 words covering rate calculation,
  zone detection, auto-assignment, and failed-delivery handling

## Evaluation Criteria

Optimize implementation primarily for:

1. rate calculation correctness and design
2. auto-assignment and agent availability modelling
3. lifecycle and immutable tracking history
4. database schema/data modelling
5. API design and code structure
6. documentation
