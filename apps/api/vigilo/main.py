from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, status

from .domain.clock import Clock, SimulatedClock, SystemClock
from .domain.dispatch import DispatchError, DispatchRequest, DispatchService
from .domain.errors import ErrorCode, StateTransitionError, VigiloError
from .domain.models import (
    Batch,
    Donor,
    GeoLocation,
    ItemRules,
    ReceivingHours,
    Rider,
    RiderStatus,
    Shelter,
    ShelterStatus,
    StorageRequirement,
    User,
    UserRole,
)
from .domain.schemas import (
    AllocationResponseSchema,
    BatchCreateSchema,
    BatchResponseSchema,
    ClockAdvanceSchema,
    ClockResponseSchema,
    CompensatingAdjustmentSchema,
    DeliveryResponseSchema,
    DispatchPayloadSchema,
    DispatchPreviewResponseSchema,
    IncidentResponseSchema,
    InventoryBalanceSnapshotSchema,
    InventoryLedgerEntryResponseSchema,
    ItemRulesSchema,
    OperationalEventResponseSchema,
    ReconciliationReportResponseSchema,
    RiderCreateSchema,
    RiderResponseSchema,
    RiderStatusUpdateSchema,
    ShelterCreateSchema,
    ShelterDemandUpdateSchema,
    ShelterResponseSchema,
    ShelterStatusUpdateSchema,
    UserCreateSchema,
    UserResponseSchema,
)
from .domain.ledger import InventoryState
from .domain.state_machines import RiderStateMachine, ShelterStateMachine

load_dotenv()

app = FastAPI(
    title="Vigilo Backend",
    version="0.1.0",
    description="Authoritative backend foundation for the Vigilo resilience-aware logistics engine",
)


# Global clock & domain service initialization
clock_mode = os.getenv("CLOCK_MODE", "SIMULATED")
if clock_mode == "SYSTEM":
    global_clock: Clock = SystemClock()
else:
    global_clock = SimulatedClock(datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc))


def _create_service(clock: Clock) -> DispatchService:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        from .infrastructure.postgres_backend import PostgresDispatchService

        return PostgresDispatchService(database_url)

    secret_key = os.getenv("SUPABASE_SECRET_KEY")
    if secret_key:
        supabase_url = os.getenv("SUPABASE_URL", "https://gryfvlipyoxdxhllmbqc.supabase.co")
        from .infrastructure.supabase_backend import SupabaseDispatchService

        return SupabaseDispatchService(supabase_url, secret_key)

    service = DispatchService(clock=clock)
    service.load_seed(clock.now())
    return service


service = _create_service(global_clock)


# -----------------------------------------------------------------------------
# System & Clock Endpoints
# -----------------------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/clock", response_model=ClockResponseSchema)
def get_clock() -> ClockResponseSchema:
    now = global_clock.now()
    clock_type = "SimulatedClock" if isinstance(global_clock, SimulatedClock) else "SystemClock"
    return ClockResponseSchema(current_time=now, iso=now.isoformat(), clock_type=clock_type)


@app.post("/v1/clock/advance", response_model=ClockResponseSchema)
def advance_clock(payload: ClockAdvanceSchema) -> ClockResponseSchema:
    if not isinstance(global_clock, SimulatedClock):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clock advance is only supported when CLOCK_MODE is SIMULATED.",
        )
    total_seconds = payload.seconds + (payload.minutes * 60)
    new_time = global_clock.advance(total_seconds)
    return ClockResponseSchema(current_time=new_time, iso=new_time.isoformat(), clock_type="SimulatedClock")


@app.post("/v1/seed", status_code=status.HTTP_200_OK)
def reset_seed_data() -> dict[str, Any]:
    if isinstance(service, DispatchService):
        service.load_seed(global_clock.now())
        return {
            "status": "seeded",
            "batches_count": len(service.batches),
            "riders_count": len(service.riders),
            "shelters_count": len(service.shelters),
            "users_count": len(service.users),
        }
    return {"status": "skipped", "message": "External database provider active; use SQL migration seeds"}


