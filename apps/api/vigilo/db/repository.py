"""Database repository implementations mapping domain models to persistent storage."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.events import AuditRecord, OperationalEvent
from ..domain.outbox import OutboxMessage, OutboxStatus
from ..domain.ledger import InventoryBalanceSnapshot, InventoryLedgerEntry, InventoryState, LedgerEntryType
from ..domain.models import (
    Allocation,
    AllocationState,
    Batch,
    Delivery,
    DeliveryState,
    GeoLocation,
    Incident,
    IncidentSeverity,
    IncidentStatus,
    ItemRules,
    ReceivingHours,
    Rider,
    RiderStatus,
    Shelter,
    ShelterStatus,
    StorageRequirement,
)
from .models import (
    AllocationModel,
    AuditRecordModel,
    BatchModel,
    DeliveryModel,
    IdempotencyKeyModel,
    IncidentModel,
    InventoryLedgerEntryModel,
    OperationalEventModel,
    OutboxMessageModel,
    RiderModel,
    ShelterModel,
)


class DatabaseRepository:
    """Manages transactional database persistence for all Vigilo domain entities."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # -------------------------------------------------------------------------
    # Batch Persistence
    # -------------------------------------------------------------------------
    def get_batch(self, batch_id: str, for_update: bool = False) -> Batch | None:
        stmt = select(BatchModel).where(BatchModel.id == batch_id)
        if for_update:
            stmt = stmt.with_for_update()
        model = self.session.execute(stmt).scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain_batch(model)

    def save_batch(self, batch: Batch) -> None:
        model = self.session.get(BatchModel, batch.id)
        if model is None:
            model = BatchModel(
                id=batch.id,
                donor_id=batch.donor_id,
                item_type=batch.item_type,
                original_quantity=batch.original_quantity,
                available_quantity=batch.available_quantity,
                reserved_quantity=batch.reserved_quantity,
                picked_up_quantity=batch.picked_up_quantity,
                delivered_quantity=batch.delivered_quantity,
                spoiled_quantity=batch.spoiled_quantity,
                safe_handling_minutes=batch.item_rules.safe_handling_minutes,
                safety_buffer_minutes=batch.item_rules.safety_buffer_minutes,
                required_prerequisites=sorted(list(batch.item_rules.required_prerequisites)),
                storage_requirement=batch.item_rules.storage_requirement.value,
                created_at=batch.created_at,
            )
            self.session.add(model)
        else:
            model.available_quantity = batch.available_quantity
            model.reserved_quantity = batch.reserved_quantity
            model.picked_up_quantity = batch.picked_up_quantity
            model.delivered_quantity = batch.delivered_quantity
            model.spoiled_quantity = batch.spoiled_quantity
            model.safe_handling_minutes = batch.item_rules.safe_handling_minutes
            model.safety_buffer_minutes = batch.item_rules.safety_buffer_minutes
            model.required_prerequisites = sorted(list(batch.item_rules.required_prerequisites))
            model.storage_requirement = batch.item_rules.storage_requirement.value

    def list_batches(self) -> list[Batch]:
        models = self.session.execute(select(BatchModel)).scalars().all()
        return [self._to_domain_batch(m) for m in models]

    # -------------------------------------------------------------------------
    # Rider Persistence
    # -------------------------------------------------------------------------
    def get_rider(self, rider_id: str, for_update: bool = False) -> Rider | None:
        stmt = select(RiderModel).where(RiderModel.id == rider_id)
        if for_update:
            stmt = stmt.with_for_update()
        model = self.session.execute(stmt).scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain_rider(model)

    def save_rider(self, rider: Rider) -> None:
        model = self.session.get(RiderModel, rider.id)
        lat = rider.location.latitude if rider.location else None
        lon = rider.location.longitude if rider.location else None
        status_val = rider.status.value if hasattr(rider.status, "value") else str(rider.status)

        if model is None:
            model = RiderModel(
                id=rider.id,
                user_id=rider.user_id,
                capacity=rider.capacity,
                active_load=rider.active_load,
                available=rider.available,
                status=status_val,
                latitude=lat,
                longitude=lon,
                last_heartbeat_at=rider.last_heartbeat_at,
            )
            self.session.add(model)
        else:
            model.capacity = rider.capacity
            model.active_load = rider.active_load
            model.available = rider.available
            model.status = status_val
            model.latitude = lat
            model.longitude = lon
            model.last_heartbeat_at = rider.last_heartbeat_at

    def list_riders(self) -> list[Rider]:
        models = self.session.execute(select(RiderModel)).scalars().all()
        return [self._to_domain_rider(m) for m in models]

    # -------------------------------------------------------------------------
    # Shelter Persistence
    # -------------------------------------------------------------------------
    def get_shelter(self, shelter_id: str, for_update: bool = False) -> Shelter | None:
        stmt = select(ShelterModel).where(ShelterModel.id == shelter_id)
        if for_update:
            stmt = stmt.with_for_update()
        model = self.session.execute(stmt).scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain_shelter(model)

    def save_shelter(self, shelter: Shelter) -> None:
        model = self.session.get(ShelterModel, shelter.id)
        lat = shelter.location.latitude if shelter.location else None
        lon = shelter.location.longitude if shelter.location else None
        status_val = shelter.status.value if hasattr(shelter.status, "value") else str(shelter.status)

        if model is None:
            model = ShelterModel(
                id=shelter.id,
                name=shelter.name,
                demand_remaining=shelter.demand_remaining,
                receiving_capacity_remaining=shelter.receiving_capacity_remaining,
                prerequisites=sorted(list(shelter.prerequisites)),
                open=shelter.open,
                status=status_val,
                latitude=lat,
                longitude=lon,
                open_hour=shelter.receiving_hours.open_hour,
                close_hour=shelter.receiving_hours.close_hour,
            )
            self.session.add(model)
        else:
            model.name = shelter.name
            model.demand_remaining = shelter.demand_remaining
            model.receiving_capacity_remaining = shelter.receiving_capacity_remaining
            model.prerequisites = sorted(list(shelter.prerequisites))
            model.open = shelter.open
            model.status = status_val
            model.latitude = lat
            model.longitude = lon
            model.open_hour = shelter.receiving_hours.open_hour
            model.close_hour = shelter.receiving_hours.close_hour

    def list_shelters(self) -> list[Shelter]:
        models = self.session.execute(select(ShelterModel)).scalars().all()
        return [self._to_domain_shelter(m) for m in models]

    # -------------------------------------------------------------------------
    # Allocation & Delivery Persistence
    # -------------------------------------------------------------------------
    def get_allocation(self, allocation_id: str, for_update: bool = False) -> Allocation | None:
        stmt = select(AllocationModel).where(AllocationModel.id == allocation_id)
        if for_update:
            stmt = stmt.with_for_update()
        model = self.session.execute(stmt).scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain_allocation(model)

    def save_allocation(self, alloc: Allocation) -> None:
        model = self.session.get(AllocationModel, alloc.id)
        state_val = alloc.state.value if hasattr(alloc.state, "value") else str(alloc.state)

        if model is None:
            model = AllocationModel(
                id=alloc.id,
                batch_id=alloc.batch_id,
                rider_id=alloc.rider_id,
                shelter_id=alloc.shelter_id,
                quantity=alloc.quantity,
                travel_minutes=alloc.travel_minutes,
                handoff_minutes=alloc.handoff_minutes,
                state=state_val,
                claimed_at=alloc.claimed_at,
                safe_until=alloc.safe_until,
                lease_expires_at=alloc.lease_expires_at,
                acknowledged_at=alloc.acknowledged_at,
                picked_up_at=alloc.picked_up_at,
            )
            self.session.add(model)
        else:
            model.state = state_val
            model.lease_expires_at = alloc.lease_expires_at
            model.acknowledged_at = alloc.acknowledged_at
            model.picked_up_at = alloc.picked_up_at

    def get_delivery(self, delivery_id: str, for_update: bool = False) -> Delivery | None:
        stmt = select(DeliveryModel).where(DeliveryModel.id == delivery_id)
        if for_update:
            stmt = stmt.with_for_update()
        model = self.session.execute(stmt).scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain_delivery(model)

    def save_delivery(self, delivery: Delivery) -> None:
        model = self.session.get(DeliveryModel, delivery.id)
        lat = delivery.current_location.latitude if delivery.current_location else None
        lon = delivery.current_location.longitude if delivery.current_location else None
        state_val = delivery.state.value if hasattr(delivery.state, "value") else str(delivery.state)

        if model is None:
            model = DeliveryModel(
                id=delivery.id,
                allocation_id=delivery.allocation_id,
                batch_id=delivery.batch_id,
                rider_id=delivery.rider_id,
                current_shelter_id=delivery.current_shelter_id,
                quantity=delivery.quantity,
                state=state_val,
                picked_up_at=delivery.picked_up_at,
                delivered_at=delivery.delivered_at,
                current_latitude=lat,
                current_longitude=lon,
                destination_history=delivery.destination_history,
            )
            self.session.add(model)
        else:
            model.current_shelter_id = delivery.current_shelter_id
            model.state = state_val
            model.delivered_at = delivery.delivered_at
            model.current_latitude = lat
            model.current_longitude = lon
            model.destination_history = delivery.destination_history

    # -------------------------------------------------------------------------
    # Inventory Ledger Persistence
    # -------------------------------------------------------------------------
    def append_ledger_entry(self, entry: InventoryLedgerEntry) -> None:
        model = InventoryLedgerEntryModel(
            id=entry.id,
            batch_id=entry.batch_id,
            entry_type=entry.entry_type.value,
            quantity=entry.quantity,
            from_state=entry.from_state.value if entry.from_state else None,
            to_state=entry.to_state.value,
            actor=entry.actor,
            command=entry.command,
            reason=entry.reason,
            occurred_at=entry.occurred_at,
            balance_available=entry.balance_after.available,
            balance_reserved=entry.balance_after.reserved,
            balance_picked_up=entry.balance_after.picked_up,
            balance_delivered=entry.balance_after.delivered,
            balance_spoiled=entry.balance_after.spoiled,
            balance_damaged=entry.balance_after.damaged,
            balance_lost=entry.balance_after.lost,
            allocation_id=entry.allocation_id,
            delivery_id=entry.delivery_id,
            idempotency_key=entry.idempotency_key,
            correlation_id=entry.correlation_id,
            metadata_json=entry.metadata,
        )
        self.session.add(model)

    def get_ledger_entries(self, batch_id: str) -> list[InventoryLedgerEntry]:
        stmt = (
            select(InventoryLedgerEntryModel)
            .where(InventoryLedgerEntryModel.batch_id == batch_id)
            .order_by(InventoryLedgerEntryModel.occurred_at.asc())
        )
        models = self.session.execute(stmt).scalars().all()
        return [self._to_domain_ledger_entry(m) for m in models]

    # -------------------------------------------------------------------------
    # Operational Events & Incidents
    # -------------------------------------------------------------------------
    def append_event(self, event: OperationalEvent) -> None:
        model = OperationalEventModel(
            id=event.id,
            event_type=str(event.event_type),
            aggregate_id=event.aggregate_id,
            aggregate_type=event.aggregate_type,
            occurred_at=event.occurred_at,
            payload_json=event.payload,
            actor=event.actor,
            correlation_id=event.correlation_id,
            evidence_json=event.evidence,
        )
        self.session.add(model)

    def list_events(self, limit: int = 50) -> list[OperationalEvent]:
        stmt = select(OperationalEventModel).order_by(OperationalEventModel.occurred_at.desc()).limit(limit)
        models = self.session.execute(stmt).scalars().all()
        return [
            OperationalEvent(
                id=m.id,
                event_type=m.event_type,
                aggregate_id=m.aggregate_id,
                aggregate_type=m.aggregate_type,
                occurred_at=m.occurred_at,
                payload=m.payload_json,
                actor=m.actor,
                correlation_id=m.correlation_id,
                evidence=m.evidence_json,
            )
            for m in reversed(models)
        ]

    def save_incident(self, incident: Incident) -> None:
        model = self.session.get(IncidentModel, incident.id)
        if model is None:
            model = IncidentModel(
                id=incident.id,
                title=incident.title,
                incident_type=incident.incident_type,
                severity=incident.severity.value,
                status=incident.status.value,
                description=incident.description,
                created_at=incident.created_at,
                resolved_at=incident.resolved_at,
                evidence_json=incident.evidence,
            )
            self.session.add(model)
        else:
            model.status = incident.status.value
            model.resolved_at = incident.resolved_at
            model.evidence_json = incident.evidence

    def list_incidents(self) -> list[Incident]:
        models = self.session.execute(select(IncidentModel)).scalars().all()
        return [
            Incident(
                id=m.id,
                title=m.title,
                incident_type=m.incident_type,
                severity=IncidentSeverity(m.severity),
                status=IncidentStatus(m.status),
                description=m.description,
                created_at=m.created_at,
                resolved_at=m.resolved_at,
                evidence=m.evidence_json,
            )
            for m in models
        ]

    # -------------------------------------------------------------------------
    # Audit Records
    # -------------------------------------------------------------------------
    def append_audit_record(self, record: AuditRecord) -> None:
        model = AuditRecordModel(
            id=record.id,
            event_id=record.event_id,
            actor=record.actor,
            command=record.command,
            decision=record.decision,
            constraints_evaluated=record.constraints_evaluated,
            evidence_json=record.evidence,
            created_at=record.created_at,
        )
        self.session.add(model)

    def get_audit_record(self, audit_id: str) -> AuditRecord | None:
        model = self.session.get(AuditRecordModel, audit_id)
        if model is None:
            return None
        return AuditRecord(
            id=model.id,
            event_id=model.event_id or "",
            actor=model.actor,
            command=model.command,
            decision=model.decision,
            constraints_evaluated=model.constraints_evaluated or [],
            evidence=model.evidence_json or {},
            created_at=model.created_at,
        )

    def list_audit_records(self, limit: int = 50) -> list[AuditRecord]:
        stmt = select(AuditRecordModel).order_by(AuditRecordModel.created_at.desc()).limit(limit)
        models = self.session.execute(stmt).scalars().all()
        return [
            AuditRecord(
                id=m.id,
                event_id=m.event_id or "",
                actor=m.actor,
                command=m.command,
                decision=m.decision,
                constraints_evaluated=m.constraints_evaluated or [],
                evidence=m.evidence_json or {},
                created_at=m.created_at,
            )
            for m in models
        ]

    # -------------------------------------------------------------------------
    # Transactional Outbox
    # -------------------------------------------------------------------------
    def append_outbox_message(self, msg: OutboxMessage) -> None:
        model = OutboxMessageModel(
            id=msg.id,
            event_id=msg.event_id,
            event_type=msg.event_type,
            topic=msg.topic,
            payload_json=msg.payload,
            status=msg.status.value,
            retry_count=msg.retry_count,
            last_error=msg.last_error,
            created_at=msg.created_at,
            published_at=msg.published_at,
        )
        self.session.add(model)

    def get_pending_outbox_messages(self, limit: int = 50) -> list[OutboxMessage]:
        stmt = (
            select(OutboxMessageModel)
            .where(OutboxMessageModel.status == "PENDING")
            .order_by(OutboxMessageModel.created_at.asc())
            .limit(limit)
        )
        models = self.session.execute(stmt).scalars().all()
        return [
            OutboxMessage(
                id=m.id,
                event_id=m.event_id,
                event_type=m.event_type,
                topic=m.topic,
                payload=m.payload_json or {},
                status=OutboxStatus(m.status),
                retry_count=m.retry_count,
                last_error=m.last_error,
                created_at=m.created_at,
                published_at=m.published_at,
            )
            for m in models
        ]

    def mark_outbox_message_published(self, msg_id: str, published_at: datetime) -> None:
        model = self.session.get(OutboxMessageModel, msg_id)
        if model is not None:
            model.status = "PUBLISHED"
            model.published_at = published_at
            model.last_error = None

    def mark_outbox_message_failed(self, msg_id: str, error: str) -> None:
        model = self.session.get(OutboxMessageModel, msg_id)
        if model is not None:
            model.retry_count += 1
            model.last_error = error
            if model.retry_count >= 5:
                model.status = "FAILED"

    # -------------------------------------------------------------------------
    # Incident Persistence
    # -------------------------------------------------------------------------
    def get_incident(self, incident_id: str, for_update: bool = False) -> Incident | None:
        stmt = select(IncidentModel).where(IncidentModel.id == incident_id)
        if for_update:
            stmt = stmt.with_for_update()
        model = self.session.execute(stmt).scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain_incident(model)

    def save_incident(self, incident: Incident) -> None:
        model = self.session.get(IncidentModel, incident.id)
        sev_val = incident.severity.value if hasattr(incident.severity, "value") else str(incident.severity)
        status_val = incident.status.value if hasattr(incident.status, "value") else str(incident.status)

        if model is None:
            model = IncidentModel(
                id=incident.id,
                severity=sev_val,
                status=status_val,
                affected_entity_type=incident.affected_entity_type,
                affected_entity_id=incident.affected_entity_id,
                reason_code=incident.reason_code,
                description=incident.description,
                evidence=incident.evidence or {},
                created_at=incident.created_at,
                resolved_at=incident.resolved_at,
            )
            self.session.add(model)
        else:
            model.severity = sev_val
            model.status = status_val
            model.description = incident.description
            model.evidence = incident.evidence or {}
            model.resolved_at = incident.resolved_at

    def list_incidents(
        self,
        status: str | None = None,
        severity: str | None = None,
        affected_entity_type: str | None = None,
        limit: int = 50,
    ) -> list[Incident]:
        stmt = select(IncidentModel).order_by(IncidentModel.created_at.desc())
        if status:
            stmt = stmt.where(IncidentModel.status == status)
        if severity:
            stmt = stmt.where(IncidentModel.severity == severity)
        if affected_entity_type:
            stmt = stmt.where(IncidentModel.affected_entity_type == affected_entity_type)
        stmt = stmt.limit(limit)
        models = self.session.execute(stmt).scalars().all()
        return [self._to_domain_incident(m) for m in models]

    @staticmethod
    def _to_domain_incident(m: IncidentModel) -> Incident:
        return Incident(
            id=m.id,
            severity=IncidentSeverity(m.severity),
            status=IncidentStatus(m.status),
            affected_entity_type=m.affected_entity_type,
            affected_entity_id=m.affected_entity_id,
            reason_code=m.reason_code,
            description=m.description,
            created_at=m.created_at,
            evidence=m.evidence or {},
            resolved_at=m.resolved_at,
        )

    # -------------------------------------------------------------------------
    # Domain Mapping Helpers
    # -------------------------------------------------------------------------
    @staticmethod
    def _to_domain_batch(m: BatchModel) -> Batch:
        return Batch(
            id=m.id,
            donor_id=m.donor_id or "donor_default",
            item_type=m.item_type,
            original_quantity=m.original_quantity,
            available_quantity=m.available_quantity,
            reserved_quantity=m.reserved_quantity,
            picked_up_quantity=m.picked_up_quantity,
            delivered_quantity=m.delivered_quantity,
            spoiled_quantity=m.spoiled_quantity,
            item_rules=ItemRules(
                safe_handling_minutes=m.safe_handling_minutes,
                safety_buffer_minutes=m.safety_buffer_minutes,
                required_prerequisites=frozenset(m.required_prerequisites or []),
                storage_requirement=StorageRequirement(m.storage_requirement),
            ),
            created_at=m.created_at,
        )

    @staticmethod
    def _to_domain_rider(m: RiderModel) -> Rider:
        loc = GeoLocation(latitude=m.latitude, longitude=m.longitude) if m.latitude is not None and m.longitude is not None else None
        return Rider(
            id=m.id,
            user_id=m.user_id,
            capacity=m.capacity,
            active_load=m.active_load,
            available=m.available,
            status=RiderStatus(m.status),
            location=loc,
            last_heartbeat_at=m.last_heartbeat_at,
        )

    @staticmethod
    def _to_domain_shelter(m: ShelterModel) -> Shelter:
        loc = GeoLocation(latitude=m.latitude, longitude=m.longitude) if m.latitude is not None and m.longitude is not None else None
        return Shelter(
            id=m.id,
            name=m.name,
            demand_remaining=m.demand_remaining,
            receiving_capacity_remaining=m.receiving_capacity_remaining,
            prerequisites=frozenset(m.prerequisites or []),
            open=m.open,
            status=ShelterStatus(m.status),
            location=loc,
            receiving_hours=ReceivingHours(open_hour=m.open_hour, close_hour=m.close_hour),
        )

    @staticmethod
    def _to_domain_allocation(m: AllocationModel) -> Allocation:
        return Allocation(
            id=m.id,
            batch_id=m.batch_id,
            rider_id=m.rider_id,
            shelter_id=m.shelter_id,
            quantity=m.quantity,
            travel_minutes=m.travel_minutes,
            handoff_minutes=m.handoff_minutes,
            state=AllocationState(m.state),
            claimed_at=m.claimed_at,
            safe_until=m.safe_until,
            lease_expires_at=m.lease_expires_at,
            acknowledged_at=m.acknowledged_at,
            picked_up_at=m.picked_up_at,
        )

    @staticmethod
    def _to_domain_delivery(m: DeliveryModel) -> Delivery:
        loc = GeoLocation(latitude=m.current_latitude, longitude=m.current_longitude) if m.current_latitude is not None and m.current_longitude is not None else None
        return Delivery(
            id=m.id,
            allocation_id=m.allocation_id,
            batch_id=m.batch_id,
            rider_id=m.rider_id,
            current_shelter_id=m.current_shelter_id,
            quantity=m.quantity,
            state=DeliveryState(m.state),
            picked_up_at=m.picked_up_at,
            delivered_at=m.delivered_at,
            current_location=loc,
            destination_history=m.destination_history or [],
        )

    @staticmethod
    def _to_domain_ledger_entry(m: InventoryLedgerEntryModel) -> InventoryLedgerEntry:
        return InventoryLedgerEntry(
            id=m.id,
            batch_id=m.batch_id,
            entry_type=LedgerEntryType(m.entry_type),
            quantity=m.quantity,
            from_state=InventoryState(m.from_state) if m.from_state else None,
            to_state=InventoryState(m.to_state),
            actor=m.actor,
            command=m.command,
            reason=m.reason,
            occurred_at=m.occurred_at,
            balance_after=InventoryBalanceSnapshot(
                available=m.balance_available,
                reserved=m.balance_reserved,
                picked_up=m.balance_picked_up,
                delivered=m.balance_delivered,
                spoiled=m.balance_spoiled,
                damaged=m.balance_damaged,
                lost=m.balance_lost,
            ),
            allocation_id=m.allocation_id,
            delivery_id=m.delivery_id,
            idempotency_key=m.idempotency_key,
            correlation_id=m.correlation_id,
            metadata=m.metadata_json or {},
        )
