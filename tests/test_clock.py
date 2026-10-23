from datetime import datetime, timedelta, timezone

from vigilo.domain.clock import SimulatedClock, SystemClock


def test_system_clock():
    clock = SystemClock()
    t1 = clock.now()
    assert t1.tzinfo is not None
    assert t1.tzinfo == timezone.utc


def test_simulated_clock():
    base = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    clock = SimulatedClock(base)
    assert clock.now() == base

    # Advance by timedelta
    clock.advance(timedelta(minutes=30))
    assert clock.now() == datetime(2026, 5, 1, 12, 30, 0, tzinfo=timezone.utc)

    # Advance by seconds
    clock.advance(90)
    assert clock.now() == datetime(2026, 5, 1, 12, 31, 30, tzinfo=timezone.utc)

    # Advance by minutes
    clock.advance_minutes(15)
    assert clock.now() == datetime(2026, 5, 1, 12, 46, 30, tzinfo=timezone.utc)

    # Set time
    target = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    clock.set_time(target)
    assert clock.now() == target
