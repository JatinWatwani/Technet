from __future__ import annotations

from typing import Set

from .errors import StateTransitionError
from .models import AllocationState, DeliveryState, RiderStatus, ShelterStatus


class AllocationStateMachine:
    """State machine governing unpicked allocation lifecycle.

    Invariant:
    An allocation in PICKED_UP state has transferred to physical custody
    and can NEVER be transitioned to EXPIRED or CANCELLED through the allocation lease worker.
    """

    ALLOWED_TRANSITIONS: dict[AllocationState, Set[AllocationState]] = {
        AllocationState.CLAIMED: {
            AllocationState.ACKNOWLEDGED,
            AllocationState.PICKED_UP,
            AllocationState.EXPIRED,
            AllocationState.CANCELLED,
        },
        AllocationState.ACKNOWLEDGED: {
            AllocationState.PICKED_UP,
            AllocationState.EXPIRED,
            AllocationState.CANCELLED,
        },
        AllocationState.PICKED_UP: set(),  # Terminal for allocation; handoff to Delivery
        AllocationState.EXPIRED: set(),    # Terminal
        AllocationState.CANCELLED: set(),  # Terminal
    }

    @classmethod
    def can_transition(cls, from_state: AllocationState, to_state: AllocationState) -> bool:
        return to_state in cls.ALLOWED_TRANSITIONS.get(from_state, set())

    @classmethod
    def validate_transition(cls, from_state: AllocationState, to_state: AllocationState, allocation_id: str = "") -> None:
        if not cls.can_transition(from_state, to_state):
            raise StateTransitionError(
                entity=f"Allocation({allocation_id})" if allocation_id else "Allocation",
                current_state=from_state.value,
                attempted_state=to_state.value,
                reason="Disallowed allocation state transition",
            )


class DeliveryStateMachine:
    """State machine governing physical custody of in-transit cargo.

    Invariant:
    Physical cargo is strictly tracked and never returned to unpicked stock.
    Disruptions transition to REROUTE_PENDING or INCIDENT_REVIEW.
    """

    ALLOWED_TRANSITIONS: dict[DeliveryState, Set[DeliveryState]] = {
        DeliveryState.PICKED_UP: {
            DeliveryState.IN_TRANSIT,
            DeliveryState.REROUTE_PENDING,
            DeliveryState.DELIVERED,
            DeliveryState.INCIDENT_REVIEW,
        },
        DeliveryState.IN_TRANSIT: {
            DeliveryState.DELIVERED,
            DeliveryState.REROUTE_PENDING,
            DeliveryState.INCIDENT_REVIEW,
        },
        DeliveryState.REROUTE_PENDING: {
            DeliveryState.IN_TRANSIT,
            DeliveryState.DELIVERED,
            DeliveryState.INCIDENT_REVIEW,
        },
        DeliveryState.DELIVERED: set(),       # Terminal
        DeliveryState.INCIDENT_REVIEW: {      # Can resume to reroute or be closed
            DeliveryState.REROUTE_PENDING,
            DeliveryState.IN_TRANSIT,
        },
    }

    @classmethod
    def can_transition(cls, from_state: DeliveryState, to_state: DeliveryState) -> bool:
        return to_state in cls.ALLOWED_TRANSITIONS.get(from_state, set())

    @classmethod
    def validate_transition(cls, from_state: DeliveryState, to_state: DeliveryState, delivery_id: str = "") -> None:
        if not cls.can_transition(from_state, to_state):
            raise StateTransitionError(
                entity=f"Delivery({delivery_id})" if delivery_id else "Delivery",
                current_state=from_state.value,
                attempted_state=to_state.value,
                reason="Disallowed delivery physical custody state transition",
            )


class ShelterStateMachine:
    """State machine governing receiving center status."""

    ALLOWED_TRANSITIONS: dict[ShelterStatus, Set[ShelterStatus]] = {
        ShelterStatus.OPEN: {
            ShelterStatus.AT_CAPACITY,
            ShelterStatus.CLOSED,
        },
        ShelterStatus.AT_CAPACITY: {
            ShelterStatus.OPEN,
            ShelterStatus.CLOSED,
        },
        ShelterStatus.CLOSED: {
            ShelterStatus.REOPENING_REVIEW,
            ShelterStatus.OPEN,
        },
        ShelterStatus.REOPENING_REVIEW: {
            ShelterStatus.OPEN,
            ShelterStatus.CLOSED,
        },
    }

    @classmethod
    def can_transition(cls, from_state: ShelterStatus, to_state: ShelterStatus) -> bool:
        return to_state in cls.ALLOWED_TRANSITIONS.get(from_state, set())

    @classmethod
    def validate_transition(cls, from_state: ShelterStatus, to_state: ShelterStatus, shelter_id: str = "") -> None:
        if not cls.can_transition(from_state, to_state):
            raise StateTransitionError(
                entity=f"Shelter({shelter_id})" if shelter_id else "Shelter",
                current_state=from_state.value,
                attempted_state=to_state.value,
                reason="Disallowed shelter operational status transition",
            )


class RiderStateMachine:
    """State machine governing volunteer rider operational availability."""

    ALLOWED_TRANSITIONS: dict[RiderStatus, Set[RiderStatus]] = {
        RiderStatus.AVAILABLE: {
            RiderStatus.ASSIGNED,
            RiderStatus.PAUSED,
            RiderStatus.OFFLINE,
        },
        RiderStatus.ASSIGNED: {
            RiderStatus.IN_TRANSIT,
            RiderStatus.AVAILABLE,
            RiderStatus.PAUSED,
            RiderStatus.OFFLINE,
        },
        RiderStatus.IN_TRANSIT: {
            RiderStatus.AVAILABLE,
            RiderStatus.ASSIGNED,
            RiderStatus.PAUSED,
            RiderStatus.OFFLINE,
        },
        RiderStatus.PAUSED: {
            RiderStatus.AVAILABLE,
            RiderStatus.OFFLINE,
        },
        RiderStatus.OFFLINE: {
            RiderStatus.AVAILABLE,
        },
    }

    @classmethod
    def can_transition(cls, from_state: RiderStatus, to_state: RiderStatus) -> bool:
        return to_state in cls.ALLOWED_TRANSITIONS.get(from_state, set())

    @classmethod
    def validate_transition(cls, from_state: RiderStatus, to_state: RiderStatus, rider_id: str = "") -> None:
        if not cls.can_transition(from_state, to_state):
            raise StateTransitionError(
                entity=f"Rider({rider_id})" if rider_id else "Rider",
                current_state=from_state.value,
                attempted_state=to_state.value,
                reason="Disallowed rider availability state transition",
            )
