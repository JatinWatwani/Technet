"""Integration tests verifying real database persistence, transactions, and ledger durability."""
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from vigilo.db.base import Base
from vigilo.db.models import (
    AllocationModel,
    BatchModel,
    DeliveryModel,
    InventoryLedgerEntryModel,
    RiderModel,
    ShelterModel,
)
from vigilo.db.repository import DatabaseRepository
from vigilo.domain.clock import SimulatedClock
from vigilo.domain.dispatch import DispatchRequest
from vigilo.domain.models import AllocationState, DeliveryState
from vigilo.infrastructure.persistent_service import PersistentDispatchService


@pytest.fixture
def db_session_factory():
    # In-memory SQLite with StaticPool provides an isolated, real relational database for testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return factory


def test_real_database_schema_and_models(db_session_factory):
    with db_session_factory() as session:
        repo = DatabaseRepository(session)
        # Verify empty initially
        assert repo.list_batches() == []
        assert repo.list_riders() == []
        assert repo.list_shelters() == []


def test_persistent_service_full_lifecycle(db_session_factory):
    now = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    clock = SimulatedClock(now)

    # 1. Initialize persistent service backed by real database engine
    service = PersistentDispatchService(clock=clock, session_factory=db_session_factory)
    service.load_seed(now)

    # Verify rows physically exist in relational database tables
    with db_session_factory() as session:
        batch_rows = session.execute(select(BatchModel)).scalars().all()
        assert len(batch_rows) >= 4

        rider_rows = session.execute(select(RiderModel)).scalars().all()
        assert len(rider_rows) >= 3

        shelter_rows = session.execute(select(ShelterModel)).scalars().all()
        assert len(shelter_rows) >= 2

        # Verify initial intake ledger entries exist in database
        ledger_rows = session.execute(select(InventoryLedgerEntryModel)).scalars().all()
        assert len(ledger_rows) >= 4

    # 2. Execute a commit transaction
    req = DispatchRequest(
        batch_id="batch_prepared_meals",
        rider_id="rider_gamma",
        shelter_id="shelter_central",
        quantity=30,
        travel_minutes=20,
        handoff_minutes=10,
        now=now,
    )
    allocation = service.commit(req)
    assert allocation.state == AllocationState.CLAIMED
    assert allocation.quantity == 30

    # Verify allocation and reservation ledger entry are persisted in database
    with db_session_factory() as session:
        db_alloc = session.get(AllocationModel, allocation.id)
        assert db_alloc is not None
        assert db_alloc.quantity == 30
        assert db_alloc.state == "CLAIMED"

        db_batch = session.get(BatchModel, "batch_prepared_meals")
        assert db_batch.available_quantity == 70
        assert db_batch.reserved_quantity == 30

        db_rider = session.get(RiderModel, "rider_gamma")
        assert db_rider.active_load == 30
        assert db_rider.status == "ASSIGNED"

    # 3. Advance clock and acknowledge
    clock.advance(300)
    service.acknowledge_allocation(allocation.id)
    with db_session_factory() as session:
        db_alloc = session.get(AllocationModel, allocation.id)
        assert db_alloc.state == "ACKNOWLEDGED"
        assert db_alloc.acknowledged_at is not None

    # 4. Confirm physical pickup
    clock.advance(600)
    delivery = service.pickup_allocation(allocation.id)
    assert delivery.state == DeliveryState.PICKED_UP

    with db_session_factory() as session:
        db_deliv = session.get(DeliveryModel, delivery.id)
        assert db_deliv is not None
        assert db_deliv.quantity == 30
        assert db_deliv.state == "PICKED_UP"

        db_batch = session.get(BatchModel, "batch_prepared_meals")
        assert db_batch.reserved_quantity == 0
        assert db_batch.picked_up_quantity == 30

    # 5. Confirm final delivery
    clock.advance(1200)
    completed = service.deliver_cargo(delivery.id)
    assert completed.state == DeliveryState.DELIVERED

    with db_session_factory() as session:
        db_deliv = session.get(DeliveryModel, delivery.id)
        assert db_deliv.state == "DELIVERED"
        assert db_deliv.delivered_at is not None

        db_batch = session.get(BatchModel, "batch_prepared_meals")
        assert db_batch.picked_up_quantity == 0
        assert db_batch.delivered_quantity == 30

        db_rider = session.get(RiderModel, "rider_gamma")
        assert db_rider.active_load == 0
        assert db_rider.status == "AVAILABLE"

    # 6. Verify mathematical reconciliation directly from database ledger entries
    reconciliation = service.reconcile_batch("batch_prepared_meals")
    assert reconciliation.is_valid is True
    assert reconciliation.original_quantity == 100
    assert reconciliation.reconciled_balance.available == 70
    assert reconciliation.reconciled_balance.delivered == 30
    assert reconciliation.reconciled_balance.reserved == 0
    assert reconciliation.reconciled_balance.picked_up == 0
    assert reconciliation.entry_count == 4  # INTAKE, RESERVATION_HOLD, PICKUP_CONFIRMED, DELIVERY_CONFIRMED


def test_postgres_dispatch_service_adapter(tmp_path):
    db_file = tmp_path / "test_vigilo.db"
    db_url = f"sqlite:///{db_file}"

    from vigilo.infrastructure.postgres_backend import PostgresDispatchService

    clock = SimulatedClock()
    pg_service = PostgresDispatchService(database_url=db_url, clock=clock)
    pg_service.load_seed()

    assert len(pg_service.batches) >= 4
    assert len(pg_service.riders) >= 3
    assert len(pg_service.shelters) >= 2

    report = pg_service.reconcile_batch("batch_prepared_meals")
    assert report.is_valid is True
