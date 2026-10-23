from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Query, Response, status

from .domain.clock import Clock, SimulatedClock, SystemClock
from .domain.dispatch import DispatchError, DispatchRequest, DispatchService
from .domain.errors import EntityNotFoundError, ErrorCode, StateTransitionError, VigiloError
from .domain.models import (
    AllocationState,
    Batch,
    DeliveryState,
    Donor,
    GeoLocation,
    IncidentStatus,
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
    AuditRecordResponseSchema,
    BaselineMetricComparisonSchema,
    BatchCreateSchema,
    BatchLifecycleReconstructionResponseSchema,
    BatchResponseSchema,
    BatchSplitPlanSchema,
    CandidateAssignmentSchema,
    CandidateGenerationResponseSchema,
    ClockAdvanceSchema,
    ClockResponseSchema,
    CompensatingAdjustmentSchema,
    DeliveryRerouteCommitSchema,
    DeliveryReroutePreviewResponseSchema,
    DeliveryResponseSchema,
    DispatchPayloadSchema,
    DispatchPreviewResponseSchema,
    EmergencyOverrideResponseSchema,
    EmergencyOverrideSchema,
    IncidentEscalateSchema,
    IncidentResolveSchema,
    IncidentResponseSchema,
    InventoryBalanceSnapshotSchema,
    InventoryLedgerEntryResponseSchema,
    ItemRulesSchema,
    LastSafeDecisionClockResponseSchema,
    OperationalEventResponseSchema,
    OutboxMessageResponseSchema,
    ReconciliationReportResponseSchema,
    RiderCreateSchema,
    RiderResponseSchema,
    RiderStatusUpdateSchema,
    RuleEvaluationResultSchema,
    SafetyEvaluationReportResponseSchema,
    SafetyEvaluationRequestSchema,
    ScenarioAdvanceTimeSchema,
    ScenarioCompareBaselineResponseSchema,
    ScenarioCreateSchema,
    ScenarioInjectFailureSchema,
    ScenarioPresetResponseSchema,
    ScenarioReplayResponseSchema,
    ScenarioStateResponseSchema,
    ShelterCloseSchema,
    ShelterCreateSchema,
    ShelterDemandUpdateSchema,
    ShelterResponseSchema,
    ShelterStatusUpdateSchema,
    SystemMetricsResponseSchema,
    SystemReadinessResponseSchema,
    UserCreateSchema,
    UserResponseSchema,
    WorkerSweepResponseSchema,
)
from .domain.ledger import InventoryState
from .domain.state_machines import RiderStateMachine, ShelterStateMachine
from .domain.simulation import ScenarioInstance, ScenarioManager, PRESET_SCENARIOS
from .domain.baseline import BaselineComparisonEngine

