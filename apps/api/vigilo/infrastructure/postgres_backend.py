from __future__ import annotations

import json
from datetime import datetime
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row

from ..domain.dispatch import DispatchError, DispatchRequest, DispatchService
from ..domain.models import Allocation, AllocationState, Batch, ItemRules, Rider, Shelter


class PostgresDispatchService:
    """PostgreSQL-backed adapter for the Supabase database.

    Preview loads current rows and reuses the deterministic domain rules.
    Commit calls the database function, which locks the affected rows and
    updates inventory, rider capacity, shelter capacity, and allocation state
    in one PostgreSQL transaction.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def preview(self, request: DispatchRequest):
        service = self._load_domain_service(request)
        return service.preview(request)

    def commit(self, request: DispatchRequest) -> Allocation:
        try:
            with psycopg.connect(self.database_url, connect_timeout=15) as connection:
                row = connection.execute(
                    """
                    select public.dispatch_allocation(
                        %(batch_id)s,
                        %(rider_id)s,
                        %(shelter_id)s,
                        %(quantity)s,
                        %(travel_minutes)s,
                        %(handoff_minutes)s,
                        %(now)s
                    ) as allocation
                    """,
                    {
                        "batch_id": request.batch_id,
                        "rider_id": request.rider_id,
                        "shelter_id": request.shelter_id,
                        "quantity": request.quantity,
                        "travel_minutes": request.travel_minutes,
                        "handoff_minutes": request.handoff_minutes,
                        "now": request.now,
                    },
                ).fetchone()
        except Exception as exc:
            known_codes = (
                "BATCH_NOT_FOUND",
                "RIDER_NOT_FOUND",
                "SHELTER_NOT_FOUND",
                "INVENTORY_INSUFFICIENT",
                "RIDER_UNAVAILABLE",
                "RIDER_CAPACITY_EXCEEDED",
                "SHELTER_CLOSED",
                "SHELTER_DEMAND_EXCEEDED",
                "SHELTER_CAPACITY_EXCEEDED",
                "MISSING_PREREQUISITE",
                "SAFETY_DEADLINE_UNSAFE",
            )
            message = str(exc)
            code = next((candidate for candidate in known_codes if candidate in message), "DISPATCH_REJECTED")
            raise DispatchError(code, message) from exc

        payload = row[0] if row else None
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            raise DispatchError("INVALID_DATABASE_RESPONSE", "The database returned an invalid allocation response.")
        return self._allocation_from_row(payload)

    def _load_domain_service(self, request: DispatchRequest) -> DispatchService:
        service = DispatchService()
        with psycopg.connect(
            self.database_url,
            connect_timeout=15,
            row_factory=cast(Any, dict_row),
        ) as connection:
            batch = cast(
                dict[str, Any] | None,
                connection.execute("select * from public.batches where id = %s", (request.batch_id,)).fetchone(),
            )
            rider = cast(
                dict[str, Any] | None,
                connection.execute("select * from public.riders where id = %s", (request.rider_id,)).fetchone(),
            )
            shelter = cast(
                dict[str, Any] | None,
                connection.execute("select * from public.shelters where id = %s", (request.shelter_id,)).fetchone(),
            )

        if batch is not None:
            service.batches[request.batch_id] = Batch(
                id=batch["id"],
                original_quantity=batch["original_quantity"],
                available_quantity=batch["available_quantity"],
                created_at=batch["created_at"],
                item_rules=ItemRules(
                    safe_handling_minutes=batch["safe_handling_minutes"],
                    safety_buffer_minutes=batch["safety_buffer_minutes"],
                    required_prerequisites=frozenset(batch.get("required_prerequisites") or []),
                ),
            )
        if rider is not None:
            service.riders[request.rider_id] = Rider(
                id=rider["id"],
                capacity=rider["capacity"],
                active_load=rider["active_load"],
                available=rider["available"],
            )
        if shelter is not None:
            service.shelters[request.shelter_id] = Shelter(
                id=shelter["id"],
                demand_remaining=shelter["demand_remaining"],
                receiving_capacity_remaining=shelter["receiving_capacity_remaining"],
                prerequisites=frozenset(shelter.get("prerequisites") or []),
                open=shelter["open"],
            )
        return service

    @staticmethod
    def _allocation_from_row(row: dict[str, Any]) -> Allocation:
        return Allocation(
            id=str(row["id"]),
            batch_id=row["batch_id"],
            rider_id=row["rider_id"],
            shelter_id=row["shelter_id"],
            quantity=row["quantity"],
            travel_minutes=row["travel_minutes"],
            handoff_minutes=row["handoff_minutes"],
            state=AllocationState(row["state"]),
            claimed_at=_as_datetime(row["claimed_at"]),
            safe_until=_as_datetime(row["safe_until"]),
        )


def _as_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
