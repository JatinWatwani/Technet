"""SQLAlchemy ORM models corresponding to Vigilo database schema."""
from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, JsonObject, TextArray, UTCDateTime


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class DonorModel(Base):
    __tablename__ = "donors"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    organization_name: Mapped[str] = mapped_column(String, nullable=False)
    contact_phone: Mapped[str] = mapped_column(String, default="", nullable=False)
    address: Mapped[str] = mapped_column(String, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class BatchModel(Base):
    __tablename__ = "batches"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    donor_id: Mapped[str | None] = mapped_column(String, ForeignKey("donors.id", ondelete="SET NULL"), nullable=True)
    item_type: Mapped[str] = mapped_column(String, default="prepared_meals", nullable=False)
    original_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    available_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    picked_up_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivered_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    spoiled_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    safe_handling_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    safety_buffer_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    required_prerequisites: Mapped[list[str]] = mapped_column(TextArray, default=list, nullable=False)
    storage_requirement: Mapped[str] = mapped_column(String, default="AMBIENT", nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        CheckConstraint("original_quantity > 0", name="chk_batch_original_qty"),
        CheckConstraint("available_quantity >= 0", name="chk_batch_avail_qty"),
        CheckConstraint("reserved_quantity >= 0", name="chk_batch_res_qty"),
        CheckConstraint("picked_up_quantity >= 0", name="chk_batch_pick_qty"),
        CheckConstraint("delivered_quantity >= 0", name="chk_batch_deliv_qty"),
        CheckConstraint("spoiled_quantity >= 0", name="chk_batch_spoil_qty"),
    )


class RiderModel(Base):
    __tablename__ = "riders"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    active_load: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String, default="AVAILABLE", nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("capacity > 0", name="chk_rider_capacity"),
        CheckConstraint("active_load >= 0", name="chk_rider_active_load"),
    )


class ShelterModel(Base):
    __tablename__ = "shelters"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, default="", nullable=False)
    demand_remaining: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    receiving_capacity_remaining: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prerequisites: Mapped[list[str]] = mapped_column(TextArray, default=list, nullable=False)
    open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String, default="OPEN", nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    open_hour: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    close_hour: Mapped[int] = mapped_column(Integer, default=24, nullable=False)

    __table_args__ = (
        CheckConstraint("demand_remaining >= 0", name="chk_shelter_demand"),
        CheckConstraint("receiving_capacity_remaining >= 0", name="chk_shelter_capacity"),
    )


class AllocationModel(Base):
    __tablename__ = "allocations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id: Mapped[str] = mapped_column(String, ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False)
    rider_id: Mapped[str] = mapped_column(String, ForeignKey("riders.id", ondelete="RESTRICT"), nullable=False)
    shelter_id: Mapped[str] = mapped_column(String, ForeignKey("shelters.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    travel_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    handoff_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    state: Mapped[str] = mapped_column(String, default="CLAIMED", nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    safe_until: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    picked_up_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_allocation_quantity"),
        CheckConstraint("travel_minutes >= 0", name="chk_allocation_travel"),
        CheckConstraint("handoff_minutes >= 0", name="chk_allocation_handoff"),
        Index("idx_allocations_batch", "batch_id"),
        Index("idx_allocations_rider", "rider_id"),
        Index("idx_allocations_shelter", "shelter_id"),
    )


class DeliveryModel(Base):
    __tablename__ = "deliveries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    allocation_id: Mapped[str] = mapped_column(String, ForeignKey("allocations.id", ondelete="CASCADE"), nullable=False)
    batch_id: Mapped[str] = mapped_column(String, ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False)
    rider_id: Mapped[str] = mapped_column(String, ForeignKey("riders.id", ondelete="RESTRICT"), nullable=False)
    current_shelter_id: Mapped[str] = mapped_column(String, ForeignKey("shelters.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String, default="ASSIGNED", nullable=False)
    picked_up_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    current_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    destination_history: Mapped[list[str]] = mapped_column(TextArray, default=list, nullable=False)


class InventoryLedgerEntryModel(Base):
    __tablename__ = "inventory_ledger_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    batch_id: Mapped[str] = mapped_column(String, ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False)
    entry_type: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    from_state: Mapped[str | None] = mapped_column(String, nullable=True)
    to_state: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    command: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    balance_available: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_reserved: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_picked_up: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_delivered: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_spoiled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    balance_damaged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    balance_lost: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    allocation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    delivery_id: Mapped[str | None] = mapped_column(String, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JsonObject, default=dict, nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_ledger_qty"),
        Index("idx_ledger_batch_occurred", "batch_id", "occurred_at"),
        Index("idx_ledger_idempotency", "idempotency_key", unique=False),
    )


class IdempotencyKeyModel(Base):
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    scope: Mapped[str] = mapped_column(String, default="global", nullable=False)
    status: Mapped[str] = mapped_column(String, default="IN_PROGRESS", nullable=False)
    response_payload: Mapped[dict | None] = mapped_column(JsonObject, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)


class OperationalEventModel(Base):
    __tablename__ = "operational_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String, nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JsonObject, default=dict, nullable=False)
    actor: Mapped[str] = mapped_column(String, default="system", nullable=False)
    correlation_id: Mapped[str] = mapped_column(String, default="", nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JsonObject, default=dict, nullable=False)


class IncidentModel(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    incident_type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="OPEN", nullable=False)
    description: Mapped[str] = mapped_column(String, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    evidence_json: Mapped[dict] = mapped_column(JsonObject, default=dict, nullable=False)


class AuditRecordModel(Base):
    __tablename__ = "audit_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    event_id: Mapped[str | None] = mapped_column(String, nullable=True)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    command: Mapped[str] = mapped_column(String, nullable=False)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    constraints_evaluated: Mapped[list[str]] = mapped_column(TextArray, default=list, nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JsonObject, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class OutboxMessageModel(Base):
    __tablename__ = "outbox_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    event_id: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    topic: Mapped[str] = mapped_column(String, default="dispatch", nullable=False)
    payload_json: Mapped[dict] = mapped_column(JsonObject, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String, default="PENDING", nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