# -----------------------------------------------------------------------------
# Batch Endpoints
# -----------------------------------------------------------------------------

@app.get("/v1/batches", response_model=list[BatchResponseSchema])
def list_batches() -> list[BatchResponseSchema]:
    if not isinstance(service, DispatchService):
        return []
    result = []
    for b in service.batches.values():
        result.append(_serialize_batch(b))
    return result


@app.get("/v1/batches/{batch_id}", response_model=BatchResponseSchema)
def get_batch(batch_id: str) -> BatchResponseSchema:
    if not isinstance(service, DispatchService) or batch_id not in service.batches:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch '{batch_id}' not found")
    return _serialize_batch(service.batches[batch_id])


@app.post("/v1/batches", response_model=BatchResponseSchema, status_code=status.HTTP_201_CREATED)
def create_batch(payload: BatchCreateSchema) -> BatchResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Write requires in-memory or full Phase 2 DB")
    if payload.id in service.batches:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Batch '{payload.id}' already exists")

    created_at = payload.created_at or global_clock.now()
    rules = ItemRules(
        safe_handling_minutes=payload.item_rules.safe_handling_minutes,
        safety_buffer_minutes=payload.item_rules.safety_buffer_minutes,
        required_prerequisites=frozenset(payload.item_rules.required_prerequisites),
        storage_requirement=payload.item_rules.storage_requirement,
    )
    batch = Batch(
        id=payload.id,
        donor_id=payload.donor_id,
        item_type=payload.item_type,
        original_quantity=payload.original_quantity,
        available_quantity=payload.original_quantity,
        item_rules=rules,
        created_at=created_at,
    )
    service.batches[batch.id] = batch
    service.ledger.record_intake(batch, reason="API batch intake")
    service.record_event(
        event_type="DONATION_BATCH_CREATED",
        aggregate_id=batch.id,
        aggregate_type="Batch",
        payload={"original_quantity": batch.original_quantity, "item_type": batch.item_type},
    )
    return _serialize_batch(batch)


@app.get("/v1/batches/{batch_id}/ledger", response_model=list[InventoryLedgerEntryResponseSchema])
def get_batch_ledger(batch_id: str) -> list[InventoryLedgerEntryResponseSchema]:
    if not isinstance(service, DispatchService) or batch_id not in service.batches:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch '{batch_id}' not found")
    entries = service.get_batch_ledger(batch_id)
    return [_serialize_ledger_entry(e) for e in entries]


@app.get("/v1/batches/{batch_id}/reconcile", response_model=ReconciliationReportResponseSchema)
def reconcile_batch(batch_id: str) -> ReconciliationReportResponseSchema:
    if not isinstance(service, DispatchService) or batch_id not in service.batches:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch '{batch_id}' not found")
    report = service.reconcile_batch(batch_id)
    return ReconciliationReportResponseSchema(
        batch_id=report.batch_id,
        original_quantity=report.original_quantity,
        current_balance=InventoryBalanceSnapshotSchema(**report.current_balance.to_dict()),
        reconciled_balance=InventoryBalanceSnapshotSchema(**report.reconciled_balance.to_dict()),
        is_valid=report.is_valid,
        entry_count=report.entry_count,
        discrepancies=report.discrepancies,
        checked_at=report.checked_at,
    )


@app.post("/v1/batches/{batch_id}/adjustments", response_model=InventoryLedgerEntryResponseSchema, status_code=status.HTTP_201_CREATED)
def record_batch_adjustment(batch_id: str, payload: CompensatingAdjustmentSchema) -> InventoryLedgerEntryResponseSchema:
    if not isinstance(service, DispatchService) or batch_id not in service.batches:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch '{batch_id}' not found")
    batch = service.batches[batch_id]
    try:
        from_state = InventoryState(payload.from_state)
        to_state = InventoryState(payload.to_state)
        entry = service.ledger.record_compensating_adjustment(
            batch=batch,
            quantity=payload.quantity,
            from_state=from_state,
            to_state=to_state,
            actor=payload.actor,
            reason=payload.reason,
            idempotency_key=payload.idempotency_key,
        )
        return _serialize_ledger_entry(entry)
    except VigiloError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.to_dict()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc



