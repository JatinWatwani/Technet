"""Transactional Outbox domain models and publisher."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Callable
from uuid import uuid4

from .events import OperationalEvent


class OutboxStatus(StrEnum):
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


@dataclass
class OutboxMessage:
    id: str
    event_id: str
    event_type: str
    topic: str
    payload: dict[str, Any]
    status: OutboxStatus = OutboxStatus.PENDING
    retry_count: int = 0
    last_error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    published_at: datetime | None = None

    @classmethod
    def from_event(
        cls,
        event: OperationalEvent,
        topic: str = "dispatch",
    ) -> OutboxMessage:
        return cls(
            id=f"outbox_{uuid4().hex}",
            event_id=event.id,
            event_type=str(event.event_type),
            topic=topic,
            payload=event.to_dict(),
            created_at=event.occurred_at,
        )

    def mark_published(self, published_at: datetime | None = None) -> None:
        self.status = OutboxStatus.PUBLISHED
        self.published_at = published_at or datetime.now(timezone.utc)
        self.last_error = None

    def mark_failed(self, error: str) -> None:
        self.retry_count += 1
        self.last_error = error
        if self.retry_count >= 5:
            self.status = OutboxStatus.FAILED
        else:
            self.status = OutboxStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "topic": self.topic,
            "payload": self.payload,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat(),
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }


class OutboxPublisher:
    """Manages event publication and safe dispatch to external subscribers."""

    def __init__(self) -> None:
        self._subscribers: list[Callable[[OutboxMessage], bool]] = []
        self._published_history: list[OutboxMessage] = []

    def subscribe(self, subscriber: Callable[[OutboxMessage], bool]) -> None:
        self._subscribers.append(subscriber)

    def publish(self, message: OutboxMessage, now: datetime | None = None) -> bool:
        """Dispatches outbox message to all subscribers and tracks delivery."""
        delivery_time = now or datetime.now(timezone.utc)
        try:
            for sub in self._subscribers:
                success = sub(message)
                if not success:
                    message.mark_failed("Subscriber rejected message")
                    return False
            message.mark_published(delivery_time)
            self._published_history.append(message)
            return True
        except Exception as exc:
            message.mark_failed(str(exc))
            return False
