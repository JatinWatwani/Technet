from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    # Inventory errors
    INVENTORY_INSUFFICIENT = "INVENTORY_INSUFFICIENT"
    INVENTORY_CONFLICT = "INVENTORY_CONFLICT"
    INVALID_QUANTITY = "INVALID_QUANTITY"
    BATCH_NOT_FOUND = "BATCH_NOT_FOUND"

    # Rider errors
    RIDER_NOT_FOUND = "RIDER_NOT_FOUND"
    RIDER_CAPACITY_EXCEEDED = "RIDER_CAPACITY_EXCEEDED"
    RIDER_UNAVAILABLE = "RIDER_UNAVAILABLE"
    RIDER_HEARTBEAT_EXPIRED = "RIDER_HEARTBEAT_EXPIRED"

    # Shelter errors
    SHELTER_NOT_FOUND = "SHELTER_NOT_FOUND"
    SHELTER_CLOSED = "SHELTER_CLOSED"
    SHELTER_DEMAND_EXCEEDED = "SHELTER_DEMAND_EXCEEDED"
    SHELTER_CAPACITY_EXCEEDED = "SHELTER_CAPACITY_EXCEEDED"
    MISSING_PREREQUISITE = "MISSING_PREREQUISITE"

    # Safety and routing errors
    SAFETY_DEADLINE_UNSAFE = "SAFETY_DEADLINE_UNSAFE"
    DESTINATION_UNAVAILABLE = "DESTINATION_UNAVAILABLE"
    ROUTE_INFEASIBLE = "ROUTE_INFEASIBLE"
    INVALID_DURATION = "INVALID_DURATION"

    # State & transaction errors
    CLAIM_EXPIRED = "CLAIM_EXPIRED"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    STALE_VERSION = "STALE_VERSION"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    RECOVERY_NOT_FEASIBLE = "RECOVERY_NOT_FEASIBLE"
    ALLOCATION_NOT_FOUND = "ALLOCATION_NOT_FOUND"
    DELIVERY_NOT_FOUND = "DELIVERY_NOT_FOUND"
    INCIDENT_NOT_FOUND = "INCIDENT_NOT_FOUND"
    DISPATCH_REJECTED = "DISPATCH_REJECTED"


class VigiloError(Exception):
    """Base class for all domain and operational exceptions in Vigilo."""

    def __init__(
        self,
        code: ErrorCode | str,
        message: str,
        evidence: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = str(code)
        self.message = message
        self.evidence = evidence or {}
        self.retryable = retryable

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "evidence": self.evidence,
            "retryable": self.retryable,
        }


# Backwards compatibility alias
OopsLoopError = VigiloError


class DomainError(VigiloError):
    """Domain business logic or invariant violation."""
    pass


class StateTransitionError(DomainError):
    """Raised when an invalid state machine transition is attempted."""

    def __init__(
        self,
        entity: str,
        current_state: str,
        attempted_state: str,
        reason: str | None = None,
    ) -> None:
        msg = f"Invalid transition for {entity} from {current_state} to {attempted_state}"
        if reason:
            msg += f": {reason}"
        super().__init__(
            code=ErrorCode.INVALID_STATE_TRANSITION,
            message=msg,
            evidence={
                "entity": entity,
                "current_state": current_state,
                "attempted_state": attempted_state,
                "reason": reason,
            },
            retryable=False,
        )


class EntityNotFoundError(DomainError):
    """Raised when a required domain aggregate is missing."""

    def __init__(self, code: ErrorCode | str, entity: str, entity_id: str) -> None:
        super().__init__(
            code=code,
            message=f"{entity} with id '{entity_id}' not found",
            evidence={"entity": entity, "id": entity_id},
            retryable=False,
        )


class ConstraintViolationError(DomainError):
    """Raised when an assignment violates hard constraints."""
    pass