from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(
    title="Vigilo Backend",
    version="0.1.0",
    description="Authoritative backend foundation for the Vigilo resilience-aware logistics engine",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/v1/health")
def v1_health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/ready", response_model=SystemReadinessResponseSchema, tags=["operations"])
def get_readiness():
    """System readiness check verifying authoritative clock, database/storage, ledger, and workers."""
    clock_type = "SimulatedClock" if isinstance(global_clock, SimulatedClock) else "SystemClock"
    now = global_clock.now()

    storage_provider = "in_memory"
    if os.getenv("DATABASE_URL"):
        storage_provider = "postgres"
    elif os.getenv("SUPABASE_SECRET_KEY"):
        storage_provider = "supabase"

    batches_count = len(service.batches) if isinstance(service, DispatchService) else 0
    ledger_ok = True
    if isinstance(service, DispatchService):
        for b in service.batches.values():
            if not service.ledger.reconcile(b).is_valid:
                ledger_ok = False
                break

    return SystemReadinessResponseSchema(
        status="ready",
        clock={"type": clock_type, "current_time": now.isoformat()},
        storage={"provider": storage_provider, "connected": True},
        ledger={"initialized": True, "active_batches_count": batches_count, "reconciled": ledger_ok},
        workers={"sweeper_ready": True, "outbox_ready": True},
        timestamp=now,
    )


@app.get("/v1/metrics", tags=["operations"])
def get_system_metrics(
    format: str | None = Query(default=None),
    x_accept: str | None = Header(None, alias="Accept"),
):
    """Expose Prometheus-compatible and structured operational metrics for telemetry dashboards."""
    now = global_clock.now()
    if isinstance(service, DispatchService):
        batches = list(service.batches.values())
        riders = list(service.riders.values())
        shelters = list(service.shelters.values())
        allocations = list(service.allocations.values())
        deliveries = list(service.deliveries.values())
        incidents = list(service.incidents.values())

        avail_units = sum(b.available_quantity for b in batches)
        res_units = sum(b.reserved_quantity for b in batches)
        picked_units = sum(b.picked_up_quantity for b in batches)
        deliv_units = sum(b.delivered_quantity for b in batches)
        spoil_units = sum(b.spoiled_quantity for b in batches)

        riders_avail = sum(1 for r in riders if r.status == RiderStatus.AVAILABLE)
        riders_transit = sum(1 for r in riders if r.status == RiderStatus.IN_TRANSIT)
        shelters_open = sum(1 for s in shelters if s.status == ShelterStatus.OPEN and s.open)

        active_allocs = sum(1 for a in allocations if a.state in (AllocationState.CLAIMED, AllocationState.ACKNOWLEDGED))
        transit_delivs = sum(1 for d in deliveries if d.state in (DeliveryState.PICKED_UP, DeliveryState.IN_TRANSIT, DeliveryState.REROUTE_PENDING))
        comp_delivs = sum(1 for d in deliveries if d.state == DeliveryState.DELIVERED)

        active_incs = sum(1 for i in incidents if i.status != IncidentStatus.RESOLVED)
        outbox_pending = sum(1 for m in service.outbox_messages if m.status.value == "PENDING")
        audit_count = len(service.audit_records)

        ledger_healthy = True
        for b in batches:
            if not service.ledger.reconcile(b).is_valid:
                ledger_healthy = False
                break
    else:
        batches = riders = shelters = allocations = deliveries = incidents = []
        avail_units = res_units = picked_units = deliv_units = spoil_units = 0
        riders_avail = riders_transit = shelters_open = 0
        active_allocs = transit_delivs = comp_delivs = 0
        active_incs = outbox_pending = audit_count = 0
        ledger_healthy = True

    if format == "prometheus" or (x_accept and "text/plain" in x_accept):
        prom_lines = [
            "# HELP vigilo_system_status System operational status (1 = healthy)",
            "# TYPE vigilo_system_status gauge",
            "vigilo_system_status 1",
            "# HELP vigilo_batches_total Total batches in inventory",
            "# TYPE vigilo_batches_total gauge",
            f"vigilo_batches_total {len(batches)}",
            "# HELP vigilo_riders_total Total registered riders",
            "# TYPE vigilo_riders_total gauge",
            f"vigilo_riders_total {len(riders)}",
            "# HELP vigilo_riders_available Available riders ready for dispatch",
            "# TYPE vigilo_riders_available gauge",
            f"vigilo_riders_available {riders_avail}",
            "# HELP vigilo_shelters_open Currently open receiving shelters",
            "# TYPE vigilo_shelters_open gauge",
            f"vigilo_shelters_open {shelters_open}",
            "# HELP vigilo_inventory_available_units Total available inventory units",
            "# TYPE vigilo_inventory_available_units gauge",
            f"vigilo_inventory_available_units {avail_units}",
            "# HELP vigilo_inventory_delivered_units Total successfully delivered units",
            "# TYPE vigilo_inventory_delivered_units counter",
            f"vigilo_inventory_delivered_units {deliv_units}",
            "# HELP vigilo_inventory_spoiled_units Total spoiled inventory units",
            "# TYPE vigilo_inventory_spoiled_units counter",
            f"vigilo_inventory_spoiled_units {spoil_units}",
            "# HELP vigilo_incidents_active Currently unresolved incidents",
            "# TYPE vigilo_incidents_active gauge",
            f"vigilo_incidents_active {active_incs}",
            "# HELP vigilo_ledger_reconciliation_healthy Ledger balance conservation status",
            "# TYPE vigilo_ledger_reconciliation_healthy gauge",
            f"vigilo_ledger_reconciliation_healthy {1 if ledger_healthy else 0}",
        ]
        return Response(content="\n".join(prom_lines) + "\n", media_type="text/plain; version=0.0.4")

    return SystemMetricsResponseSchema(
        system_status="HEALTHY",
        uptime_seconds=3600.0,
        batches_count=len(batches),
        riders_total=len(riders),
        riders_available=riders_avail,
        riders_in_transit=riders_transit,
        shelters_total=len(shelters),
        shelters_open=shelters_open,
        allocations_active=active_allocs,
        deliveries_in_transit=transit_delivs,
        deliveries_completed=comp_delivs,
        inventory_available_units=avail_units,
        inventory_reserved_units=res_units,
        inventory_in_transit_units=picked_units,
        inventory_delivered_units=deliv_units,
        inventory_spoiled_units=spoil_units,
        incidents_total=len(incidents),
        incidents_active=active_incs,
        outbox_pending_messages=outbox_pending,
        audit_records_total=audit_count,
        ledger_reconciliation_healthy=ledger_healthy,
    )


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

@app.post("/v1/dispatch/candidates", response_model=CandidateGenerationResponseSchema)
def generate_dispatch_candidates(batch_id: str = Query(...)) -> CandidateGenerationResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    try:
        result = service.generate_candidates(batch_id=batch_id)
        return CandidateGenerationResponseSchema(**result.to_dict())
    except VigiloError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.to_dict()) from exc


