from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone


class Clock(ABC):
    """Abstract authoritative clock interface for domain and simulation operations."""

    @abstractmethod
    def now(self) -> datetime:
        """Return the current authoritative time (always timezone-aware UTC)."""
        raise NotImplementedError


class SystemClock(Clock):
    """Wall-clock implementation for live production operations."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class SimulatedClock(Clock):
    """Controllable, deterministic clock for testing and simulation scenarios."""

    def __init__(self, initial_time: datetime | None = None) -> None:
        if initial_time is None:
            self._current_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        elif initial_time.tzinfo is None:
            self._current_time = initial_time.replace(tzinfo=timezone.utc)
        else:
            self._current_time = initial_time.astimezone(timezone.utc)

    def now(self) -> datetime:
        return self._current_time

    def set_time(self, new_time: datetime) -> None:
        if new_time.tzinfo is None:
            self._current_time = new_time.replace(tzinfo=timezone.utc)
        else:
            self._current_time = new_time.astimezone(timezone.utc)

    def advance(self, delta: timedelta | int | float) -> datetime:
        """Advance the simulated clock by timedelta or number of seconds."""
        if isinstance(delta, (int, float)):
            delta = timedelta(seconds=delta)
        self._current_time += delta
        return self._current_time

    def advance_minutes(self, minutes: int | float) -> datetime:
        return self.advance(timedelta(minutes=minutes))
