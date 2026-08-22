from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_delivery_agent
from app.models import User
from app.schemas.agent import (
    AgentAvailabilityRequest,
    AgentLocationRequest,
    AgentOrderPage,
    AgentProfileResponse,
    AgentStatusUpdateRequest,
)
from app.schemas.orders import OrderDetail
from app.services import agents as agent_service
from app.services import lifecycle
from app.services import orders as order_service
from app.routers.orders import order_detail

router = APIRouter(prefix="/agent", tags=["agent"])


@router.patch("/location", response_model=AgentProfileResponse)
def update_location(
    payload: AgentLocationRequest,
    agent: Annotated[User, Depends(require_delivery_agent)],
    db: Annotated[Session, Depends(get_db)],
) -> object:
    try:
        profile = agent_service.update_location(
            db,
            agent=agent,
            latitude=payload.latitude,
            longitude=payload.longitude,
        )
        db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.refresh(profile)
    return profile


@router.patch("/availability", response_model=AgentProfileResponse)
def update_availability(
    payload: AgentAvailabilityRequest,
    agent: Annotated[User, Depends(require_delivery_agent)],
    db: Annotated[Session, Depends(get_db)],
) -> object:
    try:
        profile = agent_service.update_availability(
            db, agent=agent, availability=payload.availability
        )
        db.commit()
    except agent_service.AgentAvailabilityError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except agent_service.AgentAvailabilityConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.refresh(profile)
    return profile


@router.get("/orders", response_model=AgentOrderPage)
def list_orders(
    agent: Annotated[User, Depends(require_delivery_agent)],
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, object]:
    return agent_service.list_agent_orders(
        db, agent_id=agent.id, page=page, page_size=page_size
    )


@router.patch("/orders/{order_id}/status", response_model=OrderDetail)
def update_order_status(
    order_id: int,
    payload: AgentStatusUpdateRequest,
    agent: Annotated[User, Depends(require_delivery_agent)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    order = order_service.lock_agent_order(db, order_id=order_id, agent_id=agent.id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if payload.target_status not in lifecycle.AGENT_TARGET_STATUSES:
        raise HTTPException(status_code=409, detail="Invalid agent status target")
    try:
        lifecycle.transition_order(
            db,
            order=order,
            actor=agent,
            target_status=payload.target_status,
            reason=payload.reason,
        )
        db.commit()
    except lifecycle.LifecycleConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.refresh(order)
    return order_detail(order)
