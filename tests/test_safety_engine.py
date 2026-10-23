from datetime import datetime, timedelta, timezone
import pytest

from vigilo.domain.errors import ErrorCode
from vigilo.domain.models import (
    Batch,
    ItemRules,
    ReceivingHours,
    Rider,
    RiderStatus,
    Shelter,
    ShelterStatus,
    StorageRequirement,
)
from vigilo.domain.safety_engine import SafetyEngine

NOW = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def base_batch():
    return Batch(
        id="batch_safe",
        original_quantity=100,
        item_rules=ItemRules(safe_handling_minutes=180, safety_buffer_minutes=15),
        created_at=datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def base_rider():
    return Rider(id="rider_safe", capacity=50, available=True, last_heartbeat_at=NOW)


@pytest.fixture
def base_shelter():
    return Shelter(
        id="shelter_safe",
        demand_remaining=100,
        receiving_capacity_remaining=100,
        open=True,
        receiving_hours=ReceivingHours(open_hour=6, close_hour=23),
    )


def test_safety_engine_passes_all_valid_constraints(base_batch, base_rider, base_shelter):
    report = SafetyEngine.evaluate_feasibility(
        batch=base_batch,
        rider=base_rider,
        shelter=base_shelter,
        quantity=30,
        travel_minutes=25,
        handoff_minutes=10,
        now=NOW,
    )
    assert report.feasible is True
    assert report.primary_failure_code is None
    assert len(report.evaluated_rules) >= 10


def test_safety_engine_rejects_negative_quantity_and_durations(base_batch, base_rider, base_shelter):
    report_qty = SafetyEngine.evaluate_feasibility(
        batch=base_batch,
        rider=base_rider,
        shelter=base_shelter,
        quantity=0,
        travel_minutes=25,
        handoff_minutes=10,
        now=NOW,
    )
    assert not report_qty.feasible
    assert report_qty.primary_failure_code == ErrorCode.INVALID_QUANTITY

    report_dur = SafetyEngine.evaluate_feasibility(
        batch=base_batch,
        rider=base_rider,
        shelter=base_shelter,
        quantity=20,
        travel_minutes=-5,
        handoff_minutes=10,
        now=NOW,
    )
    assert not report_dur.feasible
    assert report_dur.primary_failure_code == ErrorCode.INVALID_DURATION


def test_safety_engine_rejects_cold_chain_without_refrigeration(base_rider, base_shelter):
    cold_batch = Batch(
        id="batch_cold",
        original_quantity=50,
        item_rules=ItemRules(
            safe_handling_minutes=300,
            storage_requirement=StorageRequirement.COLD,
        ),
        created_at=NOW,
    )
    # Shelter has no refrigeration prerequisite
    base_shelter.prerequisites = frozenset({"clean_water"})

    report = SafetyEngine.evaluate_feasibility(
        batch=cold_batch,
        rider=base_rider,
        shelter=base_shelter,
        quantity=20,
        travel_minutes=20,
        handoff_minutes=10,
        now=NOW,
    )
    assert not report.feasible
    assert report.primary_failure_code == ErrorCode.MISSING_PREREQUISITE
    assert "refrigeration" in report.primary_failure_reason


def test_safety_engine_rejects_arrival_outside_receiving_hours(base_batch, base_rider, base_shelter):
    # Shelter open only 11am to 2pm (open_hour=11, close_hour=14)
    base_shelter.receiving_hours = ReceivingHours(open_hour=11, close_hour=14)

    # NOW is 10:00. Trip takes 20 mins travel + 10 mins handoff (+ 15 buffer) = 45 min -> arrival at 10:45 (hour 10, outside 11-14)
    report = SafetyEngine.evaluate_feasibility(
        batch=base_batch,
        rider=base_rider,
        shelter=base_shelter,
        quantity=20,
        travel_minutes=20,
        handoff_minutes=10,
        now=NOW,
    )
    assert not report.feasible
    assert report.primary_failure_code == ErrorCode.DESTINATION_UNAVAILABLE
    assert "receiving hours" in report.primary_failure_reason


def test_safety_engine_rejects_inaccessible_flood_route(base_batch, base_rider, base_shelter):
    # Hazard / flood disruption flag
    report = SafetyEngine.evaluate_feasibility(
        batch=base_batch,
        rider=base_rider,
        shelter=base_shelter,
        quantity=20,
        travel_minutes=20,
        handoff_minutes=10,
        now=NOW,
        is_route_accessible=False,
    )
    assert not report.feasible
    assert report.primary_failure_code == ErrorCode.ROUTE_INFEASIBLE
    assert "blocked or rendered inaccessible" in report.primary_failure_reason


def test_safety_engine_rejects_stale_rider_telemetry(base_batch, base_rider, base_shelter):
    # Rider last heartbeat 3 hours ago (> max 120 mins)
    base_rider.last_heartbeat_at = NOW - timedelta(hours=3)

    report = SafetyEngine.evaluate_feasibility(
        batch=base_batch,
        rider=base_rider,
        shelter=base_shelter,
        quantity=20,
        travel_minutes=20,
        handoff_minutes=10,
        now=NOW,
        max_heartbeat_staleness_minutes=120,
    )
    assert not report.feasible
    assert report.primary_failure_code == ErrorCode.RIDER_HEARTBEAT_EXPIRED