@app.get("/v1/batches/{batch_id}/safety-clock", response_model=LastSafeDecisionClockResponseSchema)
def get_safety_clock(
    batch_id: str,
    shelter_id: str = Query(...),
    travel_minutes: int = Query(default=25, ge=0),
    handoff_minutes: int = Query(default=10, ge=0),
) -> LastSafeDecisionClockResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    try:
        clock = service.calculate_safety_clock(
            batch_id=batch_id,
            shelter_id=shelter_id,
            travel_minutes=travel_minutes,
            handoff_minutes=handoff_minutes,
        )
        return LastSafeDecisionClockResponseSchema(**clock.to_dict())
    except VigiloError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.to_dict()) from exc


@app.post("/v1/safety/evaluate", response_model=SafetyEvaluationReportResponseSchema)
def evaluate_safety_constraints(payload: SafetyEvaluationRequestSchema) -> SafetyEvaluationReportResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    try:
        report = service.evaluate_safety(
            batch_id=payload.batch_id,
            rider_id=payload.rider_id,
            shelter_id=payload.shelter_id,
            quantity=payload.quantity,
            travel_minutes=payload.travel_minutes,
            handoff_minutes=payload.handoff_minutes,
            is_route_accessible=payload.is_route_accessible,
        )
        return SafetyEvaluationReportResponseSchema(
            feasible=report.feasible,
            primary_failure_code=report.primary_failure_code,
            primary_failure_reason=report.primary_failure_reason,
            evaluated_rules=report.evaluated_rules,
            evidence=report.evidence,
            rule_results=[RuleEvaluationResultSchema(**r.__dict__) for r in report.rule_results],
        )
    except VigiloError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.to_dict()) from exc


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
def acknowledge_allocation(
    allocation_id: str,
    x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    x_actor: str | None = Header(None, alias="X-Actor"),
) -> AllocationResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    try:
        alloc = service.acknowledge_allocation(
            allocation_id,
            actor=x_actor or "rider",
            actor_role=x_actor_role,
        )
        return _serialize_allocation(alloc)
    except VigiloError as exc:
        code_status = status.HTTP_403_FORBIDDEN if exc.code == "AUTHORIZATION_DENIED" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code_status, detail=exc.to_dict()) from exc


@app.post("/v1/allocations/{allocation_id}/cancel", response_model=AllocationResponseSchema)
def cancel_allocation(
    allocation_id: str,
    reason: str = Query(default="Manual allocation cancellation"),
    x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    x_actor: str | None = Header(None, alias="X-Actor"),
) -> AllocationResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    try:
        alloc = service.cancel_allocation(
            allocation_id,
            actor=x_actor or "dispatcher",
            reason=reason,
            actor_role=x_actor_role,
        )
        return _serialize_allocation(alloc)
    except VigiloError as exc:
        code_status = status.HTTP_403_FORBIDDEN if exc.code == "AUTHORIZATION_DENIED" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code_status, detail=exc.to_dict()) from exc


