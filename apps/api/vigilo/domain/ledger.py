from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from .errors import ErrorCode, OopsLoopError, VigiloError


class InventoryState(StrEnum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    SPOILED = "SPOILED"
    DAMAGED = "DAMAGED"
    LOST = "LOST"
    CANCELLED = "CANCELLED"


class LedgerEntryType(StrEnum):
    INTAKE = "INTAKE"
    RESERVATION_HOLD = "RESERVATION_HOLD"
    RESERVATION_RELEASE = "RESERVATION_RELEASE"
    PICKUP_CONFIRMED = "PICKUP_CONFIRMED"
    DELIVERY_CONFIRMED = "DELIVERY_CONFIRMED"
    SPOILAGE_RECORDED = "SPOILAGE_RECORDED"
    DAMAGE_RECORDED = "DAMAGE_RECORDED"
    LOSS_RECORDED = "LOSS_RECORDED"
    COMPENSATING_ADJUSTMENT = "COMPENSATING_ADJUSTMENT"


@dataclass(frozen=True)
class InventoryBalanceSnapshot:
    available: int
    reserved: int
    picked_up: int
    delivered: int
    spoiled: int = 0
    damaged: int = 0
    lost: int = 0

    @property
    def total(self) -> int:
        return (
            self.available
            + self.reserved
            + self.picked_up
            + self.delivered
            + self.spoiled
            + self.damaged
            + self.lost
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "available": self.available,
            "reserved": self.reserved,
            "picked_up": self.picked_up,
            "delivered": self.delivered,
            "spoiled": self.spoiled,
            "damaged": self.damaged,
            "lost": self.lost,
            "total": self.total,
        }


@dataclass(frozen=True)
class InventoryLedgerEntry:
    """Immutable, append-only record of a quantity transition for a batch."""

    id: str
    batch_id: str
    entry_type: LedgerEntryType
    quantity: int
    from_state: InventoryState | None
    to_state: InventoryState
    actor: str
    command: str
    reason: str
    occurred_at: datetime
    balance_after: InventoryBalanceSnapshot
    allocation_id: str | None = None
    delivery_id: str | None = None
    idempotency_key: str | None = None
    correlation_id: str = field(default_factory=lambda: uuid4().hex)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("Ledger entry quantity must be strictly positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "entry_type": self.entry_type.value,
            "quantity": self.quantity,
            "from_state": self.from_state.value if self.from_state else None,
            "to_state": self.to_state.value,
            "actor": self.actor,
            "command": self.command,
            "reason": self.reason,
            "occurred_at": self.occurred_at.isoformat(),
            "balance_after": self.balance_after.to_dict(),
            "allocation_id": self.allocation_id,
            "delivery_id": self.delivery_id,
            "idempotency_key": self.idempotency_key,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ReconciliationReport:
    """Cryptographic or mathematical proof that ledger entries reconcile with batch balance."""

    batch_id: str
    original_quantity: int
    current_balance: InventoryBalanceSnapshot
    reconciled_balance: InventoryBalanceSnapshot
    is_valid: bool
    entry_count: int
    discrepancies: list[str]
    checked_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "original_quantity": self.original_quantity,
            "current_balance": self.current_balance.to_dict(),
            "reconciled_balance": self.reconciled_balance.to_dict(),
            "is_valid": self.is_valid,
            "entry_count": self.entry_count,
            "discrepancies": self.discrepancies,
            "checked_at": self.checked_at.isoformat(),
        }


class InventoryConflictError(VigiloError):
    def __init__(self, message: str, evidence: dict[str, Any] | None = None) -> None:
        super().__init__(
            code=ErrorCode.INVENTORY_CONFLICT,
            message=message,
            evidence=evidence or {},
            retryable=False,
        )


class InventoryInsufficientError(VigiloError):
    def __init__(self, message: str, evidence: dict[str, Any] | None = None) -> None:
        super().__init__(
            code=ErrorCode.INVENTORY_INSUFFICIENT,
            message=message,
            evidence=evidence or {},
            retryable=False,
        )