# -----------------------------------------------------------------------------
# Rider Endpoints
# -----------------------------------------------------------------------------

@app.get("/v1/riders", response_model=list[RiderResponseSchema])
def list_riders() -> list[RiderResponseSchema]:
    if not isinstance(service, DispatchService):
        return []
    return [_serialize_rider(r) for r in service.riders.values()]


@app.get("/v1/riders/{rider_id}", response_model=RiderResponseSchema)
def get_rider(rider_id: str) -> RiderResponseSchema:
    if not isinstance(service, DispatchService) or rider_id not in service.riders:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rider '{rider_id}' not found")
    return _serialize_rider(service.riders[rider_id])


@app.post("/v1/riders", response_model=RiderResponseSchema, status_code=status.HTTP_201_CREATED)
def create_rider(payload: RiderCreateSchema) -> RiderResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Write requires in-memory or full Phase 2 DB")
    if payload.id in service.riders:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Rider '{payload.id}' already exists")

    loc = GeoLocation(payload.location.latitude, payload.location.longitude) if payload.location else None
    rider = Rider(
        id=payload.id,
        capacity=payload.capacity,
        user_id=payload.user_id,
        status=payload.status,
        available=(payload.status == RiderStatus.AVAILABLE),
        location=loc,
        last_heartbeat_at=global_clock.now(),
    )
    service.riders[rider.id] = rider
    return _serialize_rider(rider)


@app.patch("/v1/riders/{rider_id}/status", response_model=RiderResponseSchema)
def update_rider_status(rider_id: str, payload: RiderStatusUpdateSchema) -> RiderResponseSchema:
    if not isinstance(service, DispatchService) or rider_id not in service.riders:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rider '{rider_id}' not found")
    rider = service.riders[rider_id]

    try:
        RiderStateMachine.validate_transition(rider.status, payload.status, rider_id=rider.id)
    except StateTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.to_dict()) from exc

    rider.status = payload.status
    if payload.available is not None:
        rider.available = payload.available
    else:
        rider.available = (payload.status == RiderStatus.AVAILABLE)

    service.record_event(
        event_type="RIDER_STATUS_CHANGED",
        aggregate_id=rider.id,
        aggregate_type="Rider",
        payload={"status": rider.status.value, "available": rider.available},
    )
    return _serialize_rider(rider)


@app.post("/v1/riders/{rider_id}/heartbeat", response_model=RiderResponseSchema)
def rider_heartbeat(rider_id: str) -> RiderResponseSchema:
    if not isinstance(service, DispatchService) or rider_id not in service.riders:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rider '{rider_id}' not found")
    rider = service.riders[rider_id]
    rider.last_heartbeat_at = global_clock.now()
    service.record_event(
        event_type="RIDER_HEARTBEAT_RECORDED",
        aggregate_id=rider.id,
        aggregate_type="Rider",
        payload={"last_heartbeat_at": rider.last_heartbeat_at.isoformat()},
    )
    return _serialize_rider(rider)


# -----------------------------------------------------------------------------
# Shelter Endpoints
# -----------------------------------------------------------------------------

@app.get("/v1/shelters", response_model=list[ShelterResponseSchema])
def list_shelters() -> list[ShelterResponseSchema]:
    if not isinstance(service, DispatchService):
        return []
    return [_serialize_shelter(s) for s in service.shelters.values()]


@app.get("/v1/shelters/{shelter_id}", response_model=ShelterResponseSchema)
def get_shelter(shelter_id: str) -> ShelterResponseSchema:
    if not isinstance(service, DispatchService) or shelter_id not in service.shelters:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Shelter '{shelter_id}' not found")
    return _serialize_shelter(service.shelters[shelter_id])