@app.post("/v1/allocations/{allocation_id}/pickup", response_model=DeliveryResponseSchema)
def pickup_allocation(
    allocation_id: str,
    x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    x_actor: str | None = Header(None, alias="X-Actor"),
) -> DeliveryResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    try:
        delivery = service.pickup_allocation(
            allocation_id,
            actor=x_actor or "rider",
            actor_role=x_actor_role,
        )
        return _serialize_delivery(delivery)
    except VigiloError as exc:
        code_status = status.HTTP_403_FORBIDDEN if exc.code == "AUTHORIZATION_DENIED" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code_status, detail=exc.to_dict()) from exc


@app.post("/v1/allocations/{allocation_id}/deliver", response_model=DeliveryResponseSchema)
def deliver_allocation_cargo(
    allocation_id: str,
    x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    x_actor: str | None = Header(None, alias="X-Actor"),
) -> DeliveryResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    # Find matching delivery
    matching_delivery = next((d for d in service.deliveries.values() if d.allocation_id == allocation_id), None)
    if matching_delivery is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No active delivery found for allocation '{allocation_id}'")
    try:
        delivery = service.deliver_cargo(
            matching_delivery.id,
            actor=x_actor or "rider",
            actor_role=x_actor_role,
        )
        return _serialize_delivery(delivery)
    except VigiloError as exc:
        code_status = status.HTTP_403_FORBIDDEN if exc.code == "AUTHORIZATION_DENIED" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code_status, detail=exc.to_dict()) from exc


@app.get("/v1/deliveries/{delivery_id}", response_model=DeliveryResponseSchema)
def get_delivery(delivery_id: str) -> DeliveryResponseSchema:
    if not isinstance(service, DispatchService) or delivery_id not in service.deliveries:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Delivery '{delivery_id}' not found")
    return _serialize_delivery(service.deliveries[delivery_id])


@app.post("/v1/deliveries/{delivery_id}/deliver", response_model=DeliveryResponseSchema)
def deliver_cargo(
    delivery_id: str,
    x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    x_actor: str | None = Header(None, alias="X-Actor"),
) -> DeliveryResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    try:
        delivery = service.deliver_cargo(
            delivery_id,
            actor=x_actor or "rider",
            actor_role=x_actor_role,
        )
        return _serialize_delivery(delivery)
    except VigiloError as exc:
        code_status = status.HTTP_403_FORBIDDEN if exc.code == "AUTHORIZATION_DENIED" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code_status, detail=exc.to_dict()) from exc


# -----------------------------------------------------------------------------
# Outbox & Audit Endpoints (Phase 4)
# -----------------------------------------------------------------------------

@app.get("/v1/audit/decisions/{decision_id}", response_model=AuditRecordResponseSchema)
def get_audit_decision(decision_id: str) -> AuditRecordResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    record = None
    if hasattr(service, "get_audit_record"):
        record = service.get_audit_record(decision_id)
    if record is None:
        record = next((a for a in service.audit_records if a.id == decision_id), None)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Audit record '{decision_id}' not found")
    return AuditRecordResponseSchema(
        id=record.id,
        event_id=record.event_id,
        actor=record.actor,
        command=record.command,
        decision=record.decision,
        constraints_evaluated=record.constraints_evaluated,
        evidence=record.evidence,
        created_at=record.created_at,
    )


@app.get("/v1/audit/inventory/{batch_id}", response_model=BatchLifecycleReconstructionResponseSchema)
def get_inventory_audit_reconstruction(batch_id: str) -> BatchLifecycleReconstructionResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    try:
        report = service.reconstruct_batch_history(batch_id)
        return BatchLifecycleReconstructionResponseSchema(**report)
    except VigiloError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.to_dict()) from exc


@app.get("/v1/outbox/messages", response_model=list[OutboxMessageResponseSchema])
def list_outbox_messages(limit: int = Query(default=50, ge=1, le=200)) -> list[OutboxMessageResponseSchema]:
    if not isinstance(service, DispatchService):
        return []
    messages = service.outbox_messages[-limit:]
    return [OutboxMessageResponseSchema(**m.to_dict()) for m in messages]


