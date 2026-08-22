# Last-Mile Delivery Tracker - Codex Guide

This repository is for a job-application assignment: a modular-monolith
last-mile delivery management platform.

## Source Of Truth

- Product requirements: `docs/requirements.md`
- Current architecture: `docs/architecture.md`
- Assumptions and unresolved choices: `docs/assumptions.md`
- Planned data model: `docs/data-model.md`
- REST API and permissions: `docs/api-contract.md`
- Test plan: `docs/test-plan.md`

Read the relevant docs before changing code or documentation. Keep assignment
requirements distinct from implementation assumptions.

## Locked Direction

- Backend: Python, FastAPI, Pydantic, synchronous SQLAlchemy 2.x, PostgreSQL,
  Alembic, PyJWT, `pwdlib` with Argon2, pytest.
- Frontend: React, TypeScript, Vite, React Router, Tailwind CSS.
- Integrations: Geoapify, Resend, and Twilio behind small provider boundaries.
- Deployment target: Vercel frontend; Render FastAPI web service, PostgreSQL,
  and later notification/background worker.
- Deployment policy: complete and validate required application functionality
  locally first, then deploy near the end of implementation.
- Architecture: modular monolith.
- Default backend flow: router -> domain/service logic -> SQLAlchemy/PostgreSQL.

## Working Rules

- Read relevant existing code and docs before editing.
- Make the smallest coherent change that satisfies the task.
- Avoid unrelated changes, broad rewrites, and formatting churn.
- Preserve existing business rules unless the task explicitly changes them.
- Avoid unnecessary dependencies and speculative infrastructure.
- Prefer simple, domain-specific code over generic base classes or abstractions.
- Do not add a repository layer unless a concrete problem justifies it.
- Test meaningful behavior, especially pricing, assignment, lifecycle history,
  and authorization.
- Run relevant tests/checks before completion and report what was run.
- Report files changed and validation performed at the end of each task.
- Never expose secrets, commit `.env`, or hardcode provider credentials.
- Ask for explicit justification before introducing major infrastructure.

## Avoid Unless Explicitly Requested

Do not introduce Kafka, Redis, Celery, RabbitMQ, Kubernetes, microservices,
Redux, Next.js, PostGIS, Terraform, generic `BaseService`, generic
`BaseRepository`, or one-off interface/implementation pairs.
