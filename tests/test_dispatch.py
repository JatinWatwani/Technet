from datetime import datetime, timezone

import pytest

from oopsloop.domain.dispatch import DispatchError, DispatchRequest, DispatchService
from oopsloop.domain.models import Batch, ItemRules, Rider, Shelter


NOW = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)


def make_service(*, prerequisites=frozenset(), safe_minutes=180) -> DispatchService:
    service = DispatchService()
    service.batches["batch-1"] = Batch(
        id="batch-1",
        original_quantity=100,
        item_rules=ItemRules(
            safe_handling_minutes=safe_minutes,
            safety_buffer_minutes=10,
            required_prerequisites=prerequisites,
        ),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    service.riders["rider-1"] = Rider(id="rider-1", capacity=60)
    service.shelters["shelter-1"] = Shelter(
        id="shelter-1",
        demand_remaining=100,
        receiving_capacity_remaining=100,
    )
    return service


def request(**overrides) -> DispatchRequest:
    values = {
        "batch_id": "batch-1",
        "rider_id": "rider-1",
        "shelter_id": "shelter-1",
        "quantity": 40,
        "travel_minutes": 30,
        "handoff_minutes": 10,
        "now": NOW,
    }
    values.update(overrides)
    return DispatchRequest(**values)


def test_commit_conserves_inventory_and_updates_capacity():
    service = make_service()

    allocation = service.commit(request())

    assert allocation.quantity == 40
    assert service.batches["batch-1"].available_quantity == 60
    assert service.riders["rider-1"].active_load == 40
    assert service.shelters["shelter-1"].demand_remaining == 60
    assert service.shelters["shelter-1"].receiving_capacity_remaining == 60


def test_rejects_assignment_that_exceeds_rider_capacity():
    service = make_service()

    decision = service.preview(request(quantity=61))

    assert not decision.feasible
    assert decision.reason_code == "RIDER_CAPACITY_EXCEEDED"


def test_rejects_assignment_past_safe_handling_deadline():
    service = make_service(safe_minutes=50)

    decision = service.preview(request(travel_minutes=40, handoff_minutes=10))

    assert not decision.feasible
    assert decision.reason_code == "SAFETY_DEADLINE_UNSAFE"


def test_rejects_missing_prerequisite():
    service = make_service(prerequisites=frozenset({"clean_water", "cooking_fuel"}))

    decision = service.preview(request())

    assert not decision.feasible
    assert decision.reason_code == "MISSING_PREREQUISITE"
    assert decision.evidence["missing"] == ["clean_water", "cooking_fuel"]


def test_rejected_commit_does_not_mutate_state():
    service = make_service()
    service.riders["rider-1"].available = False

    with pytest.raises(DispatchError) as exc_info:
        service.commit(request())

    assert exc_info.value.code == "RIDER_UNAVAILABLE"
    assert service.batches["batch-1"].available_quantity == 100
    assert service.riders["rider-1"].active_load == 0