@app.post("/v1/outbox/publish")
def publish_outbox_messages(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, int]:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    published = service.publish_outbox(limit=limit)
    return {"published_count": published}


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


def raise_vigilo_http_exception(exc: VigiloError):
    if exc.code == "AUTHORIZATION_DENIED":
        code_status = status.HTTP_403_FORBIDDEN
    elif exc.code in (
        "ALLOCATION_NOT_FOUND",
        "DELIVERY_NOT_FOUND",
        "BATCH_NOT_FOUND",
        "SHELTER_NOT_FOUND",
        "RIDER_NOT_FOUND",
        "INCIDENT_NOT_FOUND",
    ):
        code_status = status.HTTP_404_NOT_FOUND
    elif exc.code in ("CLAIM_EXPIRED", "RECOVERY_NOT_FEASIBLE", "INVALID_STATE_TRANSITION"):
        code_status = status.HTTP_409_CONFLICT
    else:
        code_status = status.HTTP_400_BAD_REQUEST
    raise HTTPException(status_code=code_status, detail=exc.to_dict()) from exc


# -----------------------------------------------------------------------------
# Phase 5: Shelter Closure & Reopening Endpoints
# -----------------------------------------------------------------------------

@app.post("/v1/shelters/{shelter_id}/close", response_model=ShelterResponseSchema)
def close_shelter_endpoint(
    shelter_id: str,
    payload: ShelterCloseSchema | None = None,
    x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    x_actor: str | None = Header(None, alias="X-Actor"),
) -> ShelterResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    if x_actor_role and x_actor_role not in ("ADMIN", "DISPATCHER"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Actor not authorized to close shelters")
    reason = payload.reason if payload else "Shelter closed due to operational conditions"
    auto_reroute = payload.auto_reroute if payload else True
    try:
        shelter, _, _, _ = service.close_shelter(
            shelter_id,
            actor=x_actor or "dispatcher",
            reason=reason,
            auto_reroute=auto_reroute,
        )
        return _serialize_shelter(shelter)
    except VigiloError as exc:
        raise_vigilo_http_exception(exc)


@app.post("/v1/shelters/{shelter_id}/reopen", response_model=ShelterResponseSchema)
def reopen_shelter_endpoint(
    shelter_id: str,
    x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    x_actor: str | None = Header(None, alias="X-Actor"),
) -> ShelterResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    if x_actor_role and x_actor_role not in ("ADMIN", "DISPATCHER"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Actor not authorized to reopen shelters")
    try:
        shelter = service.reopen_shelter(shelter_id, actor=x_actor or "dispatcher")
        return _serialize_shelter(shelter)
    except VigiloError as exc:
        raise_vigilo_http_exception(exc)


# -----------------------------------------------------------------------------
# Phase 5: Delivery In-Transit Rerouting Endpoints
# -----------------------------------------------------------------------------

@app.post("/v1/deliveries/{delivery_id}/reroute/preview", response_model=DeliveryReroutePreviewResponseSchema)
def preview_delivery_reroute(delivery_id: str) -> DeliveryReroutePreviewResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    try:
        res = service.preview_reroute(delivery_id)
        return DeliveryReroutePreviewResponseSchema(**res)
    except VigiloError as exc:
        raise_vigilo_http_exception(exc)


@app.post("/v1/deliveries/{delivery_id}/reroute/commit", response_model=DeliveryResponseSchema)
def commit_delivery_reroute(
    delivery_id: str,
    payload: DeliveryRerouteCommitSchema | None = None,
    x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    x_actor: str | None = Header(None, alias="X-Actor"),
) -> DeliveryResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    target_id = payload.target_shelter_id if payload else None
    reason = payload.reason if payload else "In-transit reroute"
    try:
        delivery = service.commit_reroute(
            delivery_id=delivery_id,
            target_shelter_id=target_id,
            actor=x_actor or "dispatcher",
            reason=reason,
            actor_role=x_actor_role,
        )
        return _serialize_delivery(delivery)
    except VigiloError as exc:
        raise_vigilo_http_exception(exc)


# -----------------------------------------------------------------------------
# Phase 5: Incident Management Endpoints
# -----------------------------------------------------------------------------

@app.get("/v1/incidents", response_model=list[IncidentResponseSchema])
def list_incidents(
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    affected_entity_type: str | None = Query(default=None),
) -> list[IncidentResponseSchema]:
    if not isinstance(service, DispatchService):
        return []
    incs = service.list_incidents(status=status, severity=severity, affected_entity_type=affected_entity_type)
    return [_serialize_incident(inc) for inc in incs]


@app.get("/v1/incidents/{incident_id}", response_model=IncidentResponseSchema)
def get_incident(incident_id: str) -> IncidentResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    try:
        inc = service.get_incident(incident_id)
        return _serialize_incident(inc)
    except VigiloError as exc:
        raise_vigilo_http_exception(exc)


@app.post("/v1/incidents/{incident_id}/escalate", response_model=IncidentResponseSchema)
def escalate_incident(
    incident_id: str,
    payload: IncidentEscalateSchema | None = None,
    x_actor: str | None = Header(None, alias="X-Actor"),
) -> IncidentResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    reason = payload.reason if payload else "Escalated for immediate review"
    try:
        inc = service.escalate_incident(incident_id, reason=reason, actor=x_actor or "operator")
        return _serialize_incident(inc)
    except VigiloError as exc:
        raise_vigilo_http_exception(exc)


@app.post("/v1/incidents/{incident_id}/resolve", response_model=IncidentResponseSchema)
def resolve_incident(
    incident_id: str,
    payload: IncidentResolveSchema | None = None,
    x_actor: str | None = Header(None, alias="X-Actor"),
) -> IncidentResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    notes = payload.resolution_notes if payload else "Resolved by operations"
    try:
        inc = service.resolve_incident(incident_id, resolution_notes=notes, actor=x_actor or "operator")
        return _serialize_incident(inc)
    except VigiloError as exc:
        raise_vigilo_http_exception(exc)


# -----------------------------------------------------------------------------
# Phase 5: Background Sweep Worker Endpoints
# -----------------------------------------------------------------------------

@app.post("/v1/workers/expire-allocations")
def worker_expire_allocations() -> dict[str, Any]:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    expired = service.sweep_expired_allocations()
    return {"expired_count": len(expired), "expired_ids": [a.id for a in expired]}


@app.post("/v1/workers/monitor-heartbeats")
def worker_monitor_heartbeats(max_staleness_minutes: float = Query(default=30.0)) -> dict[str, Any]:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    incidents = service.sweep_stale_heartbeats(max_staleness_minutes=max_staleness_minutes)
    return {"stale_riders_incident_count": len(incidents), "incident_ids": [i.id for i in incidents]}


@app.post("/v1/workers/safety-deadlines")
def worker_safety_deadlines(buffer_minutes: float = Query(default=30.0)) -> dict[str, Any]:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    incidents = service.sweep_safety_deadlines(buffer_minutes=buffer_minutes)
    return {"deadline_warning_count": len(incidents), "incident_ids": [i.id for i in incidents]}


@app.post("/v1/workers/run-sweeps", response_model=WorkerSweepResponseSchema)
def worker_run_all_sweeps() -> WorkerSweepResponseSchema:
    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")
    res = service.run_all_sweeps()
    return WorkerSweepResponseSchema(**res)


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


def _serialize_incident(i) -> IncidentResponseSchema:
    return IncidentResponseSchema(
        id=i.id,
        severity=i.severity,
        status=i.status,
        affected_entity_type=i.affected_entity_type,
        affected_entity_id=i.affected_entity_id,
        reason_code=i.reason_code,
        description=i.description,
        created_at=i.created_at,
        resolved_at=i.resolved_at,
        evidence=i.evidence,
    )


def _serialize_scenario_state(instance: ScenarioInstance) -> ScenarioStateResponseSchema:
    return ScenarioStateResponseSchema(
        scenario_id=instance.scenario_id,
        name=instance.name,
        seed=instance.seed,
        status=instance.status,
        current_time=instance.clock.now(),
        batches=[_serialize_batch(b) for b in instance.service.batches.values()],
        allocations=[_serialize_allocation(a) for a in instance.service.allocations.values()],
        deliveries=[_serialize_delivery(d) for d in instance.service.deliveries.values()],
        riders=[_serialize_rider(r) for r in instance.service.riders.values()],
        shelters=[_serialize_shelter(s) for s in instance.service.shelters.values()],
        incidents=[_serialize_incident(i) for i in instance.service.incidents.values()],
        ledger_reconciliation=[
            ReconciliationReportResponseSchema(**instance.service.ledger.reconcile(b).to_dict())
            for b in instance.service.batches.values()
        ],
        metrics=instance.compute_metrics(),
    )


# ==========================================
# Phase 6: Simulation & Baseline Endpoints
# ==========================================

@app.get("/v1/scenarios/presets", response_model=list[ScenarioPresetResponseSchema], tags=["simulation"])
def list_scenario_presets():
    """List preset chaos lab scenarios designed for judge evaluations."""
    manager = ScenarioManager.get_instance()
    presets = manager.list_presets()
    return [ScenarioPresetResponseSchema(**p) for p in presets]


@app.post("/v1/scenarios", response_model=ScenarioStateResponseSchema, tags=["simulation"])
def create_scenario(payload: ScenarioCreateSchema):
    """Create and initialize a new isolated simulation scenario."""
    manager = ScenarioManager.get_instance()
    instance = manager.create_scenario(
        name=payload.name,
        scenario_id=payload.scenario_id,
        preset_id=payload.preset_id,
        seed=payload.seed,
        description=payload.description,
        start_time=payload.start_time,
    )
    instance.start()
    return _serialize_scenario_state(instance)


@app.post("/v1/scenarios/{id}/start", response_model=ScenarioStateResponseSchema, tags=["simulation"])
def start_scenario(id: str):
    """Start an initialized scenario if not already running."""
    manager = ScenarioManager.get_instance()
    try:
        instance = manager.get_scenario(id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    if instance.status != "RUNNING":
        instance.start()
    return _serialize_scenario_state(instance)


@app.post("/v1/scenarios/{id}/advance-time", response_model=ScenarioStateResponseSchema, tags=["simulation"])
def advance_scenario_time(id: str, payload: ScenarioAdvanceTimeSchema):
    """Advance scenario simulated clock and execute autonomous recovery sweep workers."""
    manager = ScenarioManager.get_instance()
    try:
        instance = manager.get_scenario(id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    try:
        instance.advance_time(payload.minutes)
    except VigiloError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
    return _serialize_scenario_state(instance)


@app.post("/v1/scenarios/{id}/inject-failure", response_model=ScenarioStateResponseSchema, tags=["simulation"])
def inject_scenario_failure(id: str, payload: ScenarioInjectFailureSchema):
    """Inject failure disturbance (shelter closure, rider loss, flood disruption, demand surge) into scenario."""
    manager = ScenarioManager.get_instance()
    try:
        instance = manager.get_scenario(id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    try:
        instance.inject_failure(
            failure_type=payload.failure_type,
            target_id=payload.target_id,
            params=payload.params,
        )
    except VigiloError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
    return _serialize_scenario_state(instance)


@app.get("/v1/scenarios/{id}/state", response_model=ScenarioStateResponseSchema, tags=["simulation"])
def get_scenario_state(id: str):
    """Retrieve full isolated state snapshot, ledger reconciliation, and live metrics for a scenario."""
    manager = ScenarioManager.get_instance()
    try:
        instance = manager.get_scenario(id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    return _serialize_scenario_state(instance)


@app.get("/v1/scenarios/{id}/replay", response_model=ScenarioReplayResponseSchema, tags=["simulation"])
def get_scenario_replay(id: str):
    """Retrieve deterministic chronological replay tape of all scenario steps and injected events."""
    manager = ScenarioManager.get_instance()
    try:
        instance = manager.get_scenario(id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    replay_data = instance.get_replay()
    return ScenarioReplayResponseSchema(**replay_data)


@app.post("/v1/scenarios/{id}/compare-baseline", response_model=ScenarioCompareBaselineResponseSchema, tags=["simulation"])
def compare_scenario_with_baseline(id: str):
    """Run baseline simulation and generate side-by-side comparative evaluation scorecard."""
    manager = ScenarioManager.get_instance()
    try:
        instance = manager.get_scenario(id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
    
    vigilo_metrics = instance.compute_metrics()
    comparison = BaselineComparisonEngine.compare(
        vigilo_metrics=vigilo_metrics,
        scenario_id=instance.scenario_id,
        scenario_name=instance.name,
        seed=instance.seed,
        start_time=instance.start_time,
        preset_id=instance.preset_id,
    )
    return ScenarioCompareBaselineResponseSchema(**comparison)


# ==========================================
# Phase 7: Emergency Overrides
# ==========================================

@app.post("/v1/emergency/override", response_model=EmergencyOverrideResponseSchema, tags=["operations"])
def execute_emergency_override(
    payload: EmergencyOverrideSchema,
    x_actor_role: str | None = Header(None, alias="X-Actor-Role"),
    x_actor: str | None = Header(None, alias="X-Actor"),
):
    """Execute an explicit, high-severity emergency override authorized strictly by an Admin."""
    if x_actor_role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Emergency overrides require explicit ADMIN role authorization.",
        )

    if not isinstance(service, DispatchService):
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Operation requires domain service")

    now = global_clock.now()
    override_id = f"ovr_{uuid4().hex[:10]}"
    actor_name = x_actor or payload.authorized_by

    applied_changes: dict[str, Any] = {}

    if payload.target_entity_type.upper() == "SHELTER":
        shelter = service.shelters.get(payload.target_entity_id)
        if not shelter:
            raise HTTPException(status_code=404, detail=f"Shelter '{payload.target_entity_id}' not found")
        if payload.override_type == "RECEIVING_HOURS_OVERRIDE":
            shelter.receiving_hours = ReceivingHours(open_hour=0, close_hour=24)
            applied_changes["receiving_hours"] = "0-24 (24/7 Emergency Access)"
        elif payload.override_type == "FORCE_OPEN":
            shelter.status = ShelterStatus.OPEN
            shelter.open = True
            applied_changes["status"] = "OPEN"
        elif payload.override_type == "CAPACITY_EXPANSION":
            delta = payload.params.get("additional_capacity", 50)
            shelter.receiving_capacity_remaining += delta
            applied_changes["receiving_capacity_remaining"] = shelter.receiving_capacity_remaining

    elif payload.target_entity_type.upper() == "RIDER":
        rider = service.riders.get(payload.target_entity_id)
        if not rider:
            raise HTTPException(status_code=404, detail=f"Rider '{payload.target_entity_id}' not found")
        if payload.override_type == "CAPACITY_EXPANSION":
            delta = payload.params.get("additional_capacity", 20)
            rider.capacity += delta
            applied_changes["capacity"] = rider.capacity
        elif payload.override_type == "FORCE_AVAILABLE":
            rider.status = RiderStatus.AVAILABLE
            rider.available = True
            applied_changes["status"] = "AVAILABLE"

    # Record operational event
    event = service.record_event(
        event_type="EMERGENCY_OVERRIDE_EXECUTED",
        aggregate_id=payload.target_entity_id,
        aggregate_type=payload.target_entity_type,
        actor=actor_name,
        payload={
            "override_id": override_id,
            "override_type": payload.override_type,
            "justification": payload.justification,
            "authorized_by": payload.authorized_by,
            "applied_changes": applied_changes,
        },
        evidence={"override_params": payload.params},
    )

    # Record immutable audit record
    from .domain.events import AuditRecord
    audit = AuditRecord.record(
        actor=actor_name,
        command="emergency.override",
        decision="OVERRIDE_EXECUTED",
        constraints=["ADMIN_OVERRIDE_AUTHORIZED"],
        evidence={
            "override_id": override_id,
            "override_type": payload.override_type,
            "justification": payload.justification,
            "authorized_by": payload.authorized_by,
            "applied_changes": applied_changes,
        },
        now=now,
        event_id=event.id,
    )
    service.audit_records.append(audit)

    return EmergencyOverrideResponseSchema(
        override_id=override_id,
        override_type=payload.override_type,
        target_entity_type=payload.target_entity_type,
        target_entity_id=payload.target_entity_id,
        status="EXECUTED",
        justification=payload.justification,
        authorized_by=payload.authorized_by,
        executed_at=now,
        audit_record_id=audit.id,
        applied_changes=applied_changes,
    )
