from datetime import datetime, timedelta, timezone
import pytest

from vigilo.domain.models import Batch, ItemRules
from vigilo.domain.safety_engine import SafetyEngine
from vigilo.domain.dispatch import DispatchService


@pytest.fixture
def test_batch():
    # Created at 10:00, safe_handling_minutes=180 (until 13:00), buffer=15
    return Batch(
        id="batch_clock_test",
        original_quantity=50,
        item_rules=ItemRules(safe_handling_minutes=180, safety_buffer_minutes=15),
        created_at=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
    )


def test_last_safe_decision_ample_window(test_batch):
    # Total overhead = 20 (travel) + 10 (handoff) + 15 (buffer) + 3 (confirm) + 2 (notify) = 50 min
    # Safe deadline is 13:00.
    # Latest useful decision = 13:00 - 50 min = 12:10.
    # Now is 11:00 -> remaining decision window = 70 min.
    now = datetime(2026, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
    clock = SafetyEngine.calculate_last_safe_decision(
        batch=test_batch,
        shelter_id="shelter_1",
        travel_minutes=20,
        handoff_minutes=10,
        now=now,
    )

    assert clock.is_feasible is True
    assert clock.is_urgently_closing is False
    assert clock.remaining_decision_window_minutes == 70.0
    assert clock.remaining_safe_handling_minutes == 120.0
    assert clock.safe_deadline == datetime(2026, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
    assert clock.latest_useful_decision_time == datetime(2026, 1, 1, 12, 10, 0, tzinfo=timezone.utc)
    assert clock.invalidating_factors == []


def test_last_safe_decision_urgent_window(test_batch):
    # Overhead = 50 min. Latest useful decision = 12:10.
    # Now is 12:00 -> remaining decision window = 10 min (<= 15 min threshold).
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    clock = SafetyEngine.calculate_last_safe_decision(
        batch=test_batch,
        shelter_id="shelter_1",
        travel_minutes=20,
        handoff_minutes=10,
        now=now,
    )

    assert clock.is_feasible is True
    assert clock.is_urgently_closing is True
    assert clock.remaining_decision_window_minutes == 10.0
    assert clock.invalidating_factors == []


def test_last_safe_decision_expired_window(test_batch):
    # Overhead = 50 min. Latest useful decision = 12:10.
    # Now is 12:15 -> decision window has expired by 5 minutes.
    now = datetime(2026, 1, 1, 12, 15, 0, tzinfo=timezone.utc)
    clock = SafetyEngine.calculate_last_safe_decision(
        batch=test_batch,
        shelter_id="shelter_1",
        travel_minutes=20,
        handoff_minutes=10,
        now=now,
    )

    assert clock.is_feasible is False
    assert clock.is_urgently_closing is False
    assert clock.remaining_decision_window_minutes == -5.0
    assert "decision_window_expired" in clock.invalidating_factors


def test_dispatch_service_calculate_safety_clock():
    service = DispatchService()
    service.load_seed()

    # batch_oversized_180 created at 09:00 with safe_handling_minutes=180 (safe until 12:00)
    # now in seed is 09:00
    clock = service.calculate_safety_clock(
        batch_id="batch_oversized_180",
        shelter_id="shelter_central",
        travel_minutes=30,
        handoff_minutes=15,
    )

    assert clock.batch_id == "batch_oversized_180"
    assert clock.is_feasible is True
    assert clock.remaining_decision_window_minutes > 0
