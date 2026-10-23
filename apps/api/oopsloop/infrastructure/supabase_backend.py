from __future__ import annotations

from datetime import datetime
from typing import Any

from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions

from ..domain.dispatch import DispatchError, DispatchRequest, DispatchService
from ..domain.models import Allocation, AllocationState, Batch, ItemRules, Rider, Shelter


class SupabaseDispatchService:
    """Supabase-backed adapter that reuses the domain validation rules.

    Preview reads the current rows and delegates hard-constraint validation to
    the same DispatchService used by local tests. Commit uses a Postgres RPC so
    row locks and all inventory updates happen in one database transaction.
    """

    def __init__(self, url: str, secret_key: str) -> None:
        self.client: Client = create_client(
            url,
            secret_key,
            options=ClientOptions(
                auto_refresh_token=False,
                persist_session=False,
            ),
        )

    def preview(self, request: DispatchRequest):
        service = self._load_domain_service(request)
        return service.preview(request)

    def commit(self, request: DispatchRequest) -> Allocation:
        try:
            response = self.client.rpc(
                "dispatch_allocation",
                {
                    "p_batch_id": request.batch_id,
                    "p_rider_id": request.rider_id,
                    "p_shelter_id": request.shelter_id,
                    "p_quantity": request.quantity,
                    "p_travel_minutes": request.travel_minutes,
                    "p_handoff_minutes": request.handoff_minutes,
                    "p_now": request.now.isoformat(),
                },
            ).execute()
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
        return self._allocation_from_row(response.data)

    def _load_domain_service(self, request: DispatchRequest) -> DispatchService:
        service = DispatchService()
        batch = self._row("batches", request.batch_id)
        rider = self._row("riders", request.rider_id)
        shelter = self._row("shelters", request.shelter_id)
        if batch is not None:
            service.batches[request.batch_id] = Batch(
                id=batch["id"],
                original_quantity=batch["original_quantity"],
                available_quantity=batch["available_quantity"],
                created_at=datetime.fromisoformat(batch["created_at"].replace("Z", "+00:00")),
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

    def _row(self, table: str, entity_id: str) -> dict[str, Any] | None:
        response = self.client.table(table).select("*").eq("id", entity_id).limit(1).execute()
        rows = response.data or []
        return rows[0] if rows else None

    @staticmethod
    def _allocation_from_row(row: dict[str, Any]) -> Allocation:
        return Allocation(
            id=row["id"],
            batch_id=row["batch_id"],
            rider_id=row["rider_id"],
            shelter_id=row["shelter_id"],
            quantity=row["quantity"],
            travel_minutes=row["travel_minutes"],
            handoff_minutes=row["handoff_minutes"],
            state=AllocationState(row["state"]),
            claimed_at=datetime.fromisoformat(row["claimed_at"].replace("Z", "+00:00")),
            safe_until=datetime.fromisoformat(row["safe_until"].replace("Z", "+00:00")),
        )
