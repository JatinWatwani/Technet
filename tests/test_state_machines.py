import pytest

from oopsloop.domain.errors import StateTransitionError
from oopsloop.domain.models import AllocationState, DeliveryState, RiderStatus, ShelterStatus
from oopsloop.domain.state_machines import (
    AllocationStateMachine,
    DeliveryStateMachine,
    RiderStateMachine,
    ShelterStateMachine,
)


def test_allocation_state_machine_valid_transitions():
    # Happy path: CLAIMED -> ACKNOWLEDGED -> PICKED_UP
    AllocationStateMachine.validate_transition(AllocationState.CLAIMED, AllocationState.ACKNOWLEDGED)
    AllocationStateMachine.validate_transition(AllocationState.ACKNOWLEDGED, AllocationState.PICKED_UP)

    # Expiry before pickup
    AllocationStateMachine.validate_transition(AllocationState.CLAIMED, AllocationState.EXPIRED)
    AllocationStateMachine.validate_transition(AllocationState.ACKNOWLEDGED, AllocationState.EXPIRED)

    # Direct pickup from CLAIMED (fast flow)
    AllocationStateMachine.validate_transition(AllocationState.CLAIMED, AllocationState.PICKED_UP)


def test_allocation_state_machine_prevents_picked_up_expiry():
    # CRITICAL INVARIANT: Picked up cargo cannot be expired by unpicked lease worker!
    with pytest.raises(StateTransitionError):
        AllocationStateMachine.validate_transition(AllocationState.PICKED_UP, AllocationState.EXPIRED)

    with pytest.raises(StateTransitionError):
        AllocationStateMachine.validate_transition(AllocationState.PICKED_UP, AllocationState.CANCELLED)

    with pytest.raises(StateTransitionError):
        AllocationStateMachine.validate_transition(AllocationState.EXPIRED, AllocationState.PICKED_UP)


def test_delivery_state_machine_physical_custody():
    # Normal delivery
    DeliveryStateMachine.validate_transition(DeliveryState.PICKED_UP, DeliveryState.IN_TRANSIT)
    DeliveryStateMachine.validate_transition(DeliveryState.IN_TRANSIT, DeliveryState.DELIVERED)

    # In-transit disruption & reroute
    DeliveryStateMachine.validate_transition(DeliveryState.IN_TRANSIT, DeliveryState.REROUTE_PENDING)
    DeliveryStateMachine.validate_transition(DeliveryState.REROUTE_PENDING, DeliveryState.IN_TRANSIT)
    DeliveryStateMachine.validate_transition(DeliveryState.REROUTE_PENDING, DeliveryState.DELIVERED)

    # Incident escalation
    DeliveryStateMachine.validate_transition(DeliveryState.IN_TRANSIT, DeliveryState.INCIDENT_REVIEW)

    # Terminal state: DELIVERED cannot transition back to IN_TRANSIT
    with pytest.raises(StateTransitionError):
        DeliveryStateMachine.validate_transition(DeliveryState.DELIVERED, DeliveryState.IN_TRANSIT)


def test_shelter_state_machine():
    ShelterStateMachine.validate_transition(ShelterStatus.OPEN, ShelterStatus.AT_CAPACITY)
    ShelterStateMachine.validate_transition(ShelterStatus.AT_CAPACITY, ShelterStatus.OPEN)
    ShelterStateMachine.validate_transition(ShelterStatus.OPEN, ShelterStatus.CLOSED)
    ShelterStateMachine.validate_transition(ShelterStatus.CLOSED, ShelterStatus.REOPENING_REVIEW)
    ShelterStateMachine.validate_transition(ShelterStatus.REOPENING_REVIEW, ShelterStatus.OPEN)

    # Cannot jump directly from AT_CAPACITY to REOPENING_REVIEW
    with pytest.raises(StateTransitionError):
        ShelterStateMachine.validate_transition(ShelterStatus.AT_CAPACITY, ShelterStatus.REOPENING_REVIEW)


def test_rider_state_machine():
    RiderStateMachine.validate_transition(RiderStatus.AVAILABLE, RiderStatus.ASSIGNED)
    RiderStateMachine.validate_transition(RiderStatus.ASSIGNED, RiderStatus.IN_TRANSIT)
    RiderStateMachine.validate_transition(RiderStatus.IN_TRANSIT, RiderStatus.AVAILABLE)
    RiderStateMachine.validate_transition(RiderStatus.AVAILABLE, RiderStatus.OFFLINE)
    RiderStateMachine.validate_transition(RiderStatus.OFFLINE, RiderStatus.AVAILABLE)

    # OFFLINE rider cannot immediately be marked IN_TRANSIT
    with pytest.raises(StateTransitionError):
        RiderStateMachine.validate_transition(RiderStatus.OFFLINE, RiderStatus.IN_TRANSIT)