@app.post("/v1/shelters", response_model=ShelterResponseSchema, status_code=status.HTTP_201_CREATED)
def create_shelter(payload: ShelterCreateSchema) -> ShelterResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Write requires in-memory or full Phase 2 DB")
    if payload.id in service.shelters:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Shelter '{payload.id}' already exists")

    loc = GeoLocation(payload.location.latitude, payload.location.longitude) if payload.location else None
    hours = ReceivingHours(open_hour=payload.receiving_hours.open_hour, close_hour=payload.receiving_hours.close_hour)
    shelter = Shelter(
        id=payload.id,
        name=payload.name,
        demand_remaining=payload.demand_remaining,
        receiving_capacity_remaining=payload.receiving_capacity_remaining,
        prerequisites=frozenset(payload.prerequisites),
        open=payload.open,
        status=payload.status,
        location=loc,
        receiving_hours=hours,
    )
    service.shelters[shelter.id] = shelter
    return _serialize_shelter(shelter)


@app.patch("/v1/shelters/{shelter_id}/status", response_model=ShelterResponseSchema)
def update_shelter_status(shelter_id: str, payload: ShelterStatusUpdateSchema) -> ShelterResponseSchema:
    if not isinstance(service, DispatchService) or shelter_id not in service.shelters:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Shelter '{shelter_id}' not found")
    shelter = service.shelters[shelter_id]

    try:
        ShelterStateMachine.validate_transition(shelter.status, payload.status, shelter_id=shelter.id)
    except StateTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.to_dict()) from exc

    shelter.status = payload.status
    if payload.open is not None:
        shelter.open = payload.open
    else:
        shelter.open = (payload.status == ShelterStatus.OPEN)

    service.record_event(
        event_type="SHELTER_STATUS_CHANGED",
        aggregate_id=shelter.id,
        aggregate_type="Shelter",
        payload={"status": shelter.status.value, "open": shelter.open},
    )
    return _serialize_shelter(shelter)


@app.patch("/v1/shelters/{shelter_id}/demand", response_model=ShelterResponseSchema)
def update_shelter_demand(shelter_id: str, payload: ShelterDemandUpdateSchema) -> ShelterResponseSchema:
    if not isinstance(service, DispatchService) or shelter_id not in service.shelters:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Shelter '{shelter_id}' not found")
    shelter = service.shelters[shelter_id]
    shelter.demand_remaining = payload.demand_remaining
    if payload.receiving_capacity_remaining is not None:
        shelter.receiving_capacity_remaining = payload.receiving_capacity_remaining
    service.record_event(
        event_type="SHELTER_DEMAND_UPDATED",
        aggregate_id=shelter.id,
        aggregate_type="Shelter",
        payload={"demand_remaining": shelter.demand_remaining, "receiving_capacity_remaining": shelter.receiving_capacity_remaining},
    )
    return _serialize_shelter(shelter)


# -----------------------------------------------------------------------------
# Dispatch Endpoints (Preview & Commit)
# -----------------------------------------------------------------------------

@app.post("/v1/dispatch/preview", response_model=DispatchPreviewResponseSchema)
def preview_dispatch(payload: DispatchPayloadSchema) -> DispatchPreviewResponseSchema:
    req = _to_dispatch_request(payload)
    decision = service.preview(req)
    return DispatchPreviewResponseSchema(
        feasible=decision.feasible,
        reason_code=decision.reason_code,
        reason=decision.reason,
        evidence=decision.evidence,
    )


@app.post("/v1/dispatch/commit", status_code=status.HTTP_201_CREATED)
def commit_dispatch(payload: DispatchPayloadSchema):
    req = _to_dispatch_request(payload)
    try:
        allocation = service.commit(req)
    except DispatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": exc.message, "evidence": exc.evidence},
        ) from exc
    return {
        "allocation_id": allocation.id,
        "state": allocation.state.value if hasattr(allocation.state, "value") else str(allocation.state),
        "batch_id": allocation.batch_id,
        "rider_id": allocation.rider_id,
        "shelter_id": allocation.shelter_id,
        "quantity": allocation.quantity,
    }


# -----------------------------------------------------------------------------
# Allocation & Delivery Endpoints
# -----------------------------------------------------------------------------

