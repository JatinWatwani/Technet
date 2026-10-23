from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from .models import (
    AllocationState,
    DeliveryState,
    IncidentSeverity,
    IncidentStatus,
    RiderStatus,
    ShelterStatus,
    StorageRequirement,
    UserRole,
)


class GeoLocationSchema(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class ReceivingHoursSchema(BaseModel):
    open_hour: int = Field(default=0, ge=0, le=24)
    close_hour: int = Field(default=24, ge=0, le=24)


# User & Donor Schemas
class UserCreateSchema(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole


class UserResponseSchema(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    created_at: datetime


class DonorCreateSchema(BaseModel):
    id: str
    user_id: str | None = None
    organization_name: str
    contact_phone: str = ""
    address: str = ""


class DonorResponseSchema(BaseModel):
    id: str
    user_id: str | None
    organization_name: str
    contact_phone: str
    address: str
    created_at: datetime


# Batch Schemas
class ItemRulesSchema(BaseModel):
    safe_handling_minutes: int = Field(gt=0)
    safety_buffer_minutes: int = Field(default=0, ge=0)
    required_prerequisites: list[str] = Field(default_factory=list)
    storage_requirement: StorageRequirement = StorageRequirement.AMBIENT


class BatchCreateSchema(BaseModel):
    id: str
    donor_id: str = "donor_default"
    item_type: str = "prepared_meals"
    original_quantity: int = Field(gt=0)
    item_rules: ItemRulesSchema
    created_at: datetime | None = None


class BatchResponseSchema(BaseModel):
    id: str
    donor_id: str
    item_type: str
    original_quantity: int
    available_quantity: int
    reserved_quantity: int
    picked_up_quantity: int
    delivered_quantity: int
    spoiled_quantity: int
    item_rules: ItemRulesSchema
    created_at: datetime
    safe_until: datetime


# Rider Schemas
class RiderCreateSchema(BaseModel):
    id: str
    capacity: int = Field(gt=0)
    user_id: str | None = None
    status: RiderStatus = RiderStatus.AVAILABLE
    location: GeoLocationSchema | None = None


class RiderStatusUpdateSchema(BaseModel):
    status: RiderStatus
    available: bool | None = None


class RiderLocationUpdateSchema(BaseModel):
    latitude: float
    longitude: float


class RiderResponseSchema(BaseModel):
    id: str
    user_id: str | None
    capacity: int
    active_load: int
    remaining_capacity: int
    available: bool
    status: RiderStatus
    location: GeoLocationSchema | None
    last_heartbeat_at: datetime | None


# Shelter Schemas
class ShelterCreateSchema(BaseModel):
    id: str
    name: str = ""
    demand_remaining: int = Field(ge=0)
    receiving_capacity_remaining: int = Field(ge=0)
    prerequisites: list[str] = Field(default_factory=list)
    open: bool = True
    status: ShelterStatus = ShelterStatus.OPEN
    location: GeoLocationSchema | None = None
    receiving_hours: ReceivingHoursSchema = Field(default_factory=ReceivingHoursSchema)


class ShelterStatusUpdateSchema(BaseModel):
    status: ShelterStatus
    open: bool | None = None


class ShelterDemandUpdateSchema(BaseModel):
    demand_remaining: int = Field(ge=0)
    receiving_capacity_remaining: int | None = Field(default=None, ge=0)


class ShelterResponseSchema(BaseModel):
    id: str
    name: str
    demand_remaining: int
    receiving_capacity_remaining: int
    prerequisites: list[str]
    open: bool
    status: ShelterStatus
    location: GeoLocationSchema | None
    receiving_hours: ReceivingHoursSchema


# Allocation & Dispatch Schemas
class DispatchPayloadSchema(BaseModel):
    batch_id: str
    rider_id: str
    shelter_id: str
    quantity: int = Field(gt=0)
    travel_minutes: int = Field(ge=0)
    handoff_minutes: int = Field(ge=0)
    now: datetime | None = None
    idempotency_key: str | None = None


class DispatchPreviewResponseSchema(BaseModel):
    feasible: bool
    reason_code: str | None = None
    reason: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class AllocationResponseSchema(BaseModel):
    id: str
    batch_id: str
    rider_id: str
    shelter_id: str
    quantity: int
    travel_minutes: int
    handoff_minutes: int
    state: AllocationState
    claimed_at: datetime
    lease_expires_at: datetime | None
    safe_until: datetime
    acknowledged_at: datetime | None
    picked_up_at: datetime | None


# Delivery Schemas
class DeliveryResponseSchema(BaseModel):
    id: str
    allocation_id: str
    batch_id: str
    rider_id: str
    current_shelter_id: str
    quantity: int
    state: DeliveryState
    picked_up_at: datetime
    delivered_at: datetime | None
    current_location: GeoLocationSchema | None
    destination_history: list[str]


# Incident Schemas
class IncidentCreateSchema(BaseModel):
    severity: IncidentSeverity
    affected_entity_type: str
    affected_entity_id: str
    reason_code: str
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class IncidentResponseSchema(BaseModel):
    id: str
    severity: IncidentSeverity
    status: IncidentStatus
    affected_entity_type: str
    affected_entity_id: str
    reason_code: str
    description: str
    created_at: datetime
    resolved_at: datetime | None
    evidence: dict[str, Any]


# Clock Schemas
class ClockResponseSchema(BaseModel):
    current_time: datetime
    iso: str
    clock_type: str


class ClockAdvanceSchema(BaseModel):
    minutes: float = Field(default=0, ge=0)
    seconds: float = Field(default=0, ge=0)


# Event & Audit Schemas
class OperationalEventResponseSchema(BaseModel):
    id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    occurred_at: datetime
    payload: dict[str, Any]
    actor: str
    correlation_id: str
    evidence: dict[str, Any]


# Inventory Ledger Schemas
class InventoryBalanceSnapshotSchema(BaseModel):
    available: int
    reserved: int
    picked_up: int
    delivered: int
    spoiled: int = 0
    damaged: int = 0
    lost: int = 0
    total: int


class InventoryLedgerEntryResponseSchema(BaseModel):
    id: str
    batch_id: str
    entry_type: str
    quantity: int
    from_state: str | None
    to_state: str
    actor: str
    command: str
    reason: str
    occurred_at: datetime
    balance_after: InventoryBalanceSnapshotSchema
    allocation_id: str | None = None
    delivery_id: str | None = None
    idempotency_key: str | None = None
    correlation_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReconciliationReportResponseSchema(BaseModel):
    batch_id: str
    original_quantity: int
    current_balance: InventoryBalanceSnapshotSchema
    reconciled_balance: InventoryBalanceSnapshotSchema
    is_valid: bool
    entry_count: int
    discrepancies: list[str]
    checked_at: datetime


class CompensatingAdjustmentSchema(BaseModel):
    quantity: int = Field(gt=0)
    from_state: str
    to_state: str
    reason: str = Field(min_length=5)
    actor: str = "coordinator"
    idempotency_key: str | None = None


# Phase 3: Safety Engine & Candidate Generation Schemas
class SafetyEvaluationRequestSchema(BaseModel):
    batch_id: str
    rider_id: str
    shelter_id: str
    quantity: int = Field(gt=0)
    travel_minutes: int = Field(ge=0)
    handoff_minutes: int = Field(ge=0)
    is_route_accessible: bool = True


class RuleEvaluationResultSchema(BaseModel):
    rule_name: str
    passed: bool
    reason_code: str | None = None
    reason: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class SafetyEvaluationReportResponseSchema(BaseModel):
    feasible: bool
    primary_failure_code: str | None = None
    primary_failure_reason: str | None = None
    evaluated_rules: list[str] = Field(default_factory=list)
    rule_results: list[RuleEvaluationResultSchema] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


class LastSafeDecisionClockResponseSchema(BaseModel):
    batch_id: str
    shelter_id: str
    safe_deadline: datetime
    latest_useful_decision_time: datetime
    remaining_safe_handling_minutes: float
    remaining_decision_window_minutes: float
    is_feasible: bool
    is_urgently_closing: bool
    travel_minutes: int
    handoff_minutes: int
    safety_buffer_minutes: int
    confirmation_minutes: int
    notification_minutes: int
    checked_at: datetime
    invalidating_factors: list[str] = Field(default_factory=list)


class CandidateAssignmentSchema(BaseModel):
    batch_id: str
    rider_id: str
    shelter_id: str
    quantity: int
    travel_minutes: int
    handoff_minutes: int
    feasible: bool
    score: float
    rank: int
    ranking_explanation: str
    evaluation: SafetyEvaluationReportResponseSchema
    safety_clock: LastSafeDecisionClockResponseSchema


class BatchSplitPlanSchema(BaseModel):
    batch_id: str
    total_batch_quantity: int
    allocated_quantity: int
    remaining_unallocated: int
    is_fully_allocated: bool
    assignments: list[CandidateAssignmentSchema]


class CandidateGenerationResponseSchema(BaseModel):
    batch_id: str
    feasible_count: int
    rejected_count: int
    feasible_candidates: list[CandidateAssignmentSchema]
    rejected_candidates: list[CandidateAssignmentSchema]
    split_plan: BatchSplitPlanSchema | None = None
    generated_at: datetime