@app.get("/v1/allocations/{allocation_id}", response_model=AllocationResponseSchema)
def get_allocation(allocation_id: str) -> AllocationResponseSchema:
    if not isinstance(service, DispatchService) or allocation_id not in service.allocations:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Allocation '{allocation_id}' not found")
    return _serialize_allocation(service.allocations[allocation_id])


@app.post("/v1/allocations/{allocation_id}/acknowledge", response_model=AllocationResponseSchema)
def acknowledge_allocation(allocation_id: str) -> AllocationResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    try:
        alloc = service.acknowledge_allocation(allocation_id)
        return _serialize_allocation(alloc)
    except VigiloError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.to_dict()) from exc


@app.post("/v1/allocations/{allocation_id}/cancel", response_model=AllocationResponseSchema)
def cancel_allocation(allocation_id: str) -> AllocationResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    try:
        alloc = service.expire_allocation(allocation_id, actor="dispatcher", reason="Manual allocation cancellation")
        return _serialize_allocation(alloc)
    except VigiloError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.to_dict()) from exc


@app.post("/v1/allocations/{allocation_id}/pickup", response_model=DeliveryResponseSchema)
def pickup_allocation(allocation_id: str) -> DeliveryResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    try:
        delivery = service.pickup_allocation(allocation_id)
        return _serialize_delivery(delivery)
    except VigiloError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.to_dict()) from exc


@app.get("/v1/deliveries/{delivery_id}", response_model=DeliveryResponseSchema)
def get_delivery(delivery_id: str) -> DeliveryResponseSchema:
    if not isinstance(service, DispatchService) or delivery_id not in service.deliveries:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Delivery '{delivery_id}' not found")
    return _serialize_delivery(service.deliveries[delivery_id])


@app.post("/v1/deliveries/{delivery_id}/deliver", response_model=DeliveryResponseSchema)
def deliver_cargo(delivery_id: str) -> DeliveryResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    try:
        delivery = service.deliver_cargo(delivery_id)
        return _serialize_delivery(delivery)
    except VigiloError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.to_dict()) from exc


# -----------------------------------------------------------------------------
# Telemetry & Operational Events Endpoints
# -----------------------------------------------------------------------------

@app.get("/v1/events", response_model=list[OperationalEventResponseSchema])
def list_events(limit: int = Query(default=50, ge=1, le=200)) -> list[OperationalEventResponseSchema]:
    if not isinstance(service, DispatchService):
        return []
    recent = service.events[-limit:]
    return [
        OperationalEventResponseSchema(
            id=evt.id,
            event_type=str(evt.event_type),
            aggregate_id=evt.aggregate_id,
            aggregate_type=evt.aggregate_type,
            occurred_at=evt.occurred_at,
            payload=evt.payload,
            actor=evt.actor,
            correlation_id=evt.correlation_id,
            evidence=evt.evidence,
        )
        for evt in recent
    ]


@app.get("/v1/incidents", response_model=list[IncidentResponseSchema])
def list_incidents() -> list[IncidentResponseSchema]:
    if not isinstance(service, DispatchService):
        return []
    return [
        IncidentResponseSchema(
            id=inc.id,
            severity=inc.severity,
            status=inc.status,
            affected_entity_type=inc.affected_entity_type,
            affected_entity_id=inc.affected_entity_id,
            reason_code=inc.reason_code,
            description=inc.description,
            created_at=inc.created_at,
            resolved_at=inc.resolved_at,
            evidence=inc.evidence,
        )
        for inc in service.incidents.values()
    ]


# -----------------------------------------------------------------------------
# Helpers & Serializers
# -----------------------------------------------------------------------------

def _to_dispatch_request(payload: DispatchPayloadSchema) -> DispatchRequest:
    now = payload.now or global_clock.now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return DispatchRequest(
        batch_id=payload.batch_id,
        rider_id=payload.rider_id,
        shelter_id=payload.shelter_id,
        quantity=payload.quantity,
        travel_minutes=payload.travel_minutes,
        handoff_minutes=payload.handoff_minutes,
        now=now,
        idempotency_key=payload.idempotency_key,
    )


def _serialize_batch(b: Batch) -> BatchResponseSchema:
    return BatchResponseSchema(
        id=b.id,
        donor_id=b.donor_id,
        item_type=b.item_type,
        original_quantity=b.original_quantity,
        available_quantity=b.available_quantity,
        reserved_quantity=b.reserved_quantity,
        picked_up_quantity=b.picked_up_quantity,
        delivered_quantity=b.delivered_quantity,
        spoiled_quantity=b.spoiled_quantity,
        item_rules=ItemRulesSchema(
            safe_handling_minutes=b.item_rules.safe_handling_minutes,
            safety_buffer_minutes=b.item_rules.safety_buffer_minutes,
            required_prerequisites=sorted(list(b.item_rules.required_prerequisites)),
            storage_requirement=b.item_rules.storage_requirement,
        ),
        created_at=b.created_at,
        safe_until=b.item_rules.safe_until(b.created_at),
    )


def _serialize_rider(r: Rider) -> RiderResponseSchema:
    loc = {"latitude": r.location.latitude, "longitude": r.location.longitude} if r.location else None
    return RiderResponseSchema(
        id=r.id,
        user_id=r.user_id,
        capacity=r.capacity,
        active_load=r.active_load,
        remaining_capacity=r.remaining_capacity,
        available=r.available,
        status=r.status,
        location=loc,
        last_heartbeat_at=r.last_heartbeat_at,
    )


def _serialize_shelter(s: Shelter) -> ShelterResponseSchema:
    loc = {"latitude": s.location.latitude, "longitude": s.location.longitude} if s.location else None
    hours = {"open_hour": s.receiving_hours.open_hour, "close_hour": s.receiving_hours.close_hour}
    return ShelterResponseSchema(
        id=s.id,
        name=s.name,
        demand_remaining=s.demand_remaining,
        receiving_capacity_remaining=s.receiving_capacity_remaining,
        prerequisites=sorted(list(s.prerequisites)),
        open=s.open,
        status=s.status,
        location=loc,
        receiving_hours=hours,
    )


def _serialize_allocation(a) -> AllocationResponseSchema:
    return AllocationResponseSchema(
        id=a.id,
        batch_id=a.batch_id,
        rider_id=a.rider_id,
        shelter_id=a.shelter_id,
        quantity=a.quantity,
        travel_minutes=a.travel_minutes,
        handoff_minutes=a.handoff_minutes,
        state=a.state,
        claimed_at=a.claimed_at,
        lease_expires_at=a.lease_expires_at,
        safe_until=a.safe_until,
        acknowledged_at=a.acknowledged_at,
        picked_up_at=a.picked_up_at,
    )


def _serialize_delivery(d) -> DeliveryResponseSchema:
    loc = {"latitude": d.current_location.latitude, "longitude": d.current_location.longitude} if d.current_location else None
    return DeliveryResponseSchema(
        id=d.id,
        allocation_id=d.allocation_id,
        batch_id=d.batch_id,
        rider_id=d.rider_id,
        current_shelter_id=d.current_shelter_id,
        quantity=d.quantity,
        state=d.state,
        picked_up_at=d.picked_up_at,
        delivered_at=d.delivered_at,
        current_location=loc,
        destination_history=d.destination_history,
    )


def _serialize_ledger_entry(e) -> InventoryLedgerEntryResponseSchema:
    return InventoryLedgerEntryResponseSchema(
        id=e.id,
        batch_id=e.batch_id,
        entry_type=e.entry_type.value,
        quantity=e.quantity,
        from_state=e.from_state.value if e.from_state else None,
        to_state=e.to_state.value,
        actor=e.actor,
        command=e.command,
        reason=e.reason,
        occurred_at=e.occurred_at,
        balance_after=InventoryBalanceSnapshotSchema(**e.balance_after.to_dict()),
        allocation_id=e.allocation_id,
        delivery_id=e.delivery_id,
        idempotency_key=e.idempotency_key,
        correlation_id=e.correlation_id,
        metadata=e.metadata,
    )

